# utils/motor_abtppn.py - Motor de Ejecución de Redes de Petri AB-TPPN

"""
Motor de Redes de Petri Temporizadas Basadas en Actividades (AB-TPPN).
======================================================================
Implementa el formalismo matemático definido en la Sección IV del artículo
IEEE Transactions on Industrial Informatics:

Definición 1 (AB-TPPN):
    Una Red de Petri Temporizada de Procesos Basada en Actividades (AB-TPPN) se
    define mediante la 7-tupla:
        N = <P, T, F, tau, Phi, Q, M_0>
    donde:
    - P = P_proc U P_ctrl U P_res: Conjunto finito de lugares (etapas de proceso,
      estados de control/sincronización y disponibilidad de recursos).
    - T = T_auto U T_200 U T_201 U T_202: Conjunto finito de transiciones particionado
      por tipo de disparo (trigger):
        * T_auto (None): Transiciones automáticas inmediatas.
        * T_200 ('200'): Transiciones sincronizadas por eventos externos de planta (SCADA/HMI).
        * T_201 ('201'): Transiciones de sincronización inter-red por paso de mensajes (PPR).
        * T_202 ('202'): Transiciones temporizadas (watchdog / timeout).
    - F subset (P x T) U (T x P): Relación de flujo (arcos dirigidos).
    - tau: P_proc -> R+ : Función de tiempo de residencia asociado a los lugares de proceso.
    - Phi: P_proc -> R+ : Función de tasa de acumulación de costo ABC en cada lugar activo.
    - Q: T_201 -> T_201 : Función de acoplamiento síncrono/asíncrono de paso de mensajes
      entre la Red de Integración (N_E) y las Redes de Servicio de los Recursos (N_S).
    - M_0: Marcado inicial de la red.

Estado del Token Coloreado (Ecuación 4):
    Cada orden de producción circula como un token coloreado estructurado:
        k = <lot_id, m, c_acc, raw_add, t_arr, V_target>
    y mantiene explícitamente el costo unitario con absorción de mermas (u = c_acc / m).

Reglas de Evolución Contable y Física al Disparar Transiciones (Ecuaciones 5-8):
    - Ecuación (5) [Balance de Masa con Rendimiento]:
        m_exit = (m_enter + delta_m_raw) * gamma(p, R)
    - Ecuación (6) [Costo de Procesamiento ABC en la Etapa]:
        c_proc(p, R) = (kappa_R^eff + omega_R + delta_R + mu_R) * tau(p, R)
    - Ecuación (7) [Costo Total Acumulado del Lote]:
        c_acc_exit = c_acc_enter + c_raw(p) + c_proc(p, R)
    - Ecuación (8) [Absorción de Merma en el Costo Unitario]:
        u_exit = c_acc_exit / m_exit = (c_acc_enter + c_raw(p) + c_proc(p, R)) / ((m_enter + delta_m_raw) * gamma(p, R))
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TokenColoreado:
    """
    Token coloreado que transporta el estado físico (masa/volumen) y contable (ABC)
    de la orden de producción (Work-In-Progress, WIP) a través de la red AB-TPPN.

    Formalización (Ecuación 4):
        k = <lot_id, m, c_acc, raw_add, t_arr, V_target>

    Atributos:
        orden_id (str): Identificador único del lote u orden (lot_id).
        material (float): Masa o volumen actual de producto en proceso (m).
        costo (float): Costo total acumulado del lote hasta la etapa actual (c_acc).
        timestamp (Optional[datetime]): Marca de tiempo de llegada/última transición (t_arr).
        v_target (Optional[float]): Cota máxima de viabilidad económica del lote (V_target).
        costo_unitario (float): Costo por unidad de masa saliente con absorción de mermas (u = c_acc / m).
        coste (float): Alias retrocompatible de `costo`.
    """
    orden_id: str
    material: float                          # Masa o volumen actual (m)
    costo: float = 0.0                       # Costo acumulado del lote c_acc
    timestamp: Optional[datetime] = None     # Marca de tiempo de llegada / último evento (t_arr)
    v_target: Optional[float] = None         # Cota máxima de viabilidad económica (V_target)
    costo_unitario: float = 0.0              # Costo unitario con absorción de mermas (u = c_acc / m)
    coste: float = 0.0                       # Alias retrocompatible

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        # Sincronizar alias coste y costo
        if self.costo == 0.0 and self.coste != 0.0:
            self.costo = self.coste
        else:
            self.coste = self.costo
        self.actualizar_costo_unitario()

    def actualizar_costo_unitario(self) -> float:
        """
        Calcula el costo unitario con absorción de mermas según la Ecuación (8):
            u = c_acc / m
        """
        if self.material and self.material > 0:
            self.costo_unitario = self.costo / self.material
        else:
            self.costo_unitario = 0.0
        return self.costo_unitario

    def acumular_costo(self, delta_costo: float):
        """
        Incrementa el costo acumulado del lote (c_acc) por procesamiento ABC,
        energía, mano de obra o transporte, y recalcula u = c_acc / m.
        """
        self.costo += delta_costo
        self.coste = self.costo
        self.actualizar_costo_unitario()

    def transformar_etapa(self, masa_adicionada: float = 0.0, costo_materia_prima: float = 0.0,
                          costo_operativo: float = 0.0, rendimiento_gamma: float = 1.0):
        """
        Aplica la transformación termodinámica y contable de una etapa de proceso (Ecs. 5-8):
        1. Balance de masa con adición secundaria y factor de rendimiento (Ec. 5):
               m_exit = (m_enter + delta_m_raw) * gamma(p, R)
        2. Acumulación de costos de materia prima y procesamiento ABC (Ec. 6 y Ec. 7):
               c_acc_exit = c_acc_enter + c_raw(p) + c_proc(p, R)
        3. Absorción de la merma física en el costo unitario saliente (Ec. 8):
               u_exit = c_acc_exit / m_exit
        """
        masa_total_in = self.material + max(0.0, masa_adicionada)
        gamma = max(0.0001, min(1.0, rendimiento_gamma))
        self.material = masa_total_in * gamma
        
        delta_costo = max(0.0, costo_materia_prima) + max(0.0, costo_operativo)
        self.acumular_costo(delta_costo)

    def es_economicamente_viable(self) -> bool:
        """
        Verifica el invariante de viabilidad económica del lote:
            c_acc <= V_target
        """
        if self.v_target is not None and self.v_target > 0:
            return self.costo <= self.v_target
        return True


@dataclass
class InstanciaRedMem:
    """
    Representación en memoria de una instancia activa de una red AB-TPPN
    (ya sea la Red de Integración N_E de un Producto o una Red de Servicio N_S
    de un Recurso) asociada a una orden de producción en curso.
    """
    
    def __init__(self, id: int, red_nombre: str, orden_id: int,
                 marcado: dict, token: TokenColoreado, pnml_path: str = None):
        self.id = id
        self.red_nombre = red_nombre
        self.orden_id = orden_id
        import json
        if isinstance(marcado, str):
            marcado = json.loads(marcado)
        self.marcado = marcado.copy() if marcado else {}
        self.token_o = token.orden_id
        self.token_m = token.material
        self.token_c = token.costo
        self.token_t = token.timestamp
        self.token_v_target = token.v_target
        self.token_u = token.costo_unitario
        self.pnml_path = pnml_path
        self.red = None
        self.bd_id = None
        self.completada = False
        self.bloqueada = False
        self.temporizadores: Dict[str, dict] = {}

    @property
    def instancia_bd_id(self):
        return self.bd_id

    @instancia_bd_id.setter
    def instancia_bd_id(self, val):
        self.bd_id = val
    
    def __repr__(self):
        return f"InstanciaRedMem(id={self.id}, red={self.red_nombre}, orden={self.orden_id}, marcado={self.marcado})"


class MotorABTPPN:
    """
    Motor de ejecución formal de Redes de Petri AB-TPPN (N = <P, T, F, tau, Phi, Q, M_0>).
    Gestiona el marcado dinámico M, la habilitación de transiciones particionadas
    (T_auto, T_200, T_201, T_202) y la propagación del TokenColoreado entre lugares y redes.
    """
    
    def __init__(self):
        self.instancias: Dict[int, InstanciaRedMem] = {}
        self.proximo_id = 1
        self.redes_cargadas: Dict[str, Any] = {}
    
    def cargar_red_desde_pnml(self, red_nombre: str, pnml_path: str) -> bool:
        """Carga una red desde archivo PNML y la guarda en caché"""
        from utils.parser_pnml import cargar_red_desde_pnml
        
        if red_nombre in self.redes_cargadas:
            return True
        
        try:
            red = cargar_red_desde_pnml(pnml_path)
            if red:
                self.redes_cargadas[red_nombre] = red
                logger.info(f"✅ Red cargada: {red_nombre} (archivo: {Path(pnml_path).name})")
                return True
            else:
                logger.error(f"❌ Error cargando red {red_nombre} desde {pnml_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Excepción cargando red {red_nombre}: {e}")
            return False
    
    def crear_instancia(self, red_nombre: str, orden_id: int,
                        token_inicial: TokenColoreado,
                        marcado_inicial: dict = None,
                        pnml_path: str = None) -> Optional[int]:
        """
        Crea una nueva instancia de red en memoria
        """
        if red_nombre not in self.redes_cargadas:
            logger.error(f"❌ Red '{red_nombre}' no está cargada en memoria")
            return None
        
        red = self.redes_cargadas[red_nombre]
        
        if marcado_inicial is None:
            marcado_inicial = {}
            for pid, place in red.places.items():
                if place.marking_inicial > 0:
                    marcado_inicial[pid] = place.marking_inicial
        
        instancia_id = self.proximo_id
        self.proximo_id += 1
        
        instancia = InstanciaRedMem(
            id=instancia_id,
            red_nombre=red_nombre,
            orden_id=orden_id,
            marcado=marcado_inicial,
            token=token_inicial,
            pnml_path=pnml_path
        )
        instancia.red = red
        
        self.instancias[instancia_id] = instancia
        logger.info(f"✅ Instancia {instancia_id} creada para red '{red_nombre}' (orden {orden_id})")
        
        return instancia_id
    
    def actualizar_instancia_bd_id(self, instancia_mem_id: int, bd_id: int):
        """Asocia el ID de base de datos a la instancia en memoria"""
        if instancia_mem_id in self.instancias:
            self.instancias[instancia_mem_id].bd_id = bd_id
            logger.debug(f"Instancia {instancia_mem_id} asociada a BD ID {bd_id}")
    
    def _verificar_precondiciones(self, instancia: InstanciaRedMem, trans_id: str) -> bool:
        """Verifica que los lugares de entrada tengan tokens suficientes"""
        entradas = self._obtener_entradas_y_pesos(instancia, trans_id)
        
        for lugar_id, peso in entradas.items():
            tokens = instancia.marcado.get(lugar_id, 0)
            if tokens < peso:
                return False
        return True
    
    def _verificar_temporizador_expirado(self, instancia_id: int, trans_id: str) -> bool:
        """Verifica si el temporizador de una transición temporal ha expirado"""
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return False
        
        transicion = instancia.red.transitions.get(trans_id)
        if not transicion or getattr(transicion, 'trigger', None) != '202':
            return False
        
        tiempo_limite = getattr(transicion, 'timeout', 60)
        
        if trans_id not in instancia.temporizadores:
            instancia.temporizadores[trans_id] = {
                'inicio': datetime.now(),
                'limite': tiempo_limite
            }
            logger.debug(f"⏰ Temporizador iniciado para {trans_id}: {tiempo_limite}s")
            return False
        
        timer = instancia.temporizadores[trans_id]
        tiempo_transcurrido = (datetime.now() - timer['inicio']).total_seconds()
        
        if tiempo_transcurrido >= timer['limite']:
            logger.warning(f"⚠️ Temporizador expirado para {trans_id} después de {tiempo_transcurrido:.1f}s")
            del instancia.temporizadores[trans_id]
            return True
        
        return False
    
    def _obtener_entradas_y_pesos(self, instancia: InstanciaRedMem, trans_id: str) -> dict:
        entradas = {}
        for arc in instancia.red.arcs.values():
            if arc.target == trans_id:
                entradas[arc.source] = arc.peso
        return entradas

    def _obtener_salidas_y_pesos(self, instancia: InstanciaRedMem, trans_id: str) -> dict:
        salidas = {}
        for arc in instancia.red.arcs.values():
            if arc.source == trans_id:
                salidas[arc.target] = arc.peso
        return salidas

    def transicion_habilitada(self, instancia_id: int, trans_id: str,
                          tiene_mensaje_externo: bool = False,
                          tiene_mensaje_red: bool = False) -> bool:
        """Verifica si una transición está habilitada según su trigger"""
        instancia = self.instancias.get(instancia_id)
        if not instancia or trans_id not in instancia.red.transitions or instancia.bloqueada:
            return False
        
        transicion = instancia.red.transitions[trans_id]
        
        if not self._verificar_precondiciones(instancia, trans_id):
            return False
        
        trigger = getattr(transicion, 'trigger', None)
        trigger_str = str(trigger).strip() if trigger is not None else None
        if trigger_str in ('None', 'none', ''):
            trigger_str = None
        
        if trigger_str is None:
            return True
        elif trigger_str == '200':
            return tiene_mensaje_externo
        elif trigger_str == '201':
            return tiene_mensaje_red
        elif trigger_str == '202':
            return self._verificar_temporizador_expirado(instancia_id, trans_id)
        
        logger.warning(f"Trigger desconocido: {trigger}")
        return False
    
    def disparar_transicion(self, instancia_id: int, trans_id: str) -> Optional[TokenColoreado]:
        """Dispara una transición (sin token externo)"""
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return None
        
        transicion = instancia.red.transitions.get(trans_id)
        if not transicion:
            return None
        
        if not self._verificar_precondiciones(instancia, trans_id):
            return None
        
        token_actual = TokenColoreado(
            orden_id=instancia.token_o,
            material=instancia.token_m,
            costo=instancia.token_c,
            timestamp=instancia.token_t,
            v_target=getattr(instancia, 'token_v_target', None),
            costo_unitario=getattr(instancia, 'token_u', 0.0)
        )
        
        # Consumir tokens de entrada
        entradas = self._obtener_entradas_y_pesos(instancia, trans_id)
        for lugar_id, peso in entradas.items():
            tokens_actuales = instancia.marcado.get(lugar_id, 0)
            nuevos_tokens = tokens_actuales - peso
            if nuevos_tokens <= 0:
                if lugar_id in instancia.marcado:
                    del instancia.marcado[lugar_id]
            else:
                instancia.marcado[lugar_id] = nuevos_tokens
        
        # Producir tokens en salida
        salidas = self._obtener_salidas_y_pesos(instancia, trans_id)
        for lugar_id, peso in salidas.items():
            instancia.marcado[lugar_id] = instancia.marcado.get(lugar_id, 0) + peso
        
        logger.debug(f"   ✅ Disparada: {transicion.nombre or trans_id}")
        logger.debug(f"      Nuevo marcado: {instancia.marcado}")
        
        return token_actual
    
    def disparar_transicion_con_token(self, instancia_id: int, trans_id: str,
                                    token: TokenColoreado) -> bool:
        """Dispara una transición con un token específico (para mensajes 200/201)"""
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return False
        
        transicion = instancia.red.transitions.get(trans_id)
        if not transicion:
            return False
        
        if not self._verificar_precondiciones(instancia, trans_id):
            return False
        
        # Consumir tokens de entrada
        entradas = self._obtener_entradas_y_pesos(instancia, trans_id)
        for lugar_id, peso in entradas.items():
            tokens_actuales = instancia.marcado.get(lugar_id, 0)
            nuevos_tokens = tokens_actuales - peso
            if nuevos_tokens <= 0:
                if lugar_id in instancia.marcado:
                    del instancia.marcado[lugar_id]
            else:
                instancia.marcado[lugar_id] = nuevos_tokens
        
        # Actualizar token de la instancia con el recibido
        instancia.token_o = token.orden_id
        instancia.token_m = token.material
        instancia.token_c = token.costo
        instancia.token_t = token.timestamp
        instancia.token_v_target = token.v_target
        instancia.token_u = token.costo_unitario
        
        # Producir tokens en salida
        salidas = self._obtener_salidas_y_pesos(instancia, trans_id)
        for lugar_id, peso in salidas.items():
            instancia.marcado[lugar_id] = instancia.marcado.get(lugar_id, 0) + peso
        
        logger.debug(f"   ✅ Disparada con token: {transicion.nombre or trans_id}")
        return True
    
    def reiniciar_temporizador(self, instancia_id: int, trans_id: str):
        """Reinicia el temporizador (cuando llega el evento esperado antes del timeout)"""
        instancia = self.instancias.get(instancia_id)
        if instancia and trans_id in instancia.temporizadores:
            del instancia.temporizadores[trans_id]
            logger.info(f"🔄 Temporizador reiniciado para {trans_id}")
    
    def obtener_transiciones_habilitadas(self, instancia_id: int,
                                         tiene_mensaje_externo: bool = False,
                                         tiene_mensaje_red: bool = False) -> List[str]:
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return []
        
        habilitadas = []
        for trans_id in instancia.red.transitions.keys():
            if self.transicion_habilitada(instancia_id, trans_id,
                                          tiene_mensaje_externo,
                                          tiene_mensaje_red):
                habilitadas.append(trans_id)
        return habilitadas
    
    def obtener_transiciones_automaticas(self, instancia_id: int) -> List[str]:
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return []
        
        automaticas = []
        for trans_id, transicion in instancia.red.transitions.items():
            trigger = getattr(transicion, 'trigger', None)
            trigger_str = str(trigger).strip() if trigger is not None else None
            if trigger_str in ('None', 'none', ''):
                trigger_str = None
                
            if trigger_str is None:
                if self._verificar_precondiciones(instancia, trans_id):
                    automaticas.append(trans_id)
                    logger.debug(f"   Automática habilitada: {transicion.nombre}")
        return automaticas
    
    def obtener_marcado(self, instancia_id: int) -> dict:
        instancia = self.instancias.get(instancia_id)
        return instancia.marcado.copy() if instancia else {}
    
    def obtener_token(self, instancia_id: int) -> Optional[TokenColoreado]:
        instancia = self.instancias.get(instancia_id)
        if not instancia:
            return None
        return TokenColoreado(
            orden_id=instancia.token_o,
            material=instancia.token_m,
            costo=instancia.token_c,
            timestamp=instancia.token_t,
            v_target=getattr(instancia, 'token_v_target', None),
            costo_unitario=getattr(instancia, 'token_u', 0.0)
        )

    def actualizar_token(self, instancia_id: int, token: TokenColoreado) -> bool:
        """
        Sincroniza el estado del TokenColoreado (masa m, costo acumulado c_acc,
        costo unitario u = c_acc / m y marca de tiempo t_arr) en la instancia en memoria.
        """
        instancia = self.instancias.get(instancia_id)
        if not instancia or not token:
            return False
        instancia.token_o = token.orden_id
        instancia.token_m = token.material
        instancia.token_c = token.costo
        instancia.token_t = token.timestamp
        instancia.token_v_target = token.v_target
        instancia.token_u = token.costo_unitario
        return True
    
    def eliminar_instancia(self, instancia_id: int):
        if instancia_id in self.instancias:
            del self.instancias[instancia_id]
            logger.info(f"Instancia {instancia_id} eliminada")
    
    def limpiar_todas_instancias(self):
        self.instancias.clear()
        self.proximo_id = 1
        logger.info("Todas las instancias eliminadas")
    
    def bloquear_instancia(self, instancia_id: int):
        if instancia_id in self.instancias:
            self.instancias[instancia_id].bloqueada = True
            self.instancias[instancia_id].completada = True