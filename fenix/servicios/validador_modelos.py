# servicios/validador_modelos.py
import logging
from typing import Dict, List, Tuple, Any
from collections import deque
from utils.parser_pnml import PetriNet

logger = logging.getLogger(__name__)


class ValidadorRedes:
    @staticmethod
    def validar_red_petri(red: PetriNet, metadatos: dict = None) -> Tuple[bool, List[str]]:
        """Valida una red Petri cargada desde PNML (y opcionalmente metadatos YAML).
        Retorna (es_valida, lista_de_errores)."""
        errores = []

        # 1. Lugares: deben tener nombre
        for pid, place in red.places.items():
            if not place.nombre or place.nombre.strip() == "":
                errores.append(f"Lugar {pid} sin nombre")

        # 2. Existe al menos un lugar final (si metadatos define estados_finales) o detectable
        if metadatos and "estados_finales" in metadatos:
            finales = metadatos["estados_finales"]
            for fid in finales:
                if fid not in red.places:
                    errores.append(f"Lugar final '{fid}' definido en metadatos pero no existe en la red")
        else:
            # Intento de detección automática: lugares sin arcos de salida
            lugares_sin_salida = set(red.places.keys())
            for arc in red.arcs.values():
                if arc.source in lugares_sin_salida:
                    lugares_sin_salida.discard(arc.source)
            if not lugares_sin_salida:
                errores.append("No se detectaron lugares sumideros (posible falta de lugar final)")

        # 3. Transiciones con trigger=200 deben tener nombre único dentro de la red
        trans_nombres = {}
        for tid, trans in red.transitions.items():
            trigger = getattr(trans, 'trigger', None)
            if trigger == '200':
                if not trans.nombre:
                    errores.append(f"Transición {tid} con trigger=200 no tiene nombre")
                elif trans.nombre in trans_nombres:
                    errores.append(f"Nombre de transición duplicado '{trans.nombre}' para trigger=200")
                else:
                    trans_nombres[trans.nombre] = tid

        # 4. Transiciones automáticas (trigger=None) deben tener precondiciones satisfacibles
        for tid, trans in red.transitions.items():
            trigger = getattr(trans, 'trigger', None)
            if trigger is None:
                entradas = [arc for arc in red.arcs.values() if arc.target == tid]
                if not entradas:
                    errores.append(f"Transición automática {tid} no tiene lugares de entrada")

        # 5. Arcos con peso cero
        for aid, arc in red.arcs.items():
            if arc.peso <= 0:
                errores.append(f"Arco {aid} tiene peso {arc.peso} (debe ser >=1)")

        # 6. Verificar que los arcos referencian lugares/transiciones existentes
        for aid, arc in red.arcs.items():
            if arc.source not in red.places and arc.source not in red.transitions:
                errores.append(f"Arco {aid}: origen '{arc.source}' no existe")
            if arc.target not in red.places and arc.target not in red.transitions:
                errores.append(f"Arco {aid}: destino '{arc.target}' no existe")

        # 7. Validación de alcanzabilidad (si se proporcionan marcado inicial y estados finales)
        if metadatos and 'estados_finales' in metadatos and metadatos.get('marcado_inicial'):
            inicial = metadatos['marcado_inicial']
            finales = metadatos['estados_finales']
            alcanzable, msg = ValidadorRedes.verificar_alcanzabilidad(red, inicial, finales)
            if not alcanzable:
                errores.append(f"La red no alcanza estado final: {msg}")

        es_valida = len(errores) == 0
        return es_valida, errores

    @staticmethod
    def validar_encadenamiento(reglas: Dict, redes_disponibles: List[str]) -> Tuple[bool, List[str]]:
        """Valida que las reglas de encadenamiento referencien redes y transiciones existentes."""
        errores = []
        for origen_key, destinos in reglas.items():
            if '.' not in origen_key:
                errores.append(f"Clave de origen mal formada: {origen_key}")
                continue
            red_origen, trans_origen = origen_key.split('.', 1)
            if red_origen not in redes_disponibles:
                errores.append(f"Red origen '{red_origen}' no existe en las redes cargadas")
            for dest in destinos:
                red_dest = dest.get('red_destino')
                evento_dest = dest.get('evento_destino')
                if red_dest not in redes_disponibles:
                    errores.append(f"Red destino '{red_dest}' no existe")
                if not evento_dest:
                    errores.append(f"Evento destino vacío para {origen_key} -> {red_dest}")
        return len(errores) == 0, errores

    @staticmethod
    def verificar_alcanzabilidad(red: PetriNet, marcado_inicial: Dict[str, int],
                                 lugares_finales: List[str],
                                 max_estados: int = 1000, max_profundidad: int = 50) -> Tuple[bool, str]:
        """
        Verifica si desde marcado_inicial se puede alcanzar un estado que contenga
        algún token en los lugares_finales. Retorna (alcanzable, mensaje).
        """
        # Helper para convertir marcado a tupla ordenada
        def estado_a_tuple(marcado):
            return tuple((l, marcado.get(l, 0)) for l in sorted(marcado.keys()))

        def tuple_a_estado(t):
            return {l: cnt for l, cnt in t}

        # Precomputar entradas y salidas de cada transición
        entradas_cache = {}
        salidas_cache = {}
        for trans_id in red.transitions:
            entradas_cache[trans_id] = {}
            salidas_cache[trans_id] = {}
            for arc in red.arcs.values():
                if arc.target == trans_id:
                    entradas_cache[trans_id][arc.source] = arc.peso
                elif arc.source == trans_id:
                    salidas_cache[trans_id][arc.target] = arc.peso

        def transicion_habilitada(marcado, trans_id):
            for lugar, peso in entradas_cache[trans_id].items():
                if marcado.get(lugar, 0) < peso:
                    return False
            return True

        def disparar_transicion(marcado, trans_id):
            nuevo = dict(marcado)
            for lugar, peso in entradas_cache[trans_id].items():
                nuevo[lugar] = nuevo.get(lugar, 0) - peso
                if nuevo[lugar] <= 0:
                    del nuevo[lugar]
            for lugar, peso in salidas_cache[trans_id].items():
                nuevo[lugar] = nuevo.get(lugar, 0) + peso
            return nuevo

        # BFS
        inicio = estado_a_tuple(marcado_inicial)
        visitados = {inicio}
        cola = deque([(inicio, 0)])  # (estado, profundidad)

        while cola:
            estado, prof = cola.popleft()
            marcado = tuple_a_estado(estado)
            # Verificar si algún lugar final tiene token
            for lugar_final in lugares_finales:
                if marcado.get(lugar_final, 0) > 0:
                    return True, f"Alcanzado lugar final {lugar_final} en profundidad {prof}"
            if prof >= max_profundidad:
                continue
            for trans_id in red.transitions:
                if transicion_habilitada(marcado, trans_id):
                    nuevo_marcado = disparar_transicion(marcado, trans_id)
                    nuevo_estado = estado_a_tuple(nuevo_marcado)
                    if nuevo_estado not in visitados:
                        if len(visitados) >= max_estados:
                            return False, f"Límite de {max_estados} estados alcanzado, no se encontró estado final"
                        visitados.add(nuevo_estado)
                        cola.append((nuevo_estado, prof + 1))
        return False, "No se alcanzó ningún lugar final dentro del límite de búsqueda"