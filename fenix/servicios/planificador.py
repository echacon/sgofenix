from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from modelos.Producto import HolonRuta, AsignacionRecurso, Formula, InsumoFormula
from modelos.Recursos import Recurso, ConexionFisica, RecursoEquipo, RecursoPersonal
from modelos.Taxonomia import EtapaRuta

class PlanificadorProduccion:
    def __init__(self, session: Session):
        self.session = session

    def seleccionar_recursos_para_orden(self, producto_id: int, cantidad: float, prioridad: int) -> Optional[dict]:
        """
        Evalúa todos los modelos de ruta (HolonRuta) activos para el producto.
        Realiza composición selectiva para cada uno, genera las asignaciones conectables
        físicamente, calcula sus costos ABC reales y selecciona la alternativa de mínimo costo global.
        """
        # 1. Obtener todas las rutas (HolonRuta) activas para el producto
        rutas = self.session.query(HolonRuta).filter(
            HolonRuta.producto_id == producto_id,
            HolonRuta.activa == True
        ).all()
        
        if not rutas:
            return None
            
        mejores_opciones_de_rutas = []
        
        for ruta in rutas:
            # 2. Composición Selectiva de Etapas:
            # Obtener todas las etapas potenciales del patrón
            etapas_potenciales = self.session.query(EtapaRuta).filter(
                EtapaRuta.patronRuta_id == ruta.patron_id
            ).order_by(EtapaRuta.id).all()
            
            # Obtener la fórmula asociada a la ruta para identificar insumos
            formula = self.session.query(Formula).filter(
                Formula.holon_ruta_id == ruta.id
            ).first()
            
            # Filtrar etapas requeridas (Composición Selectiva)
            etapas_requeridas = []
            for etapa in etapas_potenciales:
                # Regla: Si la etapa es Molienda (código de operación "MOL"),
                # solo se incluye si la fórmula tiene insumos asignados a esta etapa
                codigo_op = etapa.tipoDeOperacion.codigo if etapa.tipoDeOperacion else ""
                if codigo_op == "MOL":
                    tiene_insumos = False
                    if formula:
                        insumos_etapa = self.session.query(InsumoFormula).filter(
                            InsumoFormula.formula_id == formula.id,
                            InsumoFormula.etapa_ruta_id == etapa.id
                        ).count()
                        tiene_insumos = insumos_etapa > 0
                    if not tiene_insumos:
                        # Excluir la molienda de la composición
                        continue
                etapas_requeridas.append(etapa)
                
            if not etapas_requeridas:
                continue
                
            # 3. Obtener recursos disponibles para cada etapa requerida
            recursos_por_etapa = {}
            for etapa in etapas_requeridas:
                asignaciones = self.session.query(AsignacionRecurso).filter(
                    AsignacionRecurso.holon_ruta_id == ruta.id,
                    AsignacionRecurso.etapa_ruta_id == etapa.id
                ).all()
                if not asignaciones:
                    # Si alguna etapa obligatoria no tiene asignaciones, esta ruta no es viable
                    recursos_por_etapa = None
                    break
                recursos_por_etapa[etapa.id] = asignaciones
                
            if not recursos_por_etapa:
                continue
                
            # 4. Generar combinaciones de recursos que sean válidas (conectadas físicamente)
            combinaciones = self._generar_combinaciones_validas(etapas_requeridas, recursos_por_etapa)
            
            # 5. Evaluar costo y duración de cada combinación
            for comb in combinaciones:
                evaluacion = self._evaluar_combinacion(comb, cantidad)
                mejores_opciones_de_rutas.append({
                    "holon_ruta_id": ruta.id,
                    "holon_ruta_nombre": ruta.nombre,
                    "combinacion": comb,
                    "costo_total": evaluacion["costo_total"],
                    "duracion_total_min": evaluacion["duracion_total_min"],
                    "asignacion": evaluacion["por_etapa"]
                })
                
        if not mejores_opciones_de_rutas:
            return None
            
        # 6. Seleccionar la mejor opción absoluta (mínimo costo)
        mejor_opcion = min(mejores_opciones_de_rutas, key=lambda x: x["costo_total"])
        
        return {
            "holon_ruta_id": mejor_opcion["holon_ruta_id"],
            "holon_ruta_nombre": mejor_opcion["holon_ruta_nombre"],
            "costo_total": mejor_opcion["costo_total"],
            "duracion_total_min": mejor_opcion["duracion_total_min"],
            "asignacion": mejor_opcion["asignacion"]
        }

    def _buscar_camino_trasvase(self, origen_id: int, destino_id: int) -> Optional[List[ConexionFisica]]:
        """
        Busca un camino de conexiones físicas entre origen y destino (BFS).
        Retorna la lista de conexiones que componen el camino, o None si no hay camino.
        """
        if origen_id == destino_id:
            return []
            
        visitados = set()
        cola = [(origen_id, [])]
        
        while cola:
            actual_id, camino = cola.pop(0)
            if actual_id == destino_id:
                return camino
                
            if actual_id in visitados:
                continue
            visitados.add(actual_id)
            
            conexiones = self.session.query(ConexionFisica).filter(
                ConexionFisica.recurso_origen_id == actual_id,
                ConexionFisica.activa == True,
                ConexionFisica.disponible == True
            ).all()
            
            for conn in conexiones:
                dest_id = conn.recurso_destino_id
                if dest_id not in visitados:
                    cola.append((dest_id, camino + [conn]))
                    
        return None

    def _generar_combinaciones_validas(self, etapas: List[EtapaRuta], recursos_por_etapa: Dict[int, List[AsignacionRecurso]]) -> List[List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]]]:
        """
        Genera combinaciones de recursos respetando la conectividad física en la planta.
        Cada combinación es una lista de tuplas: (etapa, asignacion_recurso, lista_conexiones_trasvase)
        """
        etapas_ordenadas = list(etapas)
        if not etapas_ordenadas:
            return []
            
        combinaciones_validas = []
        
        def resolver(etapa_idx: int, camino_actual: List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]]):
            if etapa_idx == len(etapas_ordenadas):
                combinaciones_validas.append(camino_actual)
                return
                
            etapa = etapas_ordenadas[etapa_idx]
            asignaciones_etapa = recursos_por_etapa.get(etapa.id, [])
            
            for asig in asignaciones_etapa:
                if etapa_idx == 0:
                    resolver(etapa_idx + 1, camino_actual + [(etapa, asig, [])])
                else:
                    # Validar conectividad con el recurso de la etapa anterior
                    _, asig_anterior, _ = camino_actual[-1]
                    conexiones = self._buscar_camino_trasvase(asig_anterior.recurso_id, asig.recurso_id)
                    if conexiones is not None:
                        resolver(etapa_idx + 1, camino_actual + [(etapa, asig, conexiones)])
                        
        resolver(0, [])
        return combinaciones_validas

    def _evaluar_combinacion(self, combinacion: List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]], cantidad: float) -> dict:
        """
        Calcula el costo total ABC y duración estimada para una combinación dada.
        """
        costo_total = 0.0
        duracion_total_min = 0.0
        por_etapa = {}
        
        for etapa, asig, conns in combinacion:
            recurso_base = asig.recurso
            recurso_eq = recurso_base.equipo if recurso_base else None
            
            # 1. Costo de procesamiento en máquina
            prep_min = asig.requiere_preparacion_min or 0.0
            limp_min = asig.requiere_limpieza_min or 0.0
            duracion_proc_min = asig.duracion_estimada_min or 0.0
            
            # Si el recurso tiene velocidad, ajustar por cantidad
            if asig.velocidad_procesamiento and asig.velocidad_procesamiento > 0:
                duracion_proc_min = cantidad / asig.velocidad_procesamiento
            elif recurso_eq and recurso_eq.velocidad_procesamiento and recurso_eq.velocidad_procesamiento > 0:
                duracion_proc_min = cantidad / recurso_eq.velocidad_procesamiento
                
            tiempo_operacion_min = duracion_proc_min + prep_min + limp_min
            duracion_total_min += tiempo_operacion_min
            tiempo_operacion_h = tiempo_operacion_min / 60.0
            
            # Costos unitarios de máquina
            consumo_kw = recurso_eq.consumo_energia_kw if recurso_eq else 0.0
            costo_kwh = recurso_eq.costo_energia_por_kwh if recurso_eq else 0.0
            costo_depreciacion_h = recurso_eq.costo_depreciacion_hora if recurso_eq else 0.0
            
            # Obtener el EDR actual si el holón recurso cuenta con medidor de energía
            edr = 1.0
            if recurso_eq and getattr(recurso_eq, 'medidor_energia', False):
                edr = getattr(recurso_eq, 'edr_actual', 1.0)
                if edr is None:
                    edr = 1.0
            
            # Aplicar el EDR como multiplicador de desviación de energía y depreciación del holón
            costo_energia = (consumo_kw * tiempo_operacion_h * costo_kwh) * edr
            costo_depreciacion = (costo_depreciacion_h * tiempo_operacion_h) * edr
            costo_mano_obra = (asig.costo_por_hora_real or 0.0) * tiempo_operacion_h
            
            costo_procesamiento = costo_energia + costo_depreciacion + costo_mano_obra
            costo_total += costo_procesamiento
            
            # 2. Costo de conexiones de trasvase y recursos compartidos (bomba, multiplexor, operador)
            costos_trasvase_etapa = 0.0
            for conn in conns:
                # Estimar tiempo de trasvase a partir del flujo máximo (L/s) o usar 5 min por defecto
                if conn.flujo_maximo_lps and conn.flujo_maximo_lps > 0:
                    tiempo_transvase_min = (cantidad / conn.flujo_maximo_lps) / 60.0
                else:
                    tiempo_transvase_min = 5.0  # default 5 min
                
                duracion_total_min += tiempo_transvase_min
                tiempo_transvase_h = tiempo_transvase_min / 60.0
                
                # Costo de la conexión física estimado por la longitud (ej. 0.2 $ por metro de tubería)
                costos_trasvase_etapa += (conn.longitud_metros or 0.0) * 0.2
                
                # Si requiere bombeo (bomba compartida)
                if conn.requiere_bombeo:
                    # Tarifa estimada de bombeo (energía + depreciación bomba)
                    costos_trasvase_etapa += tiempo_transvase_h * 15.0
                    
                # Si requiere operador de trasvase (operario compartido)
                if conn.requiere_operador:
                    costos_trasvase_etapa += tiempo_transvase_h * 50.0
                    
                # Si es un multiplexor/manifold, sumamos penalización de uso por cuello de botella
                if conn.tipo == "MULTIPLEXOR":
                    costos_trasvase_etapa += 25.0  # tarifa de congestión/mantenimiento
                    
                # Costo por mermas de material durante el trasvase (estimando valor de lote)
                merma_material = cantidad * (conn.perdida_material_pct or 0.0)
                costo_merma = merma_material * 12.0  # Asumimos costo prom de material de 12.0 $/kg
                costos_trasvase_etapa += costo_merma
                
            costo_total += costos_trasvase_etapa
            
            por_etapa[etapa.nombre] = {
                "recurso_id": recurso_base.id,
                "recurso_nombre": recurso_base.nombre,
                "duracion_min": tiempo_operacion_min,
                "costo_procesamiento": costo_procesamiento,
                "costo_trasvase": costos_trasvase_etapa
            }
            
        return {
            "costo_total": costo_total,
            "duracion_total_min": duracion_total_min,
            "por_etapa": por_etapa
        }