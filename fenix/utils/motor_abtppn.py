# utils/motor_abtppn.py - Versión con logs limpios

"""Motor de Redes de Petri ABTPPN con soporte para tokens coloreados y triggers"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TokenColoreado:
    """Token coloreado que transporta información de la orden"""
    orden_id: str
    material: float
    coste: float
    timestamp: datetime


@dataclass
class InstanciaRedMem:
    """Instancia de red en memoria para una orden específica"""
    
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
        self.token_c = token.coste
        self.token_t = token.timestamp
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
    """Motor de ejecución de Redes de Petri ABTPPN"""
    
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
        
        if trigger is None:
            return True
        elif trigger == '200':
            return tiene_mensaje_externo
        elif trigger == '201':
            return tiene_mensaje_red
        elif trigger == '202':
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
            coste=instancia.token_c,
            timestamp=instancia.token_t
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
        instancia.token_c = token.coste
        instancia.token_t = token.timestamp
        
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
            if trigger is None:
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
            coste=instancia.token_c,
            timestamp=instancia.token_t
        )
    
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