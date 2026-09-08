from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from modelos.Producto import HolonRuta, AsignacionRecurso, Formula, InsumoFormula, Producto
from modelos.Recursos import Recurso, ConexionFisica, RecursoEquipo, RecursoPersonal
from modelos.Taxonomia import EtapaRuta
from utils.motor_abtppn import TokenColoreado

class PlanificadorProduccion:
    def __init__(self, session: Session):
        self.session = session

    def seleccionar_recursos_para_orden(self, producto_id: int, cantidad: float,
                                        prioridad: int, v_target: Optional[float] = None) -> Optional[dict]:
        """
        Evalúa todos los modelos de ruta (HolonRuta) activos para el producto.
        Realiza composición selectiva para cada uno, genera las asignaciones conectables
        físicamente, calcula sus costos ABC reales con balance de masa y mermas,
        y selecciona la alternativa óptima que cumpla con la cota de viabilidad económica (c_acc <= V_target).
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
            condiciones = ruta.condiciones or {}
            
            # Verificar rango de lote y prioridad mínima
            lote_min = condiciones.get('lote_minimo_kg', 0)
            lote_max = condiciones.get('lote_maximo_kg', float('inf'))
            if cantidad < lote_min or cantidad > lote_max:
                continue
            if prioridad < condiciones.get('prioridad_minima', 1):
                continue
            
            # 2. Composición Selectiva de Etapas
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
                    recursos_por_etapa = None
                    break
                recursos_por_etapa[etapa.id] = asignaciones
                
            if not recursos_por_etapa:
                continue
                
            # 4. Generar combinaciones de recursos válidas (conectadas físicamente)
            combinaciones = self._generar_combinaciones_validas(etapas_requeridas, recursos_por_etapa)
            
            # 5. Evaluar costo, balance de masa, absorción de mermas y viabilidad económica
            for comb in combinaciones:
                evaluacion = self._evaluar_combinacion(comb, cantidad, formula, v_target)
                
                # Poda Branch-and-Bound: descartar si excede la cota de viabilidad económica
                if v_target is not None and v_target > 0 and evaluacion["costo_total"] > v_target:
                    continue
                    
                mejores_opciones_de_rutas.append({
                    "holon_ruta_id": ruta.id,
                    "holon_ruta_nombre": ruta.nombre,
                    "combinacion": comb,
                    "costo_total": evaluacion["costo_total"],
                    "masa_salida": evaluacion["masa_salida"],
                    "costo_unitario": evaluacion["costo_unitario"],
                    "duracion_total_min": evaluacion["duracion_total_min"],
                    "asignacion": evaluacion["por_etapa"]
                })
                
        if not mejores_opciones_de_rutas:
            return None
            
        # 6. Seleccionar la mejor opción absoluta (mínimo costo global)
        mejor_opcion = min(mejores_opciones_de_rutas, key=lambda x: x["costo_total"])
        
        return {
            "holon_ruta_id": mejor_opcion["holon_ruta_id"],
            "holon_ruta_nombre": mejor_opcion["holon_ruta_nombre"],
            "costo_total": mejor_opcion["costo_total"],
            "masa_salida": mejor_opcion["masa_salida"],
            "costo_unitario": mejor_opcion["costo_unitario"],
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

    def _generar_combinaciones_validas(self, etapas: List[EtapaRuta],
                                       recursos_por_etapa: Dict[int, List[AsignacionRecurso]]) -> List[List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]]]:
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
                    _, asig_anterior, _ = camino_actual[-1]
                    conexiones = self._buscar_camino_trasvase(asig_anterior.recurso_id, asig.recurso_id)
                    if conexiones is not None:
                        resolver(etapa_idx + 1, camino_actual + [(etapa, asig, conexiones)])
                        
        resolver(0, [])
        return combinaciones_validas

    def _evaluar_combinacion(self, combinacion: List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]],
                             cantidad_lote: float, formula: Optional[Formula] = None,
                             v_target: Optional[float] = None) -> dict:
        """
        Calcula el costo total ABC, balance de masa, absorción de mermas y duración estimada.
        Formalización:
        - c_acc = c_acc_prev + c_raw_add + c_proc + c_trasvase
        - m_exit = (m_enter + delta_m) * gamma
        - u_exit = c_acc / m_exit
        """
        duracion_total_min = 0.0
        por_etapa = {}
        
        # Token simulado para el seguimiento de masa y costos
        token_sim = TokenColoreado(
            orden_id="SIM",
            material=0.0,
            costo=0.0,
            v_target=v_target
        )
        
        # Obtener insumos de fórmula agrupados por etapa
        insumos_por_etapa = {}
        insumos_globales = []
        if formula and formula.insumos:
            for insumo in formula.insumos:
                factor_escala = (cantidad_lote / formula.cantidad_producir_lote) if formula.cantidad_producir_lote > 0 else 1.0
                cant_insumo = insumo.cantidad * factor_escala
                costo_insumo = cant_insumo * (insumo.costo_unitario_estimado or 0.0)
                
                if insumo.etapa_ruta_id:
                    if insumo.etapa_ruta_id not in insumos_por_etapa:
                        insumos_por_etapa[insumo.etapa_ruta_id] = {"masa": 0.0, "costo": 0.0}
                    insumos_por_etapa[insumo.etapa_ruta_id]["masa"] += cant_insumo
                    insumos_por_etapa[insumo.etapa_ruta_id]["costo"] += costo_insumo
                else:
                    insumos_globales.append({"masa": cant_insumo, "costo": costo_insumo})
                    
        for idx_etapa, (etapa, asig, conns) in enumerate(combinacion):
            recurso_base = asig.recurso
            recurso_eq = recurso_base.equipo if recurso_base else None
            
            # 1. Insumos de materia prima añadidos en esta etapa
            insumo_datos = insumos_por_etapa.get(etapa.id, {"masa": 0.0, "costo": 0.0})
            masa_adicional = insumo_datos["masa"]
            costo_materia_prima = insumo_datos["costo"]
            
            # Si es la primera etapa y hay insumos sin etapa asignada, cargarlos aquí
            if idx_etapa == 0 and insumos_globales:
                for g in insumos_globales:
                    masa_adicional += g["masa"]
                    costo_materia_prima += g["costo"]
            elif idx_etapa == 0 and masa_adicional == 0.0:
                # Fallback: si no hay fórmula detallada, usar la cantidad de la orden
                masa_adicional = cantidad_lote
            
            # 2. Costo de trasvase y conexiones previas
            costos_trasvase_etapa = 0.0
            perdida_trasvase_pct = 0.0
            
            for conn in conns:
                if conn.flujo_maximo_lps and conn.flujo_maximo_lps > 0:
                    tiempo_transvase_min = (max(token_sim.material, cantidad_lote) / conn.flujo_maximo_lps) / 60.0
                else:
                    tiempo_transvase_min = 5.0  # default 5 min
                
                duracion_total_min += tiempo_transvase_min
                tiempo_transvase_h = tiempo_transvase_min / 60.0
                
                costos_trasvase_etapa += (conn.longitud_metros or 0.0) * 0.2
                if conn.requiere_bombeo:
                    costos_trasvase_etapa += tiempo_transvase_h * 15.0
                if conn.requiere_operador:
                    costos_trasvase_etapa += tiempo_transvase_h * 50.0
                if conn.tipo == "MULTIPLEXOR":
                    costos_trasvase_etapa += 25.0
                    
                perdida_trasvase_pct += (conn.perdida_material_pct or 0.0)
                
            # Aplicar pérdida de trasvase al token
            if perdida_trasvase_pct > 0:
                token_sim.material *= max(0.0, 1.0 - perdida_trasvase_pct)
            token_sim.acumular_costo(costos_trasvase_etapa)
            
            # 3. Duración de la operación en máquina
            prep_min = asig.requiere_preparacion_min or 0.0
            limp_min = asig.requiere_limpieza_min or 0.0
            duracion_proc_min = asig.duracion_estimada_min or 0.0
            
            masa_en_etapa = token_sim.material + masa_adicional
            
            if asig.velocidad_procesamiento and asig.velocidad_procesamiento > 0:
                duracion_proc_min = masa_en_etapa / asig.velocidad_procesamiento
            elif recurso_eq and recurso_eq.velocidad_procesamiento and recurso_eq.velocidad_procesamiento > 0:
                duracion_proc_min = masa_en_etapa / recurso_eq.velocidad_procesamiento
                
            tiempo_operacion_min = duracion_proc_min + prep_min + limp_min
            duracion_total_min += tiempo_operacion_min
            tiempo_operacion_h = tiempo_operacion_min / 60.0
            
            # 4. Tasas de costo ABC: (kappa + omega + delta + mu) * EDR
            consumo_kw = recurso_eq.consumo_energia_kw if recurso_eq else 0.0
            costo_kwh = recurso_eq.costo_energia_por_kwh if recurso_eq else 0.0
            costo_depreciacion_h = recurso_eq.costo_depreciacion_hora if recurso_eq else 0.0
            
            edr = 1.0
            if recurso_eq and getattr(recurso_eq, 'medidor_energia', False):
                edr = getattr(recurso_eq, 'edr_actual', 1.0) or 1.0
            
            costo_energia = (consumo_kw * tiempo_operacion_h * costo_kwh) * edr
            costo_depreciacion = (costo_depreciacion_h * tiempo_operacion_h) * edr
            costo_mano_obra = (asig.costo_por_hora_real or 0.0) * tiempo_operacion_h
            costo_overhead = (12.0 * tiempo_operacion_h)
            
            costo_procesamiento = costo_energia + costo_depreciacion + costo_mano_obra + costo_overhead
            
            # Rendimiento operacional de la etapa (gamma)
            eficiencia_etapa = asig.eficiencia_real if (asig.eficiencia_real and asig.eficiencia_real > 0) else 1.0
            
            # 5. Transformación del token: masa, costo y absorción de merma
            token_sim.transformar_etapa(
                masa_adicionada=masa_adicional,
                costo_materia_prima=costo_materia_prima,
                costo_operativo=costo_procesamiento,
                rendimiento_gamma=eficiencia_etapa
            )
            
            por_etapa[etapa.nombre] = {
                "recurso_id": recurso_base.id,
                "recurso_nombre": recurso_base.nombre,
                "duracion_min": tiempo_operacion_min,
                "costo_materia_prima": costo_materia_prima,
                "costo_procesamiento": costo_procesamiento,
                "costo_trasvase": costos_trasvase_etapa,
                "costo_acumulado_etapa": token_sim.costo,
                "masa_acumulada_etapa": token_sim.material,
                "costo_unitario_etapa": token_sim.costo_unitario
            }
            
        return {
            "costo_total": token_sim.costo,
            "masa_salida": token_sim.material,
            "costo_unitario": token_sim.costo_unitario,
            "duracion_total_min": duracion_total_min,
            "por_etapa": por_etapa
        }