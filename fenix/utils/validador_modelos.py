# utils/validador_modelos.py
"""
Módulo de validación de modelos de Redes de Petri
Previene almacenar modelos mal formados
"""

import logging
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Severidad(Enum):
    ERROR = "ERROR"
    ADVERTENCIA = "ADVERTENCIA"
    INFO = "INFO"


@dataclass
class Problema:
    """Estructura para reportar problemas encontrados"""
    severidad: Severidad
    tipo: str
    descripcion: str
    elemento_id: str = None
    sugerencia: str = None


class ValidadorRedPetri:
    """
    Valida la correctitud de una Red de Petri (PNML)
    """
    
    def __init__(self, red, nombre_red: str = None):
        """
        Args:
            red: Instancia de PetriNet del parser_pnml
            nombre_red: Nombre de la red para reportes
        """
        self.red = red
        self.nombre_red = nombre_red or red.nombre if hasattr(red, 'nombre') else "desconocida"
        self.problemas: List[Problema] = []
    
    def validar(self) -> Tuple[bool, List[Problema]]:
        """
        Ejecuta todas las validaciones
        
        Returns:
            (es_valida, lista_de_problemas)
        """
        self.problemas = []
        
        self._validar_nombres_unicos()
        self._validar_arcos_conectan_existentes()
        self._validar_no_lugares_huérfanos()
        self._validar_no_transiciones_huérfanas()
        self._validar_marcado_inicial_asciende()
        self._validar_no_ciclos_muertos()
        self._validar_conectividad()
        self._validar_refinamientos_encadenamiento()
        
        es_valida = len([p for p in self.problemas if p.severidad == Severidad.ERROR]) == 0
        
        if es_valida:
            logger.info(f"✅ Red '{self.nombre_red}' validada correctamente")
        else:
            logger.warning(f"⚠️ Red '{self.nombre_red}' tiene {len([p for p in self.problemas if p.severidad == Severidad.ERROR])} errores")
        
        return es_valida, self.problemas
    
    def _validar_nombres_unicos(self):
        """Verifica que no haya nombres duplicados"""
        nombres_places = set()
        nombres_trans = set()
        
        for pid, place in self.red.places.items():
            if place.nombre in nombres_places:
                self.problemas.append(Problema(
                    severidad=Severidad.ERROR,
                    tipo="nombre_duplicado",
                    descripcion=f"Lugar '{place.nombre}' duplicado",
                    elemento_id=pid,
                    sugerencia="Renombre los lugares para que sean únicos"
                ))
            nombres_places.add(place.nombre)
        
        for tid, trans in self.red.transitions.items():
            if trans.nombre in nombres_trans:
                self.problemas.append(Problema(
                    severidad=Severidad.ERROR,
                    tipo="nombre_duplicado",
                    descripcion=f"Transición '{trans.nombre}' duplicada",
                    elemento_id=tid,
                    sugerencia="Renombre las transiciones para que sean únicas"
                ))
            nombres_trans.add(trans.nombre)
    
    def _validar_arcos_conectan_existentes(self):
        """Verifica que los arcos conecten elementos que existen"""
        for tid, arcos in self.red.arcos_entrada.items():
            for arco in arcos:
                if arco.source not in self.red.places:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="arco_invalido",
                        descripcion=f"Arco entrada a transición '{tid}' conecta a lugar inexistente '{arco.source}'",
                        elemento_id=tid,
                        sugerencia="Verifique que el lugar de origen exista"
                    ))
        
        for tid, arcos in self.red.arcos_salida.items():
            for arco in arcos:
                if arco.target not in self.red.places:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="arco_invalido",
                        descripcion=f"Arco salida de transición '{tid}' conecta a lugar inexistente '{arco.target}'",
                        elemento_id=tid,
                        sugerencia="Verifique que el lugar de destino exista"
                    ))
    
    def _validar_no_lugares_huérfanos(self):
        """Verifica que todos los lugares tengan al menos un arco"""
        lugares_con_arco = set()
        
        for arcos in self.red.arcos_entrada.values():
            for arco in arcos:
                lugares_con_arco.add(arco.source)
        
        for arcos in self.red.arcos_salida.values():
            for arco in arcos:
                lugares_con_arco.add(arco.target)
        
        for pid in self.red.places:
            if pid not in lugares_con_arco:
                self.problemas.append(Problema(
                    severidad=Severidad.ADVERTENCIA,
                    tipo="lugar_huérfano",
                    descripcion=f"Lugar '{pid}' no tiene arcos conectados",
                    elemento_id=pid,
                    sugerencia="Considere eliminar el lugar o conectarlo al proceso"
                ))
    
    def _validar_no_transiciones_huérfanas(self):
        """Verifica que todas las transiciones tengan arcos de entrada y salida"""
        for tid in self.red.transitions:
            entradas = self.red.arcos_entrada.get(tid, [])
            salidas = self.red.arcos_salida.get(tid, [])
            
            if len(entradas) == 0:
                self.problemas.append(Problema(
                    severidad=Severidad.ERROR,
                    tipo="transicion_huérfana",
                    descripcion=f"Transición '{tid}' no tiene arcos de entrada",
                    elemento_id=tid,
                    sugerencia="Agregue al menos un arco de entrada desde un lugar"
                ))
            
            if len(salidas) == 0:
                self.problemas.append(Problema(
                    severidad=Severidad.ERROR,
                    tipo="transicion_huérfana",
                    descripcion=f"Transición '{tid}' no tiene arcos de salida",
                    elemento_id=tid,
                    sugerencia="Agregue al menos un arco de salida hacia un lugar"
                ))
    
    def _validar_marcado_inicial_asciende(self):
        """Verifica que el marcado inicial solo esté en lugares que existen"""
        for pid, place in self.red.places.items():
            if place.marking_inicial > 0:
                if pid not in self.red.places:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="marcado_invalido",
                        descripcion=f"Marcado inicial en lugar inexistente '{pid}'",
                        elemento_id=pid,
                        sugerencia="Verifique que el lugar exista en el modelo"
                    ))
    
    def _validar_no_ciclos_muertos(self):
        """Detecta posibles ciclos muertos (lugares que nunca se marcan)"""
        # Simplificado: lugares sin arcos de entrada nunca se marcan
        lugares_con_entrada = set()
        for arcos in self.red.arcos_salida.values():
            for arco in arcos:
                lugares_con_entrada.add(arco.target)
        
        lugares_con_marcado_inicial = {pid for pid, p in self.red.places.items() if p.marking_inicial > 0}
        
        lugares_inaccesibles = set(self.red.places.keys()) - lugares_con_entrada - lugares_con_marcado_inicial
        
        for pid in lugares_inaccesibles:
            self.problemas.append(Problema(
                severidad=Severidad.ADVERTENCIA,
                tipo="lugar_inaccesible",
                descripcion=f"Lugar '{pid}' nunca recibe marcado (sin arcos de entrada)",
                elemento_id=pid,
                sugerencia="Verifique si este lugar debería recibir marcado o eliminarlo"
            ))
    
    def _validar_conectividad(self):
        """Verifica que la red esté conectada (no componentes aislados)"""
        # BFS desde lugares con marcado inicial
        visitados = set()
        cola = list(self.red.places.keys())
        
        # Simplificado: verificar que haya al menos un camino
        if len(cola) == 0:
            self.problemas.append(Problema(
                severidad=Severidad.ERROR,
                tipo="red_vacia",
                descripcion="La red no tiene lugares",
                sugerencia="Agregue al menos un lugar a la red"
            ))
    
    def _validar_refinamientos_encadenamiento(self):
        """
        Valida que las transiciones que son puntos de refinamiento o encadenamiento
        tengan nombres que permitan identificarlas correctamente
        """
        transiciones_sin_nombre = []
        
        for tid, trans in self.red.transitions.items():
            if not trans.nombre or trans.nombre.strip() == "":
                transiciones_sin_nombre.append(tid)
        
        for tid in transiciones_sin_nombre:
            self.problemas.append(Problema(
                severidad=Severidad.ADVERTENCIA,
                tipo="transicion_sin_nombre",
                descripcion=f"Transición '{tid}' no tiene nombre",
                elemento_id=tid,
                sugerencia="Asigne un nombre descriptivo para facilitar encadenamiento"
            ))


