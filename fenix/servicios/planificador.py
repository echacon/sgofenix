"""
 Planificador Holónico de Producción y Enrutamiento Basado en Costos ABC (Sección V).
====================================================================================
Implementa la formalización matemática y algorítmica de la Sección V del artículo
IEEE Transactions on Industrial Informatics:

1. Retropropagación de Rendimiento y No-Monotonicidad (Ecuación 9 y Proposición 1):
   Para garantizar una masa final entregada q_n tras n etapas con rendimientos
   físicos gamma(E_i, R_i) in (0, 1], la masa inicial requerida en la etapa 1 es:
       m_0 = q_n / prod_{i=1..n} gamma(E_i, R_i)                          [Ec. 9]
   Por la Proposición 1 (Dependencia de Camino de los Estados de Costo), una merma
   en una etapa aguas abajo obliga a incrementar m_0, lo que incrementa tanto el
   costo de materia prima inicial C_raw(m_0) como las masas intermedias m_{k-1} y
   los tiempos de procesamiento dependientes de masa tau(E_k, R_k, m_{k-1}).

2. Función Objetivo de Optimización conjunta Tiempo-Costo (Ecuación 10):
       min_{pi in Pi_feas} J(pi) = C_raw(m_0) + sum_{i=1..n} (c_raw_add(E_i) + c_proc(E_i, R_i) + c_trans(R_{i-1}, R_i))
   sujeto a:
       - Conectividad física topológica K(R_{i-1}, R_i) = 1
       - Disponibilidad temporal en la agenda dinámica Psi_R y cumplimiento de fecha límite (EFT_n <= d)
       - Cota de viabilidad económica del lote: J(pi) <= V_target

3. Algoritmo 1 (Poda de Factibilidad en Dos Etapas y Búsqueda Branch-and-Bound):
   - Fase 0: Filtrado de rutas HolonRuta y composición selectiva de etapas E_P.
   - Fase 1: Poda de factibilidad topológica (conectividad K mediante BFS) y
     disponibilidad temporal sobre la agenda dinámica Psi_R (cálculo de EAT_k y EST_k).
   - Fase 2: Búsqueda Branch-and-Bound con cota inferior admisible (Lookahead Lower Bound, Ec. 11):
       LB(nu) = c_acc(nu) + sum_{j=k+1..n} (c_raw^min(E_j) + min_{R in R_cand(E_j)} Phi(E_j, R) * tau_min(E_j, R))
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from modelos.Producto import HolonRuta, AsignacionRecurso, Formula, InsumoFormula, Producto
from modelos.Recursos import Recurso, ConexionFisica, RecursoEquipo, RecursoPersonal
from modelos.Taxonomia import EtapaRuta
from utils.motor_abtppn import TokenColoreado


class PlanificadorProduccion:
    """
    Servicio de planificación holónica que ejecuta el Algoritmo 1 del artículo IEEE TII
    para seleccionar la ruta (HolonRuta) y la asignación óptima de recursos físicos
    minimizando el costo total ABC con absorción y retropropagación de mermas.
    """

    def __init__(self, session: Session):
        self.session = session

    def seleccionar_recursos_para_orden(
        self,
        producto_id: int,
        cantidad: float,
        prioridad: int,
        v_target: Optional[float] = None,
        deadline_min: Optional[float] = None,
        retropropagar_merma: bool = True,
        costo_mp_unitario: Optional[float] = None
    ) -> Optional[dict]:
        """
        Ejecuta el Algoritmo 1 (Two-Stage Feasibility Pruning & Branch-and-Bound):
        Evalúa los modelos de ruta (HolonRuta) activos para el producto, realiza la
        composición selectiva de etapas, aplica poda de factibilidad topológica (K) y
        temporal (agenda Psi_R y deadline d), y ejecuta Branch-and-Bound con la cota
        inferior admisible LB(nu) (Ec. 11) y retropropagación de mermas (Ec. 9).

        Args:
            producto_id (int): ID del producto (Product Holon PH).
            cantidad (float): Cantidad neta objetivo solicitada por la orden (q_n).
            prioridad (int): Prioridad de la orden de producción.
            v_target (Optional[float]): Cota máxima de viabilidad económica (V_target).
            deadline_min (Optional[float]): Horizonte temporal máximo permitido en minutos (d).
            retropropagar_merma (bool): Si es True (por defecto), aplica la Ec. (9)
                m_0 = q_n / prod(gamma_i) para garantizar que la masa final sea `cantidad`.
            costo_mp_unitario (Optional[float]): Costo unitario de materia prima base ($/kg)
                cuando no se detalla una tabla Formula explícita en base de datos.

        Returns:
            Optional[dict]: Diccionario con la ruta óptima, desglose ABC por etapa,
            masa inicial m_0, masa final m_n, costo unitario u_n y métricas de poda B&B,
            o None si ninguna ruta es física/temporal/económicamente factible.
        """
        # =====================================================================
        # FASE 0: Filtrado de Rutas (HolonRuta) y Composición Selectiva (E_P)
        # =====================================================================
        rutas = self.session.query(HolonRuta).filter(
            HolonRuta.producto_id == producto_id,
            HolonRuta.activa == True
        ).all()

        if not rutas:
            return None

        mejores_opciones_de_rutas = []
        estadisticas_busqueda = {
            "nodos_explorados": 0,
            "nodos_podados_conectividad": 0,
            "nodos_podados_deadline": 0,
            "nodos_podados_bb": 0
        }

        # Incumbente global de costo J* (inicializado en V_target si existe, o infinito)
        mejor_costo_global = v_target if (v_target is not None and v_target > 0) else float('inf')

        for ruta in rutas:
            condiciones = ruta.condiciones or {}

            # Verificar rango de tamaño de lote y prioridad mínima
            lote_min = condiciones.get('lote_minimo_kg', 0)
            lote_max = condiciones.get('lote_maximo_kg', float('inf'))
            if cantidad < lote_min or cantidad > lote_max:
                continue
            if prioridad < condiciones.get('prioridad_minima', 1):
                continue

            # Composición Selectiva de Etapas (E_P subset E)
            etapas_potenciales = self.session.query(EtapaRuta).filter(
                EtapaRuta.patronRuta_id == ruta.patron_id
            ).order_by(EtapaRuta.id).all()

            formula = self.session.query(Formula).filter(
                Formula.holon_ruta_id == ruta.id
            ).first()

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

            # Obtener candidatos de recursos asignables para cada etapa requerida
            recursos_por_etapa: Optional[Dict[int, List[AsignacionRecurso]]] = {}
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

            # =================================================================
            # FASE 1 y FASE 2: Poda de Factibilidad + Branch-and-Bound (Alg. 1)
            # =================================================================
            mejor_en_ruta = self._buscar_optimo_branch_and_bound(
                ruta=ruta,
                etapas=etapas_requeridas,
                recursos_por_etapa=recursos_por_etapa,
                cantidad_lote=cantidad,
                formula=formula,
                v_target=v_target,
                deadline_min=deadline_min,
                retropropagar_merma=retropropagar_merma,
                costo_mp_unitario=costo_mp_unitario,
                cota_incumbente=mejor_costo_global,
                stats=estadisticas_busqueda
            )

            if mejor_en_ruta is not None:
                if mejor_en_ruta["costo_total"] <= mejor_costo_global:
                    mejor_costo_global = mejor_en_ruta["costo_total"]
                mejores_opciones_de_rutas.append(mejor_en_ruta)

        if not mejores_opciones_de_rutas:
            return None

        # Seleccionar la mejor opción absoluta (mínimo costo global J(pi))
        mejor_opcion = min(mejores_opciones_de_rutas, key=lambda x: x["costo_total"])

        return {
            "holon_ruta_id": mejor_opcion["holon_ruta_id"],
            "holon_ruta_nombre": mejor_opcion["holon_ruta_nombre"],
            "costo_total": mejor_opcion["costo_total"],
            "masa_inicial": mejor_opcion["masa_inicial"],
            "masa_salida": mejor_opcion["masa_salida"],
            "costo_unitario": mejor_opcion["costo_unitario"],
            "duracion_total_min": mejor_opcion["duracion_total_min"],
            "makespan_min": mejor_opcion["makespan_min"],
            "asignacion": mejor_opcion["asignacion"],
            "estadisticas_bb": estadisticas_busqueda
        }

    # =========================================================================
    # MÉTODOS AUXILIARES DEL ALGORITMO 1 (SECCIÓN V)
    # =========================================================================

    @staticmethod
    def _obtener_rendimiento_gamma(asig: AsignacionRecurso, recurso_eq: Optional[RecursoEquipo]) -> float:
        """
        Obtiene el factor de rendimiento másico gamma(E_i, R_i) in (0, 1] (Ec. 2 y Ec. 3).
        Separa estrictamente la merma física (`rendimiento_gamma` / `rendimiento_nominal`)
        de la eficiencia temporal (`eficiencia_real`).
        """
        gamma_asig = getattr(asig, 'rendimiento_gamma', None)
        gamma_eq = getattr(recurso_eq, 'rendimiento_nominal', None) if recurso_eq else None

        if gamma_asig is not None and 0.0 < gamma_asig < 1.0:
            return float(gamma_asig)
        if gamma_eq is not None and 0.0 < gamma_eq <= 1.0:
            return float(gamma_eq)
        if gamma_asig is not None and 0.0 < gamma_asig <= 1.0:
            return float(gamma_asig)
        return 1.0

    @staticmethod
    def _obtener_tasa_horaria_abc(asig: AsignacionRecurso, recurso_eq: Optional[RecursoEquipo]) -> float:
        """
        Calcula la tasa horaria compuesta ABC del recurso Phi(E_i, R_i) en $/hora
        según la Ecuación (6) y la línea 34 del Algoritmo 1:
            Phi(E_i, R_i) = kappa_R^eff + omega_R + delta_R + mu_R
        donde:
            - kappa_R^eff = EDR(R) * (consumo_kw * costo_kwh)   [Ec. 15: EDR solo afecta energía]
            - omega_R = costo_por_hora_real                     [Mano de obra directa]
            - delta_R = costo_depreciacion_hora                 [Depreciación de máquina]
            - mu_R = costo_overhead_hora                        [Overhead de planta asignado]
        """
        consumo_kw = (recurso_eq.consumo_energia_kw or 0.0) if recurso_eq else 0.0
        costo_kwh = (recurso_eq.costo_energia_por_kwh or 0.0) if recurso_eq else 0.0
        delta_r = (recurso_eq.costo_depreciacion_hora or 0.0) if recurso_eq else 0.0

        edr = 1.0
        if recurso_eq and getattr(recurso_eq, 'medidor_energia', False):
            edr = getattr(recurso_eq, 'edr_actual', 1.0) or 1.0

        # Ecuación (15): kappa_R^eff = EDR(R) * kappa(R)
        kappa_eff = (consumo_kw * costo_kwh) * edr
        omega_r = asig.costo_por_hora_real or 0.0

        # Tasa de overhead mu_R tomada del modelo RecursoEquipo (por defecto 12.0 $/h)
        mu_r = 12.0
        if recurso_eq and getattr(recurso_eq, 'costo_overhead_hora', None) is not None:
            mu_r = float(recurso_eq.costo_overhead_hora)

        return kappa_eff + omega_r + delta_r + mu_r

    @staticmethod
    def _estimar_duracion_operacion_min(asig: AsignacionRecurso,
                                        recurso_eq: Optional[RecursoEquipo],
                                        masa_en_etapa: float) -> float:
        """
        Calcula la duración efectiva de operación tau(E_i, R_i, m) en minutos,
        ajustada por el factor de eficiencia temporal calibrado por EWMA (`eficiencia_real`).
        """
        prep_min = asig.requiere_preparacion_min or 0.0
        limp_min = asig.requiere_limpieza_min or 0.0
        duracion_proc_min = asig.duracion_estimada_min or 0.0

        if asig.velocidad_procesamiento and asig.velocidad_procesamiento > 0:
            duracion_proc_min = masa_en_etapa / asig.velocidad_procesamiento
        elif recurso_eq and recurso_eq.velocidad_procesamiento and recurso_eq.velocidad_procesamiento > 0:
            duracion_proc_min = masa_en_etapa / recurso_eq.velocidad_procesamiento

        # Ajuste por eficiencia temporal histórica (EWMA de duración, Ec. 12)
        eficiencia_temp = asig.eficiencia_real if (asig.eficiencia_real and asig.eficiencia_real > 0) else 1.0
        duracion_proc_ajustada = duracion_proc_min / eficiencia_temp

        return duracion_proc_ajustada + prep_min + limp_min

    @staticmethod
    def _calcular_ventana_agenda(recurso: Optional[Recurso],
                                 eat_min: float,
                                 duracion_min: float) -> Tuple[float, float]:
        """
        Fase 1b del Algoritmo 1: Verifica la agenda dinámica Psi_R del recurso
        para determinar el Tiempo de Inicio Más Temprano (EST_k >= EAT_k) y el
        Tiempo de Finalización Más Temprano (EFT_k = EST_k + duracion_min).

        Soporta intervalos ocupados en `recurso.agenda` con formato:
            [{"inicio_min": float, "fin_min": float}, ...]
        o diccionario {"intervalos_ocupados": [{"inicio_min": ..., "fin_min": ...}]}.
        """
        est_min = max(0.0, eat_min)
        if not recurso or not recurso.agenda:
            return est_min, est_min + duracion_min

        agenda = recurso.agenda
        intervalos = []
        if isinstance(agenda, list):
            intervalos = agenda
        elif isinstance(agenda, dict):
            intervalos = agenda.get("intervalos_ocupados", agenda.get("reservas", []))

        # Ordenar intervalos ocupados por inicio_min
        intervalos_validos = []
        for slot in intervalos:
            if isinstance(slot, dict) and "inicio_min" in slot and "fin_min" in slot:
                try:
                    ini = float(slot["inicio_min"])
                    fin = float(slot["fin_min"])
                    if fin > ini:
                        intervalos_validos.append((ini, fin))
                except (TypeError, ValueError):
                    continue

        intervalos_validos.sort(key=lambda x: x[0])

        # Buscar el primer hueco donde [est_min, est_min + duracion_min] no se solape
        for ini, fin in intervalos_validos:
            if est_min + duracion_min <= ini:
                break
            if est_min < fin and (est_min + duracion_min) > ini:
                est_min = fin

        return est_min, est_min + duracion_min

    def _buscar_camino_trasvase(self, origen_id: int, destino_id: int) -> Optional[List[ConexionFisica]]:
        """
        Fase 1a del Algoritmo 1: Verifica la conectividad física topológica K(R_{k-1}, R_k)
        buscando el camino más corto de conexiones físicas activas y disponibles (BFS).
        Retorna la lista de conexiones que componen el camino, o None si K = 0.
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

    def _generar_combinaciones_validas(
        self,
        etapas: List[EtapaRuta],
        recursos_por_etapa: Dict[int, List[AsignacionRecurso]]
    ) -> List[List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]]]:
        """
        Genera todas las combinaciones de recursos físicamente conectadas (Fase 1a).
        Mantenido por compatibilidad con llamadas directas o pruebas unitarias.
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

    def _precalcular_cotas_inferiores_etapas(
        self,
        etapas: List[EtapaRuta],
        recursos_por_etapa: Dict[int, List[AsignacionRecurso]],
        cantidad_lote: float,
        formula: Optional[Formula] = None,
        costo_mp_unitario: Optional[float] = None
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Precalcula para cada etapa j in {0..n-1} los valores optimistas para la
        cota inferior admisible LB(nu) de la Ecuación (11):
            - sufijo_costo_min[k]: sum_{j=k..n-1} (c_raw^min(E_j) + min_R Phi(E_j, R) * tau_min(E_j, R))
            - sufijo_tiempo_min[k]: sum_{j=k..n-1} tau_min(E_j, R)
            - sufijo_gamma_max[k]: prod_{j=k..n-1} max_R gamma(E_j, R)
        """
        n = len(etapas)
        costo_min_etapa = [0.0] * n
        tiempo_min_etapa = [0.0] * n
        gamma_max_etapa = [1.0] * n

        # Costos nominales de insumos por etapa (sin retropropagación, cota inferior admisible)
        insumos_etapa_costo = {}
        costo_global_mp = 0.0
        if formula and formula.insumos:
            factor_escala = (cantidad_lote / formula.cantidad_producir_lote) if formula.cantidad_producir_lote > 0 else 1.0
            for insumo in formula.insumos:
                c_ins = (insumo.cantidad * factor_escala) * (insumo.costo_unitario_estimado or 0.0)
                if insumo.etapa_ruta_id:
                    insumos_etapa_costo[insumo.etapa_ruta_id] = insumos_etapa_costo.get(insumo.etapa_ruta_id, 0.0) + c_ins
                else:
                    costo_global_mp += c_ins
        elif costo_mp_unitario is not None and costo_mp_unitario > 0:
            costo_global_mp = cantidad_lote * costo_mp_unitario

        for j, etapa in enumerate(etapas):
            asigs = recursos_por_etapa.get(etapa.id, [])
            min_c_proc = float('inf')
            min_t_proc = float('inf')
            max_gamma = 0.0

            for asig in asigs:
                rec_base = asig.recurso
                rec_eq = rec_base.equipo if rec_base else None
                # Masa mínima optimista en la etapa para cota inferior admisible
                masa_min_optimista = cantidad_lote if j == n - 1 else 0.0
                tau_min_r = self._estimar_duracion_operacion_min(asig, rec_eq, masa_min_optimista)
                phi_r = self._obtener_tasa_horaria_abc(asig, rec_eq)
                c_proc_r = phi_r * (tau_min_r / 60.0)
                gamma_r = self._obtener_rendimiento_gamma(asig, rec_eq)

                if c_proc_r < min_c_proc:
                    min_c_proc = c_proc_r
                if tau_min_r < min_t_proc:
                    min_t_proc = tau_min_r
                if gamma_r > max_gamma:
                    max_gamma = gamma_r

            c_raw_min_j = insumos_etapa_costo.get(etapa.id, 0.0)
            if j == 0:
                c_raw_min_j += costo_global_mp

            costo_min_etapa[j] = c_raw_min_j + (min_c_proc if min_c_proc != float('inf') else 0.0)
            tiempo_min_etapa[j] = min_t_proc if min_t_proc != float('inf') else 0.0
            gamma_max_etapa[j] = max_gamma if max_gamma > 0.0 else 1.0

        # Sumas/productos sufijos desde k hasta n-1
        sufijo_costo_min = [0.0] * (n + 1)
        sufijo_tiempo_min = [0.0] * (n + 1)
        sufijo_gamma_max = [1.0] * (n + 1)

        for k in range(n - 1, -1, -1):
            sufijo_costo_min[k] = costo_min_etapa[k] + sufijo_costo_min[k + 1]
            sufijo_tiempo_min[k] = tiempo_min_etapa[k] + sufijo_tiempo_min[k + 1]
            sufijo_gamma_max[k] = gamma_max_etapa[k] * sufijo_gamma_max[k + 1]

        return sufijo_costo_min, sufijo_tiempo_min, sufijo_gamma_max

    def _buscar_optimo_branch_and_bound(
        self,
        ruta: HolonRuta,
        etapas: List[EtapaRuta],
        recursos_por_etapa: Dict[int, List[AsignacionRecurso]],
        cantidad_lote: float,
        formula: Optional[Formula],
        v_target: Optional[float],
        deadline_min: Optional[float],
        retropropagar_merma: bool,
        costo_mp_unitario: Optional[float],
        cota_incumbente: float,
        stats: Dict[str, int]
    ) -> Optional[dict]:
        """
        Implementa las Fases 1 y 2 del Algoritmo 1:
        Recorre el árbol de asignaciones etapa por etapa aplicando:
          - Poda Topológica (Fase 1a): K(R_{k-1}, R_k) mediante `_buscar_camino_trasvase`.
          - Poda Temporal (Fase 1b): Agenda dinámica Psi_R (EAT_k, EST_k, EFT_k) y cota `deadline_min`.
          - Poda Económica Branch-and-Bound (Fase 2, Ec. 11):
                LB(nu) = c_acc_optimista(nu) + sufijo_costo_min[k + 1] > J*
        En las hojas (k == n), evalúa la función objetivo exacta J(pi) (Ec. 10) con
        retropropagación completa de mermas m_0 = q_n / prod(gamma_i) (Ec. 9).
        """
        n = len(etapas)
        sufijo_costo_min, sufijo_tiempo_min, sufijo_gamma_max = self._precalcular_cotas_inferiores_etapas(
            etapas, recursos_por_etapa, cantidad_lote, formula, costo_mp_unitario
        )

        # Costo base nominal de materia prima para la cota inferior admisible
        costo_mp_base = 0.0
        if formula and formula.insumos:
            factor_escala = (cantidad_lote / formula.cantidad_producir_lote) if formula.cantidad_producir_lote > 0 else 1.0
            for insumo in formula.insumos:
                costo_mp_base += (insumo.cantidad * factor_escala) * (insumo.costo_unitario_estimado or 0.0)
        elif costo_mp_unitario is not None and costo_mp_unitario > 0:
            costo_mp_base = cantidad_lote * costo_mp_unitario

        mejor_solucion = None
        mejor_costo = cota_incumbente

        def expandir(
            k: int,
            camino_actual: List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]],
            eft_anterior_min: float,
            costo_proc_acum_min: float,
            gamma_acum: float
        ):
            nonlocal mejor_solucion, mejor_costo

            # Caso base (hoja del árbol): todas las etapas tienen recurso asignado
            if k == n:
                evaluacion = self._evaluar_combinacion(
                    combinacion=camino_actual,
                    cantidad_lote=cantidad_lote,
                    formula=formula,
                    v_target=v_target,
                    retropropagar_merma=retropropagar_merma,
                    costo_mp_unitario=costo_mp_unitario
                )

                # Verificar deadline exacto con masas retropropagadas si aplica
                if deadline_min is not None and evaluacion["makespan_min"] > deadline_min:
                    stats["nodos_podados_deadline"] += 1
                    return

                # Verificar cota de viabilidad V_target y actualizar incumbente J*
                if evaluacion["costo_total"] <= mejor_costo:
                    mejor_costo = evaluacion["costo_total"]
                    mejor_solucion = {
                        "holon_ruta_id": ruta.id,
                        "holon_ruta_nombre": ruta.nombre,
                        "combinacion": camino_actual,
                        "costo_total": evaluacion["costo_total"],
                        "masa_inicial": evaluacion["masa_inicial"],
                        "masa_salida": evaluacion["masa_salida"],
                        "costo_unitario": evaluacion["costo_unitario"],
                        "duracion_total_min": evaluacion["duracion_total_min"],
                        "makespan_min": evaluacion["makespan_min"],
                        "asignacion": evaluacion["por_etapa"]
                    }
                else:
                    stats["nodos_podados_bb"] += 1
                return

            etapa = etapas[k]
            candidatos = recursos_por_etapa.get(etapa.id, [])

            for asig in candidatos:
                stats["nodos_explorados"] += 1
                recurso_base = asig.recurso
                recurso_eq = recurso_base.equipo if recurso_base else None

                # -------------------------------------------------------------
                # FASE 1a: Poda por Conectividad Topológica K(R_{k-1}, R_k)
                # -------------------------------------------------------------
                conexiones: List[ConexionFisica] = []
                tiempo_trasvase_min = 0.0
                costo_trasvase_min = 0.0
                factor_conservacion_trasvase = 1.0

                if k > 0:
                    _, asig_ant, _ = camino_actual[-1]
                    camino_conns = self._buscar_camino_trasvase(asig_ant.recurso_id, asig.recurso_id)
                    if camino_conns is None:
                        stats["nodos_podados_conectividad"] += 1
                        continue
                    conexiones = camino_conns
                    for conn in conexiones:
                        t_conn = (cantidad_lote / conn.flujo_maximo_lps) / 60.0 if (conn.flujo_maximo_lps and conn.flujo_maximo_lps > 0) else 5.0
                        tiempo_trasvase_min += t_conn
                        t_conn_h = t_conn / 60.0
                        costo_trasvase_min += (conn.longitud_metros or 0.0) * 0.2
                        if conn.requiere_bombeo:
                            costo_trasvase_min += t_conn_h * 15.0
                        if conn.requiere_operador:
                            costo_trasvase_min += t_conn_h * 50.0
                        if conn.tipo == "MULTIPLEXOR":
                            costo_trasvase_min += 25.0
                        factor_conservacion_trasvase *= max(0.0001, 1.0 - (conn.perdida_material_pct or 0.0))

                # -------------------------------------------------------------
                # FASE 1b: Poda por Disponibilidad Temporal en Agenda Psi_R
                # -------------------------------------------------------------
                eat_k = eft_anterior_min + tiempo_trasvase_min
                tau_k_min = self._estimar_duracion_operacion_min(asig, recurso_eq, cantidad_lote)
                est_k, eft_k = self._calcular_ventana_agenda(recurso_base, eat_k, tau_k_min)

                if deadline_min is not None and (eft_k + sufijo_tiempo_min[k + 1]) > deadline_min:
                    stats["nodos_podados_deadline"] += 1
                    continue

                # -------------------------------------------------------------
                # FASE 2: Poda Branch-and-Bound mediante Cota Inferior LB(nu) (Ec. 11)
                # -------------------------------------------------------------
                gamma_k = self._obtener_rendimiento_gamma(asig, recurso_eq) * factor_conservacion_trasvase
                nuevo_gamma_acum = gamma_acum * gamma_k

                phi_k = self._obtener_tasa_horaria_abc(asig, recurso_eq)
                c_proc_k_min = phi_k * (tau_k_min / 60.0)
                nuevo_costo_proc_acum = costo_proc_acum_min + costo_trasvase_min + c_proc_k_min

                # Cota inferior de materia prima considerando el rendimiento máximo alcanzable en el sufijo
                gamma_total_optimista = max(0.0001, nuevo_gamma_acum * sufijo_gamma_max[k + 1])
                factor_merma_optimista = (1.0 / gamma_total_optimista) if retropropagar_merma else 1.0
                c_raw_lb = costo_mp_base * factor_merma_optimista

                # Ecuación (11): LB(nu) = c_acc(nu) + sum_{j=k+1..n} c_min(E_j)
                # (sufijo_costo_min[k+1] incluye los costos mínimos de procesamiento de las etapas restantes)
                costo_proc_restante_lb = 0.0
                for j_rem in range(k + 1, n):
                    etapa_rem = etapas[j_rem]
                    asigs_rem = recursos_por_etapa.get(etapa_rem.id, [])
                    if asigs_rem:
                        min_cp = min(
                            self._obtener_tasa_horaria_abc(a_r, a_r.recurso.equipo if a_r.recurso else None) *
                            (self._estimar_duracion_operacion_min(a_r, a_r.recurso.equipo if a_r.recurso else None, cantidad_lote) / 60.0)
                            for a_r in asigs_rem
                        )
                        costo_proc_restante_lb += min_cp

                lb_nu = c_raw_lb + nuevo_costo_proc_acum + costo_proc_restante_lb

                if lb_nu > mejor_costo:
                    stats["nodos_podados_bb"] += 1
                    continue

                expandir(
                    k=k + 1,
                    camino_actual=camino_actual + [(etapa, asig, conexiones)],
                    eft_anterior_min=eft_k,
                    costo_proc_acum_min=nuevo_costo_proc_acum,
                    gamma_acum=nuevo_gamma_acum
                )

        expandir(0, [], 0.0, 0.0, 1.0)
        return mejor_solucion

    def _evaluar_combinacion(
        self,
        combinacion: List[Tuple[EtapaRuta, AsignacionRecurso, List[ConexionFisica]]],
        cantidad_lote: float,
        formula: Optional[Formula] = None,
        v_target: Optional[float] = None,
        retropropagar_merma: bool = True,
        costo_mp_unitario: Optional[float] = None
    ) -> dict:
        """
        Evalúa de forma exacta una secuencia completa de asignaciones (Ecuaciones 5 a 10):
        1. Calcula el factor de rendimiento acumulado de la ruta:
               Gamma_ruta = prod_{i=1..n} ((1 - perdida_trasvase_i) * gamma(E_i, R_i))
        2. Si `retropropagar_merma=True` (Ec. 9 y Proposición 1), escala la masa
           de entrada por 1 / Gamma_ruta:
               m_0 = q_n / prod_{i=1..n} gamma(E_i, R_i)
           garantizando que la masa final entregada a la salida de la etapa n sea `cantidad_lote` (q_n).
        3. Propaga el `TokenColoreado` etapa por etapa calculando:
           - Ventanas temporales reales en la agenda dinámica Psi_R (EAT_i, EST_i, EFT_i).
           - Tasa ABC compuesta (Ec. 6 y Ec. 15):
                 c_proc(E_i, R_i) = (EDR(R_i)*kappa_{R_i} + omega_{R_i} + delta_{R_i} + mu_{R_i}) * tau(E_i, R_i)
           - Costo acumulado c_acc (Ec. 7) y costo unitario con absorción de merma u = c_acc / m (Ec. 8).
        """
        duracion_total_min = 0.0
        reloj_planta_min = 0.0
        por_etapa = {}

        # ---------------------------------------------------------------------
        # Paso 1: Calcular rendimiento acumulado prod_{i=1..n} gamma(E_i, R_i) (Ec. 9)
        # ---------------------------------------------------------------------
        producto_gamma = 1.0
        for _, asig, conns in combinacion:
            recurso_base = asig.recurso
            recurso_eq = recurso_base.equipo if recurso_base else None
            perdida_trasvase_pct = sum((c.perdida_material_pct or 0.0) for c in conns)
            factor_trasvase = max(0.0001, 1.0 - perdida_trasvase_pct)
            gamma_etapa = self._obtener_rendimiento_gamma(asig, recurso_eq)
            producto_gamma *= (factor_trasvase * gamma_etapa)

        factor_retropropagacion = (1.0 / max(0.0001, producto_gamma)) if retropropagar_merma else 1.0
        masa_inicial_requerida = cantidad_lote * factor_retropropagacion

        # Token simulado para el seguimiento físico y contable del lote (Ec. 4)
        token_sim = TokenColoreado(
            orden_id="SIM",
            material=0.0,
            costo=0.0,
            v_target=v_target
        )

        # ---------------------------------------------------------------------
        # Paso 2: Agrupar insumos de fórmula por etapa (escalados por retropropagación)
        # ---------------------------------------------------------------------
        insumos_por_etapa = {}
        insumos_globales = []
        if formula and formula.insumos:
            escala_base = (cantidad_lote / formula.cantidad_producir_lote) if formula.cantidad_producir_lote > 0 else 1.0
            factor_escala = escala_base * factor_retropropagacion
            for insumo in formula.insumos:
                cant_insumo = insumo.cantidad * factor_escala
                costo_insumo = cant_insumo * (insumo.costo_unitario_estimado or 0.0)

                if insumo.etapa_ruta_id:
                    if insumo.etapa_ruta_id not in insumos_por_etapa:
                        insumos_por_etapa[insumo.etapa_ruta_id] = {"masa": 0.0, "costo": 0.0}
                    insumos_por_etapa[insumo.etapa_ruta_id]["masa"] += cant_insumo
                    insumos_por_etapa[insumo.etapa_ruta_id]["costo"] += costo_insumo
                else:
                    insumos_globales.append({"masa": cant_insumo, "costo": costo_insumo})

        # ---------------------------------------------------------------------
        # Paso 3: Simulación hacia adelante a lo largo de la ruta (Ecs. 5-8)
        # ---------------------------------------------------------------------
        for idx_etapa, (etapa, asig, conns) in enumerate(combinacion):
            recurso_base = asig.recurso
            recurso_eq = recurso_base.equipo if recurso_base else None

            # 1. Insumos de materia prima añadidos en esta etapa
            insumo_datos = insumos_por_etapa.get(etapa.id, {"masa": 0.0, "costo": 0.0})
            masa_adicional = insumo_datos["masa"]
            costo_materia_prima = insumo_datos["costo"]

            if idx_etapa == 0 and insumos_globales:
                for g in insumos_globales:
                    masa_adicional += g["masa"]
                    costo_materia_prima += g["costo"]
            elif idx_etapa == 0 and masa_adicional == 0.0:
                # Si no hay fórmula detallada, la masa inicial es m_0 = q_n / prod(gamma_i) (Ec. 9)
                masa_adicional = masa_inicial_requerida
                if costo_mp_unitario is not None and costo_mp_unitario > 0:
                    costo_materia_prima = masa_inicial_requerida * costo_mp_unitario

            # 2. Costo y tiempo de trasvase por conexiones físicas previas
            costos_trasvase_etapa = 0.0
            perdida_trasvase_pct = 0.0
            tiempo_trasvase_etapa_min = 0.0

            for conn in conns:
                masa_flujo = max(token_sim.material, cantidad_lote)
                if conn.flujo_maximo_lps and conn.flujo_maximo_lps > 0:
                    tiempo_transvase_min = (masa_flujo / conn.flujo_maximo_lps) / 60.0
                else:
                    tiempo_transvase_min = 5.0  # default 5 min

                duracion_total_min += tiempo_transvase_min
                tiempo_trasvase_etapa_min += tiempo_transvase_min
                tiempo_transvase_h = tiempo_transvase_min / 60.0

                costos_trasvase_etapa += (conn.longitud_metros or 0.0) * 0.2
                if conn.requiere_bombeo:
                    costos_trasvase_etapa += tiempo_transvase_h * 15.0
                if conn.requiere_operador:
                    costos_trasvase_etapa += tiempo_transvase_h * 50.0
                if conn.tipo == "MULTIPLEXOR":
                    costos_trasvase_etapa += 25.0

                perdida_trasvase_pct += (conn.perdida_material_pct or 0.0)

            if perdida_trasvase_pct > 0:
                token_sim.material *= max(0.0, 1.0 - perdida_trasvase_pct)
            token_sim.acumular_costo(costos_trasvase_etapa)

            # 3. Duración de la operación en máquina tau(E_i, R_i, m_{i-1})
            masa_en_etapa = token_sim.material + masa_adicional
            tiempo_operacion_min = self._estimar_duracion_operacion_min(asig, recurso_eq, masa_en_etapa)
            duracion_total_min += tiempo_operacion_min
            tiempo_operacion_h = tiempo_operacion_min / 60.0

            # Ventana temporal sobre la agenda dinámica Psi_R (EAT_i, EST_i, EFT_i)
            eat_i = reloj_planta_min + tiempo_trasvase_etapa_min
            est_i, eft_i = self._calcular_ventana_agenda(recurso_base, eat_i, tiempo_operacion_min)
            reloj_planta_min = eft_i

            # 4. Tasas de costo ABC (Ecuación 6 y Ecuación 15):
            #    c_proc = (EDR(R)*kappa_R + omega_R + delta_R + mu_R) * tau(E_i, R_i)
            tasa_abc_hora = self._obtener_tasa_horaria_abc(asig, recurso_eq)
            costo_procesamiento = tasa_abc_hora * tiempo_operacion_h

            # Rendimiento físico de la etapa gamma(E_i, R_i) in (0, 1]
            gamma_etapa = self._obtener_rendimiento_gamma(asig, recurso_eq)

            # 5. Transformación formal del token (Ecuaciones 5, 7 y 8)
            token_sim.transformar_etapa(
                masa_adicionada=masa_adicional,
                costo_materia_prima=costo_materia_prima,
                costo_operativo=costo_procesamiento,
                rendimiento_gamma=gamma_etapa
            )

            por_etapa[etapa.nombre] = {
                "recurso_id": recurso_base.id,
                "recurso_nombre": recurso_base.nombre,
                "duracion_min": tiempo_operacion_min,
                "eat_min": eat_i,
                "est_min": est_i,
                "eft_min": eft_i,
                "rendimiento_gamma": gamma_etapa,
                "costo_materia_prima": costo_materia_prima,
                "costo_procesamiento": costo_procesamiento,
                "costo_trasvase": costos_trasvase_etapa,
                "costo_acumulado_etapa": token_sim.costo,
                "masa_acumulada_etapa": token_sim.material,
                "costo_unitario_etapa": token_sim.costo_unitario
            }

        return {
            "costo_total": token_sim.costo,
            "masa_inicial": masa_inicial_requerida,
            "masa_salida": token_sim.material,
            "costo_unitario": token_sim.costo_unitario,
            "duracion_total_min": duracion_total_min,
            "makespan_min": reloj_planta_min,
            "por_etapa": por_etapa
        }
