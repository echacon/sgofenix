#!/usr/bin/env python3
# main.py - Orquestador continuo de FÉNIX (versión con tablas)

import sys
import codecs
import time
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuración de logging al inicio
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fenix.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

from servicios.orquestador import Orquestador
from servicios.cola_eventos import ServicioColaEventos
from servicios.seguimiento_ordenes import ServicioSeguimiento
from utils.motor_abtppn import MotorABTPPN
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.RedPetri import RedPetri
from modelos.Colaevento import ColaEvento

# ---------- Configuración ----------
INTERVALO_SEGUNDOS = 5          # Ciclo del orquestador
MAX_ITERACIONES_ESTABILIZACION = 20

# ---------- Conexión a BD ----------
engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)

# ---------- Inicialización global ----------
motor = MotorABTPPN()
session_inicial = Session()
orquestador = Orquestador(motor, session_inicial)
servicio_cola = ServicioColaEventos()  # Usará su propia sesión

# Cargar todas las redes Petri desde BD a memoria
def cargar_redes_en_motor():
    session = Session()
    try:
        redes_bd = session.query(RedPetri).filter_by(activo=True).all()
        for red in redes_bd:
            red_mem = orquestador.cargar_red_desde_bd(red.nombre)
            if red_mem and red.nombre not in motor.redes_cargadas:
                motor.redes_cargadas[red.nombre] = red_mem
                logger.info(f"   ✅ Red cargada: {red.nombre}")
        # Cargar configuración de encadenamiento desde BD
        orquestador.cargar_configuracion_desde_bd()
    finally:
        session.close()

# Cargar instancias activas desde BD a memoria (útil si el orquestador se reinicia)
def cargar_instancias_activas():
    session = Session()
    try:
        from utils.motor_abtppn import TokenColoreado
        instancias_bd = session.query(InstanciaRed).filter_by(activa=True).all()
        if not instancias_bd:
            return
        logger.info(f"🔄 Cargando {len(instancias_bd)} instancia(s) activa(s)...")
        for inst_bd in instancias_bd:
            # Verificar si ya existe en memoria
            existe = any(
                inst.orden_id == inst_bd.orden_id and inst.red_nombre == inst_bd.tipo
                for inst in motor.instancias.values()
            )
            if existe:
                continue

            token = TokenColoreado(
                orden_id=inst_bd.token_o or f"ORD-{inst_bd.orden_id}",
                material=inst_bd.token_m or 0,
                coste=inst_bd.token_c or 0,
                timestamp=inst_bd.token_t or datetime.now()
            )
            mem_id = motor.crear_instancia(
                red_nombre=inst_bd.tipo,
                orden_id=inst_bd.orden_id,
                token_inicial=token,
                marcado_inicial=inst_bd.marcado,
                pnml_path=None
            )
            if mem_id:
                motor.actualizar_instancia_bd_id(mem_id, inst_bd.id)
                if inst_bd.completada:
                    motor.instancias[mem_id].completada = True
                    motor.instancias[mem_id].bloqueada = True
                logger.info(f"      ✅ Instancia cargada: {inst_bd.tipo} (orden {inst_bd.orden_id})")
    finally:
        session.close()

# Procesar nuevas órdenes pendientes (estado='pendiente')
def procesar_nuevas_ordenes():
    session = Session()
    try:
        ordenes_pendientes = session.query(OrdenProduccion).filter_by(estado='pendiente').all()
        if not ordenes_pendientes:
            return
        logger.info(f"📋 {len(ordenes_pendientes)} orden(es) pendiente(s) detectada(s)")
        for orden in ordenes_pendientes:
            logger.info(f"   → Inicializando orden {orden.id} ({orden.numero_orden})")
            exito = orquestador.inicializar_orden(orden.id)
            if exito:
                session.refresh(orden)
                logger.info(f"      ✅ Orden {orden.id} ahora en estado '{orden.estado}'")
            else:
                logger.error(f"      ❌ No se pudo inicializar orden {orden.id}")
        session.commit()
    finally:
        session.close()

