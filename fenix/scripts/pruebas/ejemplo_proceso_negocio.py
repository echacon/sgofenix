#!/usr/bin/env python3
"""
Ejemplo de Proceso de Negocio con Suscripciones
Demuestra el flujo completo: Pedido → Planificación → Producción → Completado
"""

import sys
from pathlib import Path
from datetime import datetime
import time

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.motor_abtppn_bacup import MotorABTPPN, TokenColoreado
from modelos.RedPetri import RedPetri
from modelos.SuscripcionEvento import SuscripcionEvento
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.DocumentosNegocio import OrdenProduccion


def setup_bd():
    """Configura la base de datos"""
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    return Session()


def registrar_red_bd(session, nombre_red, tipo_red='negocio'):
    """Registra una red en la BD si no existe"""
    red = session.query(RedPetri).filter_by(nombre=nombre_red).first()
    if not red:
        red = RedPetri(
            nombre=nombre_red,
            descripcion=f"Red de {tipo_red}",
            version=1,
            lugares={},
            transiciones={},
            arcos={},
            tipo_red=tipo_red,
            activo=True
        )
        session.add(red)
        session.commit()
        print(f"✅ Red registrada: {nombre_red} (ID: {red.id})")
    else:
        print(f"📌 Red ya existe: {nombre_red} (ID: {red.id})")
    return red


def crear_suscripcion(session, red_origen_nombre, evento, red_destino_nombre, accion, destino_param):
    """Crea una suscripción entre redes"""
    red_origen = session.query(RedPetri).filter_by(nombre=red_origen_nombre).first()
    red_destino = session.query(RedPetri).filter_by(nombre=red_destino_nombre).first()
    
    if not red_origen or not red_destino:
        print(f"❌ No se encontraron redes: {red_origen_nombre} → {red_destino_nombre}")
        return None
    
    # Verificar si ya existe
    existente = session.query(SuscripcionEvento).filter_by(
        red_origen_id=red_origen.id,
        evento=evento,
        red_destino_id=red_destino.id,
        accion=accion
    ).first()
    
    if existente:
        print(f"📌 Suscripción ya existe: {red_origen_nombre}.{evento} → {red_destino_nombre}")
        return existente
    
    suscripcion = SuscripcionEvento(
        red_origen_id=red_origen.id,
        evento=evento,
        red_destino_id=red_destino.id,
        accion=accion,
        destino_param=destino_param,
        parametros={},
        activo=True
    )
    session.add(suscripcion)
    session.commit()
    print(f"✅ Suscripción creada: {red_origen_nombre}.{evento} → {red_destino_nombre} ({accion}: {destino_param})")
    return suscripcion


def crear_orden_produccion(session, producto_nombre, cantidad):
    """Crea una orden de producción de prueba"""
    from modelos.Producto import Producto, HolonRuta
    from modelos.Taxonomia import FamiliaProducto, PatronDeRuta
    
    producto = session.query(Producto).filter_by(nombre=producto_nombre).first()
    if not producto:
        # Buscar una familia existente
        familia = session.query(FamiliaProducto).first()
        if not familia:
            # Crear familia dummy
            familia = FamiliaProducto(
                nombre="Pinturas Base Agua",
                descripcion="Familia de pinturas base agua"
            )
            session.add(familia)
            session.commit()
            print(f"   📌 Familia creada: {familia.nombre} (ID: {familia.id})")
        
        # Crear producto con los campos correctos
        producto = Producto(
            nombre=producto_nombre,
            codigo_interno=f"PROD-{producto_nombre[:3].upper()}",
            es_fabricado=True,
            es_adquirido=False,
            es_final=True,
            es_insumo=False,
            es_intermedio=False,
            id_tipoDeProducto=familia.id
        )
        session.add(producto)
        session.commit()
        print(f"   📌 Producto creado: {producto.nombre} (ID: {producto.id})")
        
        # Crear un HolonRuta para el producto
        patron = session.query(PatronDeRuta).first()
        if patron:
            holon_ruta = HolonRuta(
                producto_id=producto.id,
                fechaModelo=datetime.now().strftime("%Y-%m-%d"),
                nombreRuta="Ruta Estándar",
                id_tipoRuta=patron.id
            )
            session.add(holon_ruta)
            session.commit()
            print(f"   📌 HolonRuta creado para producto")
    
    orden = OrdenProduccion(
        producto_id=producto.id,
        numero_orden=f"ORD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        cantidad=cantidad,
        estado='pendiente',
        fecha_solicitud=datetime.now(),
        prioridad=1
    )
    session.add(orden)
    session.commit()
    print(f"✅ Orden de producción creada: ID {orden.id} - {producto_nombre} x{cantidad}")
    return orden

def ejecutar_simulacion_produccion(motor, orden_id, token_inicial):
    """Simula la ejecución de una orden de producción"""
    print(f"\n🏭 INICIANDO SIMULACIÓN DE PRODUCCIÓN para orden {orden_id}")
    
    # Crear instancia de la ruta de producto
    instancia_id = motor.crear_instancia(
        red_nombre="Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml",
        orden_id=orden_id,
        token_inicial=token_inicial
    )
    
    if not instancia_id:
        print("❌ No se pudo crear instancia de producción")
        return False
    
    # Simular pasos de producción
    pasos = [
        ('t1', "OrdenEn WIP"),
        ('t2', "Iniciar disp - Refinamiento a dispersión"),
    ]
    
    for trans_id, desc in pasos:
        print(f"   ⏳ {desc}...")
        exito, mensaje = motor.disparar(instancia_id, trans_id)
        print(f"      → {mensaje}")
        time.sleep(1)  # Pequeña pausa para visualizar
    
    print(f"✅ Simulación de producción completada para orden {orden_id}")
    return True


