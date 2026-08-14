# servicios/orquestador.py - Versión con logs limpios

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import time
import threading
from sqlalchemy.orm import Session

from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.RedPetri import RedPetri, TransicionRed
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, InvariantePaso, CriterioAceptacionEtapa, EspecificacionCalidad
from servicios.verificador_terminacion import VerificadorTerminacion

logger = logging.getLogger(__name__)


class Orquestador:
    """Orquestador que coordina el motor y la persistencia"""
    
    def __init__(self, motor: MotorABTPPN, session):
        self.motor = motor
        self.session = session
        
        # Mapeo de mensajes cargado desde BD
        self.mapeo_mensajes: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
        
        # Cache de redes cargadas
        self.redes_cache: Dict[str, Any] = {}
        self.verificador = VerificadorTerminacion(session)
    
    # ==================== CARGA DE CONFIGURACIÓN ====================
    
    def cargar_configuracion_desde_bd(self, encadenamiento_nombre: str = None) -> bool:
        """Carga la configuración de encadenamiento desde BD"""
        query = self.session.query(ConfiguracionEncadenamiento).filter_by(activo=True)
        if encadenamiento_nombre:
            query = query.filter_by(nombre=encadenamiento_nombre)
        
        config = query.first()
        
        if not config:
            logger.warning("⚠️ No se encontró configuración de encadenamiento activa")
            return False
        
        self.mapeo_mensajes.clear()
        
        for key, destinos in config.reglas.items():
            parts = key.split('.', 1)
            if len(parts) == 2:
                red_origen = parts[0]
                trans_nombre = parts[1]
                # Limpiar prefijo "pnml." si está presente
                if trans_nombre.startswith('pnml.'):
                    trans_nombre = trans_nombre[5:]  # quitar "pnml."
                
                for dest in destinos:
                    red_destino = dest.get('red_destino')
                    evento_destino = dest.get('evento_destino')
                    
                    if red_destino and evento_destino:
                        self.mapeo_mensajes.setdefault(
                            (red_origen, trans_nombre), []
                        ).append((red_destino, evento_destino))
        
        logger.info(f"📬 Configuración cargada: {len(self.mapeo_mensajes)} reglas")
        return True
    
    def cargar_red_desde_bd(self, red_nombre: str) -> Optional[Any]:
        """Carga una red Petri desde la BD a memoria"""
        if red_nombre in self.redes_cache:
            return self.redes_cache[red_nombre]
        
        red_bd = self.session.query(RedPetri).filter_by(nombre=red_nombre, activo=True).first()
        
        if not red_bd:
            logger.warning(f"⚠️ Red no encontrada: {red_nombre}")
            return None
        
        from utils.parser_pnml import PetriNet, Place, Transition, Arc
        
        places = {}
        for pid, p_data in red_bd.lugares.items():
            places[pid] = Place(
                id=pid,
                nombre=p_data.get('name', pid),
                marking_inicial=p_data.get('marking_inicial', 0)
            )
        
        transitions = {}
        for tid, t_data in red_bd.transiciones.items():
            transitions[tid] = Transition(
                id=tid,
                nombre=t_data.get('name', tid),
                trigger=t_data.get('trigger')
            )
        

        arcs = {}
        for aid, a_data in red_bd.arcos.items():
            arcs[aid] = Arc(
                id=aid,
                source=a_data.get('source'),
                target=a_data.get('target'),
                peso=a_data.get('peso', 1)
            )
        
        red_mem = PetriNet(
            nombre=red_bd.nombre,
            places=places,
            transitions=transitions,
            arcs=arcs
        )
        
        self.redes_cache[red_nombre] = red_mem
        # ✅ NUEVO: también cargar en el motor si no está
        if red_nombre not in self.motor.redes_cargadas:
            self.motor.redes_cargadas[red_nombre] = red_mem

        logger.info(f"✅ Red cargada: {red_nombre}")
        
        return red_mem
    
    # ==================== INICIALIZACIÓN DE ÓRDENES ====================
    
    def inicializar_orden(self, orden_id: int) -> bool:
        """Inicializa el seguimiento de una orden existente"""
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden:
            logger.error(f"❌ Orden {orden_id} no encontrada")
            return False
        
        if orden.estado != 'pendiente':
            logger.warning(f"⚠️ Orden {orden_id} no está pendiente (estado={orden.estado})")
            return False
        
        # Seleccionar holon_ruta (ya debería estar asignado)
        if orden.holon_ruta_id:
            holon = self.session.query(HolonRuta).get(orden.holon_ruta_id)
        else:
            holon = self._seleccionar_holon_ruta(orden.producto_id, orden.cantidad, orden.prioridad)
        
        if not holon:
            logger.error(f"❌ No hay ruta disponible para orden {orden_id}")
            orden.estado = 'fallida'
            self.session.commit()
            return False
        
        # Instanciar redes
        self._instanciar_redes_para_orden(orden, holon)
        
        orden.estado = 'en_produccion'
        orden.fecha_inicio = datetime.now()
        self.session.commit()
        
        logger.info(f"✅ Orden {orden.numero_orden} inicializada")
        return True
    
    def _seleccionar_holon_ruta(self, producto_id: int, cantidad: float, prioridad: int):
        """Selecciona la mejor ruta para el producto"""
        holones = self.session.query(HolonRuta).filter_by(
            producto_id=producto_id, activa=True
        ).all()
        
        candidatos = []
        for holon in holones:
            condiciones = holon.condiciones or {}
            lote_min = condiciones.get('lote_minimo_kg', 0)
            lote_max = condiciones.get('lote_maximo_kg', float('inf'))
            prioridad_min = condiciones.get('prioridad_minima', 1)
            
            if cantidad >= lote_min and cantidad <= lote_max and prioridad >= prioridad_min:
                orden_pref = condiciones.get('orden_preferencia', 999)
                candidatos.append((orden_pref, holon))
        
        if not candidatos:
            return None
        
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]
    
    def _instanciar_redes_para_orden(self, orden, holon):
        """Instancia todas las redes para una orden y guarda recursos ocupados."""
        patron = holon.patron
        
        token = TokenColoreado(
            orden_id=orden.numero_orden,
            material=orden.cantidad,
            coste=0,
            timestamp=datetime.now()
        )
        
        # Recopilar asignaciones de recursos por etapa

        asignacion_orden = orden.asignacion_recursos
        
        asignaciones_por_etapa = {}
        for asig in holon.asignaciones:
            etapa_nombre = asig.etapa.nombre
            if etapa_nombre not in asignaciones_por_etapa:
                asignaciones_por_etapa[etapa_nombre] = []
            # Obtener nombre del recurso (asumiendo que asig.recurso es objeto Recurso)
            recurso_nombre = asig.recurso.nombre if asig.recurso else str(asig.recurso_id)
            asignaciones_por_etapa[etapa_nombre].append(recurso_nombre)
        
        redes_bd = self.session.query(RedPetri).filter_by(
            patron_ruta_id=patron.id, activo=True
        ).all()
        
        for red_bd in redes_bd:
            red_mem = self.cargar_red_desde_bd(red_bd.nombre)
            if not red_mem:
                continue
            
            if red_bd.nombre not in self.motor.redes_cargadas:
                self.motor.redes_cargadas[red_bd.nombre] = red_mem
            
            marcado_inicial = {}
            for pid, place in red_mem.places.items():
                if place.marking_inicial > 0:
                    marcado_inicial[pid] = place.marking_inicial
            
            # Determinar recursos ocupados por esta red (coincidencia por nombre de etapa o por mapeo explícito)
            # Asumimos que el nombre de la red coincide con alguna etapa (ej: "dispersion" → etapa "Dispersión")
            recursos_ocupados = {}
            for etapa_nombre,  recurso_info in asignacion_orden.items():
                if etapa_nombre.lower() in red_bd.nombre.lower(): 
                    recursos_ocupados['recursos'] = [recurso_info['recurso_nombre']]
                    break
            # Si no se encuentra, dejar vacío (pero se podría inferir de otro modo)
            
            inst_mem_id = self.motor.crear_instancia(
                red_nombre=red_bd.nombre,
                orden_id=orden.id,
                token_inicial=token,
                marcado_inicial=marcado_inicial,
                pnml_path=None
            )
            
            inst_bd = InstanciaRed(
                orden_id=orden.id,
                tipo=red_bd.nombre,
                patron_ruta_id=patron.id,
                holon_ruta_id=holon.id,
                marcado=marcado_inicial,
                token_o=token.orden_id,
                token_m=token.material,
                token_c=token.coste,
                token_t=token.timestamp,
                activa=True,
                recursos_ocupados=recursos_ocupados   # ← NUEVO
            )
            self.session.add(inst_bd)
            self.session.flush()
            
            self.motor.actualizar_instancia_bd_id(inst_mem_id, inst_bd.id)
            logger.info(f"   📊 Instancia: {red_bd.nombre} con recursos {recursos_ocupados}")
        
        self.session.commit()
        
        # Procesar automáticas iniciales
        for inst_mem_id in self.motor.instancias:
            inst = self.motor.instancias[inst_mem_id]
            if inst.orden_id == orden.id:
                self.procesar_automaticas_instancia(inst_mem_id)

    def _resolver_red_por_recurso(self, orden_id: int, recurso_nombre: str) -> Optional[str]:
        """Dado un recurso físico, determina a qué red pertenece dentro de la orden activa."""
        # Buscar instancia activa que tenga ese recurso en recursos_ocupados
        instancia = self.session.query(InstanciaRed).filter(
            InstanciaRed.orden_id == orden_id,
            InstanciaRed.activa == True,
            InstanciaRed.completada == False
        ).first()  # Podría haber varias; asumimos que un recurso solo está en una red a la vez
        
        # Mejor: recorrer todas y verificar si el recurso está en recursos_ocupados
        for inst in self.session.query(InstanciaRed).filter(
            InstanciaRed.orden_id == orden_id,
            InstanciaRed.activa == True,
            InstanciaRed.completada == False
        ):
            ocupados = inst.recursos_ocupados or {}
            # Asumiendo que recursos_ocupados es un dict con una clave 'recursos' o una lista
            recursos_lista = ocupados.get('recursos', []) if isinstance(ocupados, dict) else []
            if recurso_nombre in recursos_lista:
                return inst.tipo
        
        return None
    
    # ==================== PROCESAMIENTO DE EVENTOS ====================

    def procesar_evento_planta(self, orden_id: int, evento_nombre: str,
                            recurso_nombre: str = None, red_nombre: str = None,
                            timestamp: datetime = None, mediciones: dict = None) -> bool:
        """Procesa un evento de planta (trigger 200).
        
        Args:
            orden_id: ID de la orden
            evento_nombre: Nombre del evento (ej: "Cargar solidos")
            recurso_nombre: Recurso físico que originó el evento (opcional)
            red_nombre: Nombre de la red (opcional, se deduce si no se da)
            timestamp: Momento del evento (si no se da, usa ahora)
            mediciones: Mediciones de telemetría física del SCADA (opcional)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Resolver red si no viene explícita
        if not red_nombre and recurso_nombre:
            red_nombre = self._resolver_red_por_recurso(orden_id, recurso_nombre)
            if not red_nombre:
                logger.error(f"❌ No se pudo resolver red para recurso {recurso_nombre} en orden {orden_id}")
                return False
        
        if not red_nombre:
            logger.error(f"❌ Falta red_nombre y no se pudo resolver mediante recurso")
            return False
        
        inst_mem_id = self._buscar_instancia_red(orden_id, red_nombre)
        if not inst_mem_id:
            logger.error(f"❌ Instancia no encontrada: {red_nombre} para orden {orden_id}")
            return False
        
        instancia = self.motor.instancias.get(inst_mem_id)
        if instancia and instancia.bloqueada:
            logger.warning(f"⛔ Instancia {red_nombre} bloqueada (orden terminada)")
            return False
        if not instancia:
            return False
        
        # Obtener transiciones habilitadas por evento (normalizado)
        transiciones_habilitadas = self._obtener_transiciones_disparables_por_evento(inst_mem_id, evento_nombre)
        if not transiciones_habilitadas:
            logger.warning(f"⚠️ Evento '{evento_nombre}' no habilita ninguna transición en red {red_nombre}")
            return False
        
        trans_id = transiciones_habilitadas[0]
        if len(transiciones_habilitadas) > 1:
            logger.info(f"   ℹ️ Evento '{evento_nombre}' habilita múltiples: {transiciones_habilitadas}. Usando {trans_id}")
        
        # Validar invariantes del paso actual (antes de disparar)
        if mediciones and recurso_nombre:
            from modelos.Recursos import Recurso
            from modelos.Taxonomia import EtapaRuta
            
            recurso = self.session.query(Recurso).filter(
                (Recurso.nombre == recurso_nombre) | (Recurso.codigo == recurso_nombre)
            ).first()
            
            if recurso:
                inst_bd = self.session.query(InstanciaRed).filter_by(
                    orden_id=orden_id, tipo=red_nombre, activa=True
                ).first()
                
                if inst_bd:
                    red_mem = instancia.red
                    in_places = [a.source for a in red_mem.arcs.values() if a.target == trans_id]
                    lugar_origen_nombre = red_mem.places[in_places[0]].nombre if in_places else ""
                    
                    asig = self.session.query(AsignacionRecurso).join(EtapaRuta).filter(
                        AsignacionRecurso.holon_ruta_id == inst_bd.holon_ruta_id,
                        AsignacionRecurso.recurso_id == recurso.id,
                        (EtapaRuta.nombre.like(f"%{lugar_origen_nombre}%") | 
                         EtapaRuta.nombre.like(f"%{in_places[0]}%") if in_places else True)
                    ).first()
                    
                    if asig:
                        invariantes = self.session.query(InvariantePaso).filter_by(
                            asignacion_recurso_id=asig.id
                        ).all()
                        
                        for inv in invariantes:
                            if inv.parametro in mediciones:
                                val = mediciones[inv.parametro]
                                if inv.valor_minimo is not None and val < inv.valor_minimo:
                                    logger.error(f"❌ Invariante violado: {inv.parametro} ({val}) menor que mínimo ({inv.valor_minimo})")
                                    raise ValueError(f"Invariante violado: {inv.parametro} fuera de rango")
                                if inv.valor_maximo is not None and val > inv.valor_maximo:
                                    logger.error(f"❌ Invariante violado: {inv.parametro} ({val}) mayor que máximo ({inv.valor_maximo})")
                                    raise ValueError(f"Invariante violado: {inv.parametro} fuera de rango")

        # Obtener token actual
        token_actual = self.motor.obtener_token(inst_mem_id)
        if not token_actual:
            token_actual = TokenColoreado(
                orden_id=f"ORD-{orden_id}", material=0, coste=0, timestamp=timestamp
            )
        
        # Calcular duración real desde el último cambio de token hasta este evento
        duracion_real = 0.0
        costo_paso = 0.0
        if token_actual.timestamp and timestamp:
            duracion_real = (timestamp - token_actual.timestamp).total_seconds()
            if duracion_real > 0 and recurso_nombre:
                costo_hora = self._obtener_costo_hora_recurso(orden_id, red_nombre, recurso_nombre)
                costo_paso = (duracion_real / 3600.0) * costo_hora
                token_actual.coste += costo_paso
            token_actual.timestamp = timestamp
        
        # Disparar
        resultado = self.motor.disparar_transicion_con_token(inst_mem_id, trans_id, token_actual)
        
        if resultado:
            self._persistir_evento_externo(inst_mem_id, evento_nombre, recurso_nombre, timestamp,
                                        duracion_real, costo_paso, mediciones)
            token_nuevo = self.motor.obtener_token(inst_mem_id)
            if token_nuevo:
                transicion_obj = instancia.red.transitions.get(trans_id)
                if transicion_obj:
                    self._generar_mensajes_salida(inst_mem_id, trans_id, transicion_obj, token_nuevo)
            self.estabilizar_red(orden_id)
            logger.info(f"   ✅ Procesado: {evento_nombre} → {trans_id} (dur={duracion_real:.1f}s, coste={costo_paso:.2f})")
            return True
        
        return False
    

    def procesar_control_calidad(self, orden_id: int, recurso_nombre: str, mediciones_qc: Dict[str, float], red_nombre: str = None) -> bool:
        """
        Recibe las mediciones de control de calidad del laboratorio.
        Compara con los CriterioAceptacionEtapa de la etapa actual.
        Si cumple, dispara automáticamente la aprobación (trigger 201).
        Si falla, dispara el reproceso (trigger 200).
        """
        if not red_nombre:
            red_nombre = self._resolver_red_por_recurso(orden_id, recurso_nombre)
        if not red_nombre:
            logger.error(f"❌ No se pudo resolver red para recurso {recurso_nombre}")
            return False
            
        inst_mem_id = self._buscar_instancia_red(orden_id, red_nombre)
        if not inst_mem_id:
            return False
            
        instancia = self.motor.instancias.get(inst_mem_id)
        if not instancia or instancia.bloqueada:
            return False
            
        inst_bd = self.session.query(InstanciaRed).filter_by(
            orden_id=orden_id, tipo=red_nombre, activa=True
        ).first()
        if not inst_bd:
            return False
            
        token_actual = self.motor.obtener_token(inst_mem_id)
        if not token_actual:
            return False
            
        lugares_con_token = [pid for pid, mark in instancia.marcado.items() if mark > 0]
        if not lugares_con_token:
            return False
        lugar_actual = lugares_con_token[0]
        lugar_actual_nombre = instancia.red.places[lugar_actual].nombre
        
        from modelos.Taxonomia import EtapaRuta
        etapa = self.session.query(EtapaRuta).filter(
            EtapaRuta.patronRuta_id == inst_bd.patron_ruta_id,
            (EtapaRuta.nombre.like(f"%{lugar_actual_nombre}%") | 
             EtapaRuta.nombre.like(f"%{lugar_actual}%"))
        ).first()
        
        if not etapa:
            logger.error(f"❌ No se encontró EtapaRuta para el lugar {lugar_actual}")
            return False
            
        criterios = self.session.query(CriterioAceptacionEtapa).filter_by(
            holon_ruta_id=inst_bd.holon_ruta_id,
            etapa_ruta_id=etapa.id
        ).all()
        
        aprobado = True
        motivos_rechazo = []
        
        for crit in criterios:
            espec = crit.especificacion
            if espec.nombre in mediciones_qc:
                val = mediciones_qc[espec.nombre]
                if espec.limite_minimo is not None and val < espec.limite_minimo:
                    aprobado = False
                    motivos_rechazo.append(f"{espec.nombre} ({val}) menor que mínimo ({espec.limite_minimo})")
                if espec.limite_maximo is not None and val > espec.limite_maximo:
                    aprobado = False
                    motivos_rechazo.append(f"{espec.nombre} ({val}) mayor que máximo ({espec.limite_maximo})")
                    
        if aprobado:
            logger.info(f"✅ Calidad aprobada para orden {orden_id} en etapa {etapa.nombre}.")
            trigger_evento = "201"
            evento_nombre = "Aprobado"
        else:
            logger.warning(f"❌ Calidad rechazada para orden {orden_id} en etapa {etapa.nombre}. Motivo: {', '.join(motivos_rechazo)}")
            trigger_evento = "200"
            evento_nombre = f"Rechazado ({', '.join(motivos_rechazo)})"
            
        # Obtener transiciones de salida del lugar actual en la red
        red_mem = instancia.red
        arcos_salida = [a for a in red_mem.arcs.values() if a.source == lugar_actual]
        transiciones_candidatas = [a.target for a in arcos_salida]
        
        trans_id = None
        for tid in transiciones_candidatas:
            if self.motor._verificar_precondiciones(instancia, tid):
                trans_obj = red_mem.transitions[tid]
                nombre_t = (trans_obj.nombre or tid).lower()
                trigger_t = getattr(trans_obj, 'trigger', None)
                
                if aprobado:
                    if "aprobado" in nombre_t or "ok" in nombre_t or "pass" in nombre_t or "aceptado" in nombre_t or trigger_t == "201":
                        trans_id = tid
                        break
                else:
                    if "rechazado" in nombre_t or "reproceso" in nombre_t or "fail" in nombre_t or "rechazo" in nombre_t or trigger_t == "200":
                        trans_id = tid
                        break
                        
        if not trans_id:
            logger.error(f"❌ No se encontró transición habilitada para el resultado de calidad (aprobado={aprobado}) en lugar {lugar_actual}")
            return False
        
        timestamp = datetime.now()
        duracion_real = 0.0
        costo_paso = 0.0
        if token_actual.timestamp:
            duracion_real = (timestamp - token_actual.timestamp).total_seconds()
            costo_hora = self._obtener_costo_hora_recurso(orden_id, red_nombre, recurso_nombre)
            costo_paso = (duracion_real / 3600.0) * costo_hora
            token_actual.coste += costo_paso
            token_actual.timestamp = timestamp
            
        resultado = self.motor.disparar_transicion_con_token(inst_mem_id, trans_id, token_actual)
        if resultado:
            self._persistir_evento_externo(inst_mem_id, evento_nombre, recurso_nombre, timestamp,
                                        duracion_real, costo_paso, mediciones_qc)
            
            token_nuevo = self.motor.obtener_token(inst_mem_id)
            if token_nuevo:
                transicion_obj = instancia.red.transitions.get(trans_id)
                if transicion_obj:
                    self._generar_mensajes_salida(inst_mem_id, trans_id, transicion_obj, token_nuevo)
            
            self.estabilizar_red(orden_id)
            self._verificar_y_finalizar_orden(orden_id)
            return True
            
        return False

    def _obtener_transiciones_disparables_por_evento(self, instancia_mem_id: int, evento_nombre: str) -> List[str]:
        """
        Retorna las transiciones con trigger=200 que coinciden con el evento
        (normalizando espacios y mayúsculas) y están habilitadas.
        """
        instancia = self.motor.instancias.get(instancia_mem_id)
        if not instancia:
            return []

        evento_normalizado = evento_nombre.strip().lower()
        disparables = []

        for trans_id, transicion in instancia.red.transitions.items():
            trigger = getattr(transicion, 'trigger', None)
            if trigger != '200':
                continue

            # Obtener nombre de la transición y normalizar
            nombre_trans = transicion.nombre or ""
            nombre_normalizado = nombre_trans.strip().lower()

            # Coincidencia por nombre normalizado
            if nombre_normalizado == evento_normalizado:
                if self.motor._verificar_precondiciones(instancia, trans_id):
                    disparables.append(trans_id)
                    logger.debug(f"   ✓ Transición {trans_id} ({transicion.nombre}) habilitada por evento")
            # También permitir si el evento es exactamente el ID técnico
            elif evento_nombre == trans_id:
                if self.motor._verificar_precondiciones(instancia, trans_id):
                    disparables.append(trans_id)
                    logger.debug(f"   ✓ Transición {trans_id} (ID) habilitada")

        if not disparables:
            # Log de ayuda: mostrar qué transiciones trigger=200 están disponibles
            disponibles = [(tid, t.nombre) for tid, t in instancia.red.transitions.items()
                        if getattr(t, 'trigger', None) == '200']
            logger.warning(f"⚠️ Evento '{evento_nombre}' no coincide con ninguna transición trigger=200. Disponibles: {disponibles}")

        return disparables


    def estabilizar_red(self, orden_id: int, max_iteraciones: int = 50) -> int:
        """
        Procesa iterativamente mensajes y automáticas hasta que el sistema se estabiliza.
        Retorna el número de iteraciones realizadas.
        """
        iteracion = 0
        hubo_cambios = True
        
        while hubo_cambios and iteracion < max_iteraciones:
            hubo_cambios = False
            iteracion += 1
            
            logger.debug(f"🔄 Estabilización - Iteración {iteracion}")
            
            # 1. Procesar mensajes pendientes (trigger=201)
            mensajes_procesados = self._procesar_todos_mensajes(orden_id)
            if mensajes_procesados > 0:
                hubo_cambios = True
                logger.debug(f"   📬 Mensajes procesados: {mensajes_procesados}")
            
            # 2. Procesar transiciones automáticas (trigger=None) en todas las instancias
            autos_procesadas = self._procesar_todas_automaticas(orden_id)
            if autos_procesadas > 0:
                hubo_cambios = True
                logger.debug(f"   ⚙️ Automáticas procesadas: {autos_procesadas}")

            # ✅ NUEVO: Verificar si la orden ya terminó
            if self._verificar_y_finalizar_orden(orden_id):
                logger.info(f"   🏁 Orden {orden_id} terminada durante estabilización")
                return iteracion
            
            if not hubo_cambios:
                logger.debug(f"   ✅ Sistema estabilizado en iteración {iteracion}")
        
        if iteracion >= max_iteraciones:
            logger.warning(f"⚠️ Se alcanzó max_iteraciones={max_iteraciones}")
        
        return iteracion
    
    def marcar_instancia_completada(self, instancia_bd_id: int, tipo: str, lugar: str):
        """Persiste que una instancia ha terminado (éxito/fallo/descarte) y la bloquea."""
        instancia_bd = self.session.query(InstanciaRed).get(instancia_bd_id)
        if not instancia_bd or instancia_bd.completada:
            return
        
        instancia_bd.completada = True
        instancia_bd.tipo_terminacion = tipo
        instancia_bd.lugar_terminacion = lugar
        instancia_bd.activa = False
        instancia_bd.fecha_cierre = datetime.now()
        self.session.commit()
        
        # Bloquear en memoria si existe
        mem_id = self._buscar_instancia_red(instancia_bd.orden_id, instancia_bd.tipo)
        if mem_id and mem_id in self.motor.instancias:
            self.motor.instancias[mem_id].completada = True
            self.motor.instancias[mem_id].bloqueada = True
            logger.info(f"🏁 Instancia {instancia_bd.tipo} marcada como completada ({tipo} en {lugar})")

    def _verificar_y_finalizar_orden(self, orden_id: int) -> bool:
        """
        Verifica cada instancia activa. Si alguna está terminada, la marca como completada.
        Si todas están terminadas, cierra la orden.
        """
        instancias = self.session.query(InstanciaRed).filter_by(
            orden_id=orden_id, activa=True
        ).all()
        
        todas_terminadas = True
        alguna_terminada = False
        
        for inst_bd in instancias:
            if inst_bd.completada:
                continue
            
            res = self.verificador.instancia_terminada(inst_bd)
            if res["terminada"]:
                inst_bd.completada = True
                inst_bd.tipo_terminacion = res["tipo"]
                inst_bd.lugar_terminacion = res["lugar"]
                inst_bd.activa = False
                inst_bd.fecha_cierre = datetime.now()
                self.session.commit()
                logger.info(f"   ✅ Instancia {inst_bd.tipo} completada: {res['tipo']} en {res['lugar']}")
                alguna_terminada = True
                
                mem_id = self._buscar_instancia_red(orden_id, inst_bd.tipo)
                if mem_id and mem_id in self.motor.instancias:
                    self.motor.instancias[mem_id].completada = True
                    self.motor.instancias[mem_id].bloqueada = True
            else:
                todas_terminadas = False
        
        if todas_terminadas and alguna_terminada:
            orden = self.session.query(OrdenProduccion).get(orden_id)
            if orden and orden.estado not in ('completada', 'fallida', 'cancelada'):
                orden.estado = 'completada'
                orden.fecha_fin = datetime.now()
                self.session.commit()
                logger.info(f"🏁 Orden {orden.numero_orden} finalizada: completada")
                
                # Ejecutar bucle de aprendizaje EWMA al terminar la orden
                self.ejecutar_aprendizaje_orden(orden_id)
                return True
        elif alguna_terminada:
            self.session.commit()
        
        return todas_terminadas

    def ejecutar_aprendizaje_orden(self, orden_id: int):
        """
        Analiza el historial de eventos de la orden y recalcula la eficiencia
        real de los recursos usando un suavizado EWMA (alfa = 0.2).
        """
        logger.info(f"🧠 Iniciando bucle de aprendizaje EWMA para orden {orden_id}...")
        
        eventos = self.session.query(EventoRed).filter(
            EventoRed.orden_id == orden_id
        ).all()
        
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden or not orden.holon_ruta_id:
            return
            
        for ev in eventos:
            meta = ev.invariantes or {}
            recurso_nombre = meta.get("recurso")
            duracion_real_min = meta.get("duracion_min", 0.0)
            
            if not recurso_nombre or duracion_real_min <= 0.0:
                continue
                
            from modelos.Recursos import Recurso
            
            recurso = self.session.query(Recurso).filter(
                (Recurso.nombre == recurso_nombre) | (Recurso.codigo == recurso_nombre)
            ).first()
            
            if not recurso:
                continue
                
            asig = self.session.query(AsignacionRecurso).filter(
                AsignacionRecurso.holon_ruta_id == orden.holon_ruta_id,
                AsignacionRecurso.recurso_id == recurso.id
            ).first()
            
            if not asig:
                continue
                
            duracion_nominal = asig.duracion_estimada_min
            if duracion_nominal <= 0.0:
                continue
                
            # Calcular eficiencia observada en este lote
            eficiencia_obs = duracion_nominal / duracion_real_min
            eficiencia_obs = max(0.1, min(1.5, eficiencia_obs))
            
            # Recalcular usando EWMA
            alfa = 0.2
            eficiencia_anterior = asig.eficiencia_real if asig.eficiencia_real is not None else 1.0
            eficiencia_nueva = (alfa * eficiencia_obs) + ((1.0 - alfa) * eficiencia_anterior)
            
            asig.eficiencia_real = eficiencia_nueva
            logger.info(f"   📈 Recurso '{recurso.nombre}' recalibrado en ruta: eficiencia {eficiencia_anterior:.3f} → {eficiencia_nueva:.3f} (obs={eficiencia_obs:.3f})")
            
        self.session.commit()

    def _procesar_todos_mensajes(self, orden_id: int) -> int:
        """Procesa todos los mensajes pendientes habilitados. Retorna cantidad procesados."""
        contador = 0
        
        while True:
            msg = self.session.query(MensajePendiente).filter_by(
                orden_id=orden_id, consumido=False
            ).first()
            
            if not msg:
                logger.debug("No hay mensajes pendientes")
                break
            
            logger.debug(f"Mensaje encontrado: {msg.red_destino}.{msg.evento}")

            inst_mem_id = self._buscar_instancia_red(msg.orden_id, msg.red_destino)
            if not inst_mem_id:
                logger.debug("Instancia en memoria no encontrada")
                msg.consumido = True
                self.session.commit()
                continue

            instancia = self.motor.instancias.get(inst_mem_id)
            if not instancia:
                logger.debug("Instancia no encontrada en motor")
                msg.consumido = True
                self.session.commit()
                continue
            
            logger.debug(f"Instancia encontrada: {instancia.red_nombre}")
            logger.debug(f"Marcado actual: {instancia.marcado}")
            
            trans_id = self._buscar_transicion_por_nombre(instancia, msg.evento)
            if not trans_id:
                logger.debug(f"Transición '{msg.evento}' no encontrada")
                msg.consumido = True
                self.session.commit()
                continue

            logger.debug(f"Transición encontrada: {trans_id}")
            
            if self.motor.transicion_habilitada(inst_mem_id, trans_id, tiene_mensaje_red=True):
                logger.debug("Transición habilitada, disparando...")
                token = TokenColoreado(
                    orden_id=msg.datos.get('token_orden_id', f"ORD-{msg.orden_id}"),
                    material=msg.datos.get('token_material', 0),
                    coste=msg.datos.get('token_coste', 0),
                    timestamp=datetime.now()
                )
                
                disparo_exitoso = self.motor.disparar_transicion_con_token(inst_mem_id, trans_id, token)
                
                if disparo_exitoso:
                    logger.debug("Transición disparada exitosamente")
                    self._persistir_evento_mensaje(inst_mem_id, trans_id, msg.red_origen)
                    msg.consumido = True
                    self.session.commit()
                    contador += 1
                    
                    token_nuevo = self.motor.obtener_token(inst_mem_id)
                    if token_nuevo:
                        transicion_obj = instancia.red.transitions.get(trans_id)
                        if transicion_obj:
                            self._generar_mensajes_salida(inst_mem_id, trans_id, transicion_obj, token_nuevo)
                    
                    logger.debug(f"Mensaje procesado: {msg.red_destino}.{msg.evento}")
                    self._verificar_y_finalizar_orden(msg.orden_id)
                else:
                    logger.debug("Fallo al disparar transición")
                    break
            else:
                logger.debug("Transición NO habilitada")
                entradas = self.motor._obtener_entradas_y_pesos(instancia, trans_id)
                for lugar, peso in entradas.items():
                    tiene = instancia.marcado.get(lugar, 0)
                    logger.debug(f"      {lugar}: necesita {peso}, tiene {tiene}")
                break
        
        return contador

    def _procesar_todas_automaticas(self, orden_id: int) -> int:
        """Procesa todas las transiciones automáticas habilitadas en todas las instancias."""
        contador = 0
        hubo_auto = True
        
        while hubo_auto:
            hubo_auto = False
            
            for mem_id, inst in self.motor.instancias.items():
                if inst.orden_id != orden_id or inst.completada:
                    continue
                
                transiciones_auto = self.motor.obtener_transiciones_automaticas(mem_id)
                for trans_id in transiciones_auto:
                    transicion = inst.red.transitions[trans_id]
                    token = self.motor.disparar_transicion(mem_id, trans_id)
                    
                    if token:
                        self._persistir_evento_auto(mem_id, transicion.nombre)
                        contador += 1
                        hubo_auto = True
                        self._generar_mensajes_salida(mem_id, trans_id, transicion, token)
                        self._verificar_y_finalizar_orden(orden_id)
                        break
                
                if hubo_auto:
                    break
        
        return contador
    
    def procesar_mensajes_pendientes(self, orden_id: int = None):
        """Procesa handshakes entre redes (método público, usado por el bucle)"""
        query = self.session.query(MensajePendiente).filter_by(consumido=False)
        if orden_id:
            query = query.filter_by(orden_id=orden_id)
        
        for msg in query.all():
            logger.info(f"📬 Mensaje: {msg.red_origen} -> {msg.red_destino}.{msg.evento}")
            
            inst_mem_id = self._buscar_instancia_red(msg.orden_id, msg.red_destino)
            if not inst_mem_id:
                msg.consumido = True
                self.session.commit()
                continue
            
            instancia = self.motor.instancias.get(inst_mem_id)
            trans_id = self._buscar_transicion_por_nombre(instancia, msg.evento)
            
            if not trans_id:
                msg.consumido = True
                self.session.commit()
                continue
            
            if not self.motor.transicion_habilitada(inst_mem_id, trans_id, tiene_mensaje_red=True):
                continue
            
            token = TokenColoreado(
                orden_id=msg.datos.get('token_orden_id', f"ORD-{msg.orden_id}"),
                material=msg.datos.get('token_material', 0),
                coste=msg.datos.get('token_coste', 0),
                timestamp=datetime.now()
            )
            
            if self.motor.disparar_transicion_con_token(inst_mem_id, trans_id, token):
                self._persistir_evento_mensaje(inst_mem_id, msg.evento, msg.red_origen)
                self.procesar_automaticas_instancia(inst_mem_id)
                
                token_nuevo = self.motor.obtener_token(inst_mem_id)
                if token_nuevo:
                    transicion_obj = instancia.red.transitions.get(trans_id)
                    if transicion_obj:
                        self._generar_mensajes_salida(inst_mem_id, trans_id, transicion_obj, token_nuevo)
                
                msg.consumido = True
                self.session.commit()
                logger.info(f"   ✅ Handshake completado")
    
    def procesar_automaticas_instancia(self, instancia_mem_id: int, max_iteraciones: int = 100):
        """Procesa transiciones automáticas (trigger=None)"""
        instancia = self.motor.instancias.get(instancia_mem_id)
        if not instancia or instancia.completada:
            return
        
        iteraciones = 0
        while iteraciones < max_iteraciones:
            transiciones_auto = self.motor.obtener_transiciones_automaticas(instancia_mem_id)
            if not transiciones_auto:
                break
            
            for trans_id in transiciones_auto:
                transicion = instancia.red.transitions[trans_id]
                token = self.motor.disparar_transicion(instancia_mem_id, trans_id)
                
                if token:
                    self._persistir_evento_auto(instancia_mem_id, transicion.nombre)
                    self._generar_mensajes_salida(instancia_mem_id, trans_id, transicion, token)
            
            iteraciones += 1
    
    def _generar_mensajes_salida(self, instancia_mem_id: int, trans_id: str, transicion, token: TokenColoreado):
        """Genera mensajes según mapeo de encadenamiento"""
        logger.debug(f"Generando mensajes para transición {trans_id}")
        
        instancia = self.motor.instancias.get(instancia_mem_id)
        if not instancia:
            logger.debug("No se encontró instancia")
            return
        
        # Usar el ID de la transición (t1, t41, etc.) como clave
        clave = (instancia.red_nombre, trans_id)
        
        logger.debug(f"Buscando mensajes para clave: {clave}")
        
        mensajes_destino = self.mapeo_mensajes.get(clave, [])
        
        for red_destino, evento_destino in mensajes_destino:
            red_destino_limpio = red_destino.replace('.pnml', '')
            msg = MensajePendiente(
                orden_id=instancia.orden_id,
                red_origen=instancia.red_nombre,
                transicion_origen=trans_id,
                red_destino=red_destino_limpio,
                evento=evento_destino,
                datos={
                    'token_orden_id': token.orden_id,
                    'token_material': token.material,
                    'token_coste': token.coste
                },
                consumido=False,
                fecha_creacion=datetime.now()
            )
            self.session.add(msg)
            self.session.commit()
            logger.info(f"   📬 Mensaje CREADO: {clave[0]}.{clave[1]} → {red_destino}.{evento_destino}")
            

    def iniciar_bucle(self, session_factory, intervalo_segundos=5):
        """
        Inicia un hilo worker que procesa periódicamente todas las órdenes activas.
        """
        self._bucle_activo = True
        self._session_factory = session_factory
        
        def worker():
            while self._bucle_activo:
                try:
                    session = self._session_factory()
                    try:
                        original_session = self.session
                        self.session = session
                        self.procesar_todas_ordenes_activas()
                        self.session = original_session
                    finally:
                        session.close()
                except Exception as e:
                    logger.exception(f"Error en bucle orquestador: {e}")
                time.sleep(intervalo_segundos)
        
        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()
        logger.info(f"🔄 Bucle orquestador iniciado (intervalo={intervalo_segundos}s)")
    
    def detener_bucle(self):
        """Detiene el worker del bucle."""
        self._bucle_activo = False
        if hasattr(self, '_worker_thread') and self._worker_thread:
            self._worker_thread.join(timeout=2)
            logger.info("🛑 Bucle orquestador detenido")
    
    def procesar_todas_ordenes_activas(self):
        """
        Itera sobre todas las órdenes en estado 'en_produccion' o 'pendiente'
        y les aplica: mensajes, automáticas y verificación de terminación.
        """
        ordenes = self.session.query(OrdenProduccion).filter(
            OrdenProduccion.estado.in_(['en_produccion', 'pendiente'])
        ).all()
        
        if not ordenes:
            return
        
        logger.debug(f"📋 Procesando {len(ordenes)} órdenes activas")
        
        for orden in ordenes:
            self.procesar_mensajes_pendientes(orden.id)
            self._procesar_todas_automaticas(orden.id)
            self._verificar_y_finalizar_orden(orden.id)


    # ==================== MÉTODOS AUXILIARES ====================
    
    def _buscar_instancia_red(self, orden_id: int, red_nombre: str) -> Optional[int]:
        for mem_id, inst in self.motor.instancias.items():
            if inst.orden_id == orden_id and inst.red_nombre == red_nombre:
                return mem_id
        return None
    
    def _buscar_transicion_por_nombre(self, instancia, nombre: str) -> Optional[str]:
        for trans_id, transicion in instancia.red.transitions.items():
            if transicion.nombre == nombre:
                return trans_id
        return None
    
    # ==================== PERSISTENCIA ====================
    
    def _persistir_evento_auto(self, instancia_mem_id: int, trans_nombre: str):
        instancia_mem = self.motor.instancias.get(instancia_mem_id)
        if not instancia_mem:
            return
        
        # Calcular duración desde el timestamp del token hasta ahora
        token = self.motor.obtener_token(instancia_mem_id)
        duracion_seg = 0.0
        if token and token.timestamp:
            duracion_seg = (datetime.now() - token.timestamp).total_seconds()
            # Opcional: actualizar token timestamp a ahora (pero cuidado con múltiples automáticas)
            token.timestamp = datetime.now()
            # No actualizamos coste porque no tenemos recurso
        
        evento = EventoRed(
            orden_id=instancia_mem.orden_id,
            instancia_id=instancia_mem.bd_id,
            transicion_nombre=trans_nombre,
            timestamp=datetime.now(),
            invariantes={'tipo': 'auto', 'marcado': instancia_mem.marcado.copy()},
            token_m=instancia_mem.token_m,
            token_c=instancia_mem.token_c,
            costo_real_paso=0.0
        )
        self.session.add(evento)
        self._actualizar_instancia_bd(instancia_mem)
        self.session.commit()
    
    def _persistir_evento_externo(self, instancia_mem_id: int, trans_nombre: str, 
                                recurso_nombre: str, timestamp: datetime,
                                duracion_seg: float = None, costo_paso: float = None,
                                mediciones: dict = None):
        instancia_mem = self.motor.instancias.get(instancia_mem_id)
        if not instancia_mem:
            return
        
        invariantes_dict = {
            'tipo': 'externo', 
            'recurso': recurso_nombre, 
            'marcado': instancia_mem.marcado.copy(),
            'duracion_min': (duracion_seg / 60.0) if duracion_seg else 0.0
        }
        if mediciones:
            invariantes_dict['mediciones'] = mediciones
            
        evento = EventoRed(
            orden_id=instancia_mem.orden_id,
            instancia_id=instancia_mem.bd_id,
            transicion_nombre=trans_nombre,
            timestamp=timestamp,
            invariantes=invariantes_dict,
            token_m=instancia_mem.token_m,
            token_c=instancia_mem.token_c,
            costo_real_paso=costo_paso
        )
        self.session.add(evento)
        self._actualizar_instancia_bd(instancia_mem)
        self.session.commit()
    
    def _persistir_evento_mensaje(self, instancia_mem_id: int, trans_id: str, red_origen: str):
        instancia_mem = self.motor.instancias.get(instancia_mem_id)
        if not instancia_mem:
            return
        
        transicion = instancia_mem.red.transitions.get(trans_id)
        trans_nombre = transicion.nombre if transicion else trans_id
        
        evento = EventoRed(
            orden_id=instancia_mem.orden_id,
            instancia_id=instancia_mem.bd_id,
            transicion_nombre=trans_nombre,
            timestamp=datetime.now(),
            invariantes={'tipo': 'mensaje', 'red_origen': red_origen, 'marcado': instancia_mem.marcado.copy()},
            token_m=instancia_mem.token_m,
            token_c=instancia_mem.token_c
        )
        self.session.add(evento)
        self._actualizar_instancia_bd(instancia_mem)
        self.session.commit()
    
    def _actualizar_instancia_bd(self, instancia_mem):
        instancia_bd = self.session.query(InstanciaRed).get(instancia_mem.bd_id)
        if instancia_bd:
            instancia_bd.marcado = instancia_mem.marcado
            instancia_bd.token_o = instancia_mem.token_o
            instancia_bd.token_m = instancia_mem.token_m
            instancia_bd.token_c = instancia_mem.token_c
            instancia_bd.token_t = instancia_mem.token_t

    def _obtener_costo_hora_recurso(self, orden_id: int, red_nombre: str, recurso_id: str) -> float:
        """Busca el costo por hora del recurso asignado a esta etapa."""
        # Buscar el holon_ruta de la orden
        orden = self.session.query(OrdenProduccion).get(orden_id)
        if not orden or not orden.holon_ruta_id:
            return 0.0
        
        # Buscar la asignación de recurso para esta red y recurso
        # Primero obtener la red para saber su tipo (red_nombre)
        red = self.session.query(RedPetri).filter_by(nombre=red_nombre).first()
        if not red:
            return 0.0
        
        # Buscar el PatronDeRuta asociado a la red
        if not red.patron_ruta_id:
            return 0.0
        
        # Buscar la etapa del patrón que corresponde a esta red? No es directo.
        # Alternativa: buscar en asignacion_recurso donde el recurso_id coincida y el holon_ruta_id sea el de la orden
        from modelos.Producto import AsignacionRecurso
        asignacion = self.session.query(AsignacionRecurso).filter(
            AsignacionRecurso.holon_ruta_id == orden.holon_ruta_id,
            AsignacionRecurso.recurso_id == recurso_id
        ).first()
        
        if asignacion:
            return asignacion.costo_por_hora_real
        return 0.0
    