# Procesar eventos de la cola (tabla cola_evento)
def procesar_eventos_cola():
    session = Session()
    evento = None  # Para manejar excepción
    try:
        # Obtener siguiente evento pendiente (FIFO)
        evento = session.query(ColaEvento).filter_by(estado='pendiente').order_by(ColaEvento.fecha_creacion).first()
        if not evento:
            return None

        # Marcar como procesando
        evento.estado = 'procesando'
        session.commit()

        logger.info(f"📱 Evento {evento.id}: {evento.red_nombre}.{evento.transicion_nombre} (orden {evento.orden_id})")

        # Procesar con el orquestador
        resultado = orquestador.procesar_evento_planta(
            orden_id=evento.orden_id,
            red_nombre=evento.red_nombre,
            evento_nombre=evento.transicion_nombre,
            recurso_nombre = evento.datos.get('recurso') if evento.datos else None,
            timestamp=datetime.now()
        )

        if resultado:
            # Marcar completado
            evento.estado = 'completado'
            evento.fecha_procesamiento = datetime.now()
            session.commit()
            logger.info(f"   ✅ Evento procesado correctamente")

            # Estabilizar la red después del evento
            iteraciones = orquestador.estabilizar_red(evento.orden_id, max_iteraciones=MAX_ITERACIONES_ESTABILIZACION)
            logger.debug(f"   🔄 Estabilización completada en {iteraciones} iteración(es)")

            # Verificar si la orden terminó
            terminada = orquestador._verificar_y_finalizar_orden(evento.orden_id)
            if terminada:
                logger.info(f"   🏁 Orden {evento.orden_id} finalizada automáticamente")
        else:
            # Marcar error y aumentar intentos
            evento.estado = 'error'
            evento.intentos = (evento.intentos or 0) + 1
            evento.error = "No se pudo procesar el evento (transición no habilitada o error interno)"
            evento.fecha_procesamiento = datetime.now()
            session.commit()
            logger.error(f"   ❌ Error procesando evento")

        return resultado

    except Exception as e:
        session.rollback()
        logger.exception(f"   ❌ Excepción al procesar evento: {e}")
        # Marcar como error si se pudo obtener el evento
        if evento and evento.id:
            try:
                evento = session.query(ColaEvento).get(evento.id)
                if evento:
                    evento.estado = 'error'
                    evento.intentos = (evento.intentos or 0) + 1
                    evento.error = str(e)
                    evento.fecha_procesamiento = datetime.now()
                    session.commit()
            except:
                pass
        return False
    finally:
        session.close()

# Bucle principal
def bucle_principal():
    logger.info("🚀 Iniciando orquestador FÉNIX (modo tabla)")
    logger.info(f"   Intervalo de escaneo: {INTERVALO_SEGUNDOS} s")
    logger.info("   - Nuevas órdenes (estado='pendiente') se inicializan automáticamente")
    logger.info("   - Eventos de la tabla 'cola_evento' se procesan en orden FIFO")
    logger.info("   - Presiona Ctrl+C para detener\n")

    # Carga inicial de redes y instancias activas
    cargar_redes_en_motor()
    cargar_instancias_activas()
    logger.info("   ✅ Estado inicial cargado\n")

    try:
        while True:
            # 1. Procesar nuevas órdenes pendientes
            procesar_nuevas_ordenes()

            # 2. Procesar eventos de la cola (uno por ciclo, para no bloquear)
            procesar_eventos_cola()

            # 3. Procesar mensajes pendientes (handshakes) y automáticas en segundo plano
            #    Esto ya se hace dentro de estabilizar_red después de cada evento,
            #    pero también podemos hacer un barrido periódico por si quedaron colgados.
            with Session() as session:
                ordenes_activas = session.query(OrdenProduccion).filter(
                    OrdenProduccion.estado.in_(['en_produccion', 'pendiente'])
                ).all()
                for orden in ordenes_activas:
                    # Procesar mensajes pendientes no consumidos
                    orquestador.procesar_mensajes_pendientes(orden.id)
                    # Procesar automáticas
                    orquestador._procesar_todas_automaticas(orden.id)
                    # Verificar terminación
                    if orquestador._verificar_y_finalizar_orden(orden.id):
                        logger.info(f"   🏁 Orden {orden.id} finalizada en ciclo de fondo")
                session.commit()

            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        logger.info("\n🛑 Orquestador detenido por el usuario")
        # Persistir estado actual de las instancias en memoria a BD
        with Session() as session:
            for mem_id, inst_mem in motor.instancias.items():
                if inst_mem.bd_id:
                    inst_bd = session.get(InstanciaRed, inst_mem.bd_id)
                    if inst_bd:
                        inst_bd.marcado = inst_mem.marcado
                        inst_bd.token_m = inst_mem.token_m
                        inst_bd.token_c = inst_mem.token_c
                        inst_bd.token_t = inst_mem.token_t
            session.commit()
        logger.info("   ✅ Estado persistido")

if __name__ == "__main__":
    bucle_principal()