def main():
    print("=" * 70)
    print("🎯 EJEMPLO: PROCESO DE NEGOCIO CON SUSCRIPCIONES")
    print("=" * 70)
    
    # 1. Configurar BD y motor
    session = setup_bd()
    motor = MotorABTPPN(db_session=session)
    motor.set_session(session)
    
    # 2. Registrar redes en BD
    print("\n📋 REGISTRANDO REDES...")
    red_negocio = registrar_red_bd(session, "ProcesoNegocio_Pedido", "negocio")
    red_produccion = registrar_red_bd(session, "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", "ruta")
    
    # 3. Configurar refinamientos (si no existen)
    print("\n🔧 CONFIGURANDO REFINAMIENTOS...")
    motor.configurar_refinamiento(
        "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
        "Iniciar disp",
        "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml"
    )
    
    motor.mapeo_eventos["Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml"] = {
        "Libre": "27",
        "Descargar": "11",
        "Transportar": "3"
    }
    
    # 4. Crear suscripciones (eventos entre procesos)
    print("\n🔗 CREANDO SUSCRIPCIONES...")
    
    # Suscripción 1: Cuando se inicia producción, crear orden (simulación)
    # Nota: Esto es conceptual - en realidad la orden ya existe
    crear_suscripcion(
        session, "ProcesoNegocio_Pedido", "transicion_disparada",
        "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", "crear_instancia", ""
    )
    
    # Suscripción 2: Cuando producción completa, notificar a proceso negocio
    crear_suscripcion(
        session, "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", "operacion_completada",
        "ProcesoNegocio_Pedido", "disparar_transicion", "Orden_Completada_Evento"
    )
    
    # 5. Crear orden de producción
    print("\n📦 CREANDO ORDEN DE PRODUCCIÓN...")
    orden = crear_orden_produccion(session, "Pintura Base Agua 20L", 100)
    
    # 6. Crear token inicial
    token = TokenColoreado(
        orden_id=f"ORD-{orden.id}",
        material=1000.0,
        coste=0.0,
        timestamp=datetime.now()
    )
    
    # 7. Iniciar proceso de negocio
    print("\n🚀 INICIANDO PROCESO DE NEGOCIO...")
    instancia_negocio_id = motor.crear_instancia(
        red_nombre="ProcesoNegocio_Pedido.pnml",
        orden_id=orden.id,
        token_inicial=token
    )
    
    if not instancia_negocio_id:
        print("❌ No se pudo iniciar el proceso de negocio")
        return
    
    # 8. Simular el flujo del proceso de negocio
    print("\n📋 EJECUTANDO PROCESO DE NEGOCIO...")
    
    # Paso 1: Recibir pedido
    print("   1. Recibiendo pedido...")
    exito, mensaje = motor.disparar(instancia_negocio_id, 't1')
    print(f"      → {mensaje}")
    
    # Paso 2: Planificar (simulación)
    print("   2. Planificando producción...")
    exito, mensaje = motor.disparar(instancia_negocio_id, 't2')
    print(f"      → {mensaje}")
    
    # Paso 3: Iniciar producción (esto debería disparar la suscripción)
    print("   3. Iniciando producción (dispara suscripción)...")
    exito, mensaje = motor.disparar(instancia_negocio_id, 't3')
    print(f"      → {mensaje}")
    
    # 9. Simular producción (esto normalmente sería automático por suscripción)
    # Por ahora lo hacemos manualmente para demostración
    print("\n🏭 SIMULANDO PRODUCCIÓN...")
    
    # Buscar instancia de producción creada por suscripción
    instancia_produccion_id = None
    for inst_id, inst in motor.instancias.items():
        if inst.orden_id == orden.id and inst.red.nombre == "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4":
            instancia_produccion_id = inst_id
            break
    
    if instancia_produccion_id:
        print(f"   📌 Instancia de producción encontrada: ID {instancia_produccion_id}")
        
        # Ejecutar producción
        exito, mensaje = motor.disparar(instancia_produccion_id, 't1')
        print(f"      → {mensaje}")
        
        exito, mensaje = motor.disparar(instancia_produccion_id, 't2')
        print(f"      → {mensaje}")
        
        # Esperar a que la red hija termine y notifique
        print("\n   ⏳ Esperando notificación de fin de producción...")
        time.sleep(2)
        
        # Verificar si se disparó el evento de completado
        print("\n   🔔 Verificando notificación a proceso negocio...")
    else:
        print("   ⚠️ No se encontró instancia de producción automática")
        print("   → Ejecutando producción manual...")
        ejecutar_simulacion_produccion(motor, orden.id, token)
    
    # 10. Mostrar estado final
    print("\n" + "=" * 70)
    print("📊 ESTADO FINAL")
    print("=" * 70)
    
    print("\n🔹 Instancias activas:")
    for inst in motor.listar_instancias_activas():
        print(f"   ID {inst['id']}: {inst['red']} - Activa: {inst['activa']}")
    
    print("\n🔹 Historial de eventos de la orden:")
    historial = motor.obtener_historial(orden.id)
    for evento in historial[-10:]:  # últimos 10 eventos
        print(f"   {evento['timestamp'][11:19]} - {evento['transicion_nombre']}")
    
    print("\n" + "=" * 70)
    print("✅ EJEMPLO COMPLETADO")
    print("=" * 70)
    
    session.close()


if __name__ == "__main__":
    main()