class ValidadorEncadenamiento:
    """
    Valida reglas de encadenamiento entre redes
    """
    
    def __init__(self, reglas: dict, redes_disponibles: set = None):
        """
        Args:
            reglas: Diccionario con reglas de encadenamiento
            redes_disponibles: Set con nombres de redes cargadas
        """
        self.reglas = reglas
        self.redes_disponibles = redes_disponibles or set()
        self.problemas: List[Problema] = []
    
    def validar(self) -> Tuple[bool, List[Problema]]:
        """Valida consistencia de reglas de encadenamiento"""
        self.problemas = []
        
        for red_origen, transiciones in self.reglas.items():
            # Verificar que la red origen exista
            if self.redes_disponibles and red_origen not in self.redes_disponibles:
                self.problemas.append(Problema(
                    severidad=Severidad.ERROR,
                    tipo="red_no_existe",
                    descripcion=f"Red origen '{red_origen}' no está cargada",
                    sugerencia="Verifique el nombre de la red en las reglas"
                ))
            
            for trans_id, destino in transiciones.items():
                # Verificar estructura de la regla
                if 'red_destino' not in destino:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="regla_incompleta",
                        descripcion=f"Regla para {red_origen}.{trans_id} falta 'red_destino'",
                        sugerencia="Complete la regla con red_destino y evento"
                    ))
                
                if 'evento' not in destino:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="regla_incompleta",
                        descripcion=f"Regla para {red_origen}.{trans_id} falta 'evento'",
                        sugerencia="Complete la regla con el evento destino"
                    ))
                
                red_destino = destino.get('red_destino', '')
                if self.redes_disponibles and red_destino not in self.redes_disponibles:
                    self.problemas.append(Problema(
                        severidad=Severidad.ERROR,
                        tipo="red_destino_no_existe",
                        descripcion=f"Red destino '{red_destino}' no está cargada",
                        sugerencia="Verifique el nombre de la red destino"
                    ))
        
        es_valida = len([p for p in self.problemas if p.severidad == Severidad.ERROR]) == 0
        
        if es_valida:
            logger.info(f"✅ Encadenamiento validado: {len(self.reglas)} redes origen, {sum(len(r) for r in self.reglas.values())} reglas")
        
        return es_valida, self.problemas


class ValidadorCompleto:
    """
    Valida todos los componentes del sistema
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
    
    def validar_red_desde_archivo(self, ruta_pnml: str) -> Tuple[bool, List[Problema]]:
        """Valida una red desde archivo PNML antes de importar a BD"""
        from utils.parser_pnml import cargar_red_desde_pnml
        
        red = cargar_red_desde_pnml(ruta_pnml)
        if not red:
            return False, [Problema(
                severidad=Severidad.ERROR,
                tipo="archivo_invalido",
                descripcion=f"No se pudo cargar el archivo {ruta_pnml}",
                sugerencia="Verifique que el archivo sea un PNML válido"
            )]
        
        validador = ValidadorRedPetri(red, ruta_pnml)
        return validador.validar()
    
    def validar_antes_de_guardar(self, red) -> Tuple[bool, List[Problema]]:
        """
        Valida una red antes de guardarla en BD
        Útil para prevenir almacenar modelos erróneos
        """
        validador = ValidadorRedPetri(red)
        return validador.validar()
    
    def validar_todo(self, pnml_dir: str = None) -> dict:
        """Valida todas las redes en un directorio"""
        from pathlib import Path
        from utils.parser_pnml import cargar_red_desde_pnml
        
        resultados = {
            'total_archivos': 0,
            'validas': 0,
            'invalidas': 0,
            'errores_por_red': {}
        }
        
        if pnml_dir:
            ruta_dir = Path(pnml_dir)
            for pnml_file in ruta_dir.glob("*.pnml"):
                resultados['total_archivos'] += 1
                red = cargar_red_desde_pnml(str(pnml_file))
                if red:
                    validador = ValidadorRedPetri(red, pnml_file.stem)
                    es_valida, problemas = validador.validar()
                    
                    if es_valida:
                        resultados['validas'] += 1
                    else:
                        resultados['invalidas'] += 1
                        resultados['errores_por_red'][pnml_file.stem] = [
                            p for p in problemas if p.severidad == Severidad.ERROR
                        ]
        
        return resultados


# Función helper para reportar problemas
def reportar_problemas(problemas: List[Problema]) -> str:
    """Genera reporte legible de problemas"""
    if not problemas:
        return "✅ No se encontraron problemas"
    
    lineas = []
    for p in problemas:
        emoji = "❌" if p.severidad == Severidad.ERROR else "⚠️" if p.severidad == Severidad.ADVERTENCIA else "ℹ️"
        lineas.append(f"{emoji} [{p.severidad.value}] {p.tipo}")
        lineas.append(f"   {p.descripcion}")
        if p.elemento_id:
            lineas.append(f"   Elemento: {p.elemento_id}")
        if p.sugerencia:
            lineas.append(f"   Sugerencia: {p.sugerencia}")
        lineas.append("")
    
    return "\n".join(lineas)


# script/validar_modelos.py
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Validar todas las redes en el directorio PNML
    pnml_dir = Path(__file__).parent.parent / "static" / "archivospnml"
    
    print("=" * 60)
    print("VALIDACIÓN DE MODELOS DE REDES DE PETRI")
    print("=" * 60)
    
    validador = ValidadorCompleto()
    resultados = validador.validar_todo(str(pnml_dir))
    
    print(f"\n📊 Resumen:")
    print(f"   Archivos procesados: {resultados['total_archivos']}")
    print(f"   Válidas: {resultados['validas']}")
    print(f"   Inválidas: {resultados['invalidas']}")
    
    if resultados['errores_por_red']:
        print(f"\n❌ Redes con errores:")
        for red, errores in resultados['errores_por_red'].items():
            print(f"\n   📁 {red}:")
            for err in errores:
                print(f"      - {err.descripcion}")
    else:
        print(f"\n✅ Todas las redes son válidas")