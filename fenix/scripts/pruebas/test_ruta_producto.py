# scripts/test_ruta_producto.py
"""Prueba la integración de RutaProducto con el Orquestador"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

import logging
logging.basicConfig(level=logging.DEBUG)
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.motor_abtppn_backup import MotorABTPPN
from servicios.orquestador_backup import Orquestador
from modelos.RutaProducto import RutaProducto
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_simular_flujo_completo(orden_id: int):
    """Prueba 6: Simular un flujo completo de eventos"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 6: Simular flujo completo de eventos")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Verificar estado inicial
    estado = orquestador.obtener_estado_orden(orden_id)
    print(f"\n📊 Estado inicial de la orden {orden_id}:")
    for inst in estado.get('instancias', []):
        print(f"   {inst.get('red_nombre')}: marcado={inst.get('marcado', {})}")
    
    # Simular eventos según la secuencia de producción
    # Estos nombres deben coincidir con las transiciones en tus PNML
    
    eventos = [
        # Red integradora (padre)
        {"red": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", 
         "evento": "IniciarProceso", 
         "datos": {"recurso": {"id": 1, "nombre": "LINEA-01"}}},
        
        {"red": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", 
         "evento": "DosificarBase", 
         "datos": {"recurso": {"id": 2, "nombre": "DOS-01"}, "cantidad": 500}},
        
        # Red de dispersión
        {"red": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", 
         "evento": "IniciarDispersion", 
         "datos": {"recurso": {"id": 3, "nombre": "DISP-01"}}},
        
        {"red": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", 
         "evento": "AgregarPigmento", 
         "datos": {"recurso": {"id": 3, "nombre": "DISP-01"}, "cantidad": 100}},
        
        {"red": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", 
         "evento": "FinalizarDispersion", 
         "datos": {"recurso": {"id": 3, "nombre": "DISP-01"}}},
        
        # Red de dilución
        {"red": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2", 
         "evento": "IniciarDilucion", 
         "datos": {"recurso": {"id": 4, "nombre": "DIL-01"}}},
        
        {"red": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2", 
         "evento": "AgregarAgua", 
         "datos": {"recurso": {"id": 4, "nombre": "DIL-01"}, "cantidad": 300}},
        
        {"red": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2", 
         "evento": "FinalizarDilucion", 
         "datos": {"recurso": {"id": 4, "nombre": "DIL-01"}}},
        
        # Finalizar integradora
        {"red": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4", 
         "evento": "FinalizarProduccion", 
         "datos": {"recurso": {"id": 1, "nombre": "LINEA-01"}}},
    ]
    
    print("\n🎬 Simulando eventos...")
    for i, evt in enumerate(eventos, 1):
        print(f"\n   Evento {i}: {evt['red']}.{evt['evento']}")
        
        exito, mensaje = orquestador.procesar_evento_externo(
            orden_id=orden_id,
            red_nombre=evt['red'],
            nombre_evento=evt['evento'],
            datos=evt['datos']
        )
        
        if exito:
            print(f"      ✅ Procesado correctamente")
        else:
            print(f"      ❌ Falló: {mensaje}")
    
    # Verificar estado final
    print("\n📊 Estado final de la orden:")
    estado = orquestador.obtener_estado_orden(orden_id)
    for inst in estado.get('instancias', []):
        print(f"   {inst.get('red_nombre')}:")
        print(f"      Activa: {inst.get('activa')}")
        print(f"      Marcado: {inst.get('marcado', {})}")
    
    # Verificar eventos registrados
    from modelos.ProcesoOcurrente import EventoRed
    eventos_registrados = session.query(EventoRed).filter_by(orden_id=orden_id).all()
    print(f"\n📝 Eventos registrados en BD: {len(eventos_registrados)}")
    for evt in eventos_registrados[-5:]:  # últimos 5
        print(f"   - {evt.transicion_nombre} @ {evt.timestamp}")
    
    session.close()
    return True


def test_crear_y_simular():
    """Prueba combinada: crear orden y simular eventos (usando el MISMO orquestador)"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA COMPLETA: Crear orden + Simular eventos")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Crear UN SOLO motor y orquestador para toda la prueba
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Obtener primera ruta
    rutas = orquestador.obtener_rutas_disponibles()
    if not rutas:
        print("❌ No hay rutas disponibles")
        session.close()
        return None
    
    ruta_id = rutas[0]['id']
    print(f"📋 Usando ruta ID: {ruta_id}")
    
    # Crear orden (esto debe dejar instancias en el motor)
    orden_id = orquestador.crear_orden_desde_ruta(
        ruta_producto_id=ruta_id,
        cantidad=1000.0,
        prioridad=1
    )
    
    if not orden_id:
        print("❌ Falló la creación de la orden")
        session.close()
        return None
    
    print(f"\n✅ Orden creada: {orden_id}")
    
    # Verificar que las instancias estén en el motor
    print(f"\n📊 Instancias en motor después de crear: {len(motor.instancias)}")
    for inst_id, inst in motor.instancias.items():
        print(f"   - {inst.red.nombre} (activa: {inst.activa})")
    
    # SIMULAR EVENTOS CON EL MISMO ORQUESTADOR
    print("\n🎬 Simulando eventos...")
    
    # Lista de eventos (ajusta los nombres según tus transiciones reales)
    eventos = [
        # Primero, obtener las transiciones automáticas disponibles
    ]
    
    # Mejor: Procesar automáticas primero
    print("\n⚙️ Procesando transiciones automáticas...")
    orquestador._procesar_automaticas_orden(orden_id)
    
    # Mostrar estado actual
    estado = orquestador.obtener_estado_orden(orden_id)
    print(f"\n📊 Estado después de automáticas:")
    for inst in estado.get('instancias', []):
        print(f"   {inst.get('red_nombre')}: marcado={inst.get('marcado', {})}")
    
    # Verificar eventos registrados
    from modelos.ProcesoOcurrente import EventoRed
    eventos_registrados = session.query(EventoRed).filter_by(orden_id=orden_id).all()
    print(f"\n📝 Eventos registrados en BD: {len(eventos_registrados)}")
    
    session.close()
    return orden_id

# Modificar run_all_tests() para incluir la nueva prueba

def test_obtener_rutas():
    """Prueba 1: Obtener rutas disponibles"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 1: Obtener rutas disponibles")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    rutas = orquestador.obtener_rutas_disponibles()
    
    if not rutas:
        print("❌ No hay rutas registradas")
        print("\nPrimero ejecuta: python scripts/inicializar_ruta_producto.py")
        session.close()
        return False
    
    print(f"✅ Se encontraron {len(rutas)} rutas:")
    for ruta in rutas:
        print(f"   ID: {ruta['id']} - {ruta['nombre']} v{ruta['version']}")
        if ruta.get('descripcion'):
            print(f"       {ruta['descripcion']}")
    
    session.close()
    return True


def test_crear_orden_desde_ruta():
    """Prueba 2: Crear una orden desde una ruta"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 2: Crear orden desde ruta")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Obtener primera ruta
    rutas = orquestador.obtener_rutas_disponibles()
    if not rutas:
        print("❌ No hay rutas disponibles")
        session.close()
        return None
    
    ruta_id = rutas[0]['id']
    print(f"📋 Usando ruta ID: {ruta_id}")
    
    # Crear orden
    orden_id = orquestador.crear_orden_desde_ruta(
        ruta_producto_id=ruta_id,
        cantidad=1000.0,
        prioridad=1
    )
    
    if orden_id:
        print(f"\n✅ Orden creada exitosamente!")
        print(f"   ID: {orden_id}")
        
        # Verificar en BD
        orden = session.query(OrdenProduccion).get(orden_id)
        if orden:
            print(f"   Número: {orden.numero_orden}")
            print(f"   Estado: {orden.estado}")
            print(f"   Producto ID: {orden.producto_id}")
            print(f"   Ruta Producto ID: {orden.ruta_producto_id}")
        
        session.close()
        return orden_id
    else:
        print("❌ Falló la creación de la orden")
        session.close()
        return None


def test_estado_orden(orden_id: int):
    """Prueba 3: Obtener estado de una orden"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 3: Obtener estado de orden")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    estado = orquestador.obtener_estado_orden(orden_id)
    
    print(f"\n📊 Estado de orden {orden_id}:")
    print(f"   Número: {estado.get('numero_orden', 'N/A')}")
    print(f"   Estado: {estado.get('estado', 'N/A')}")
    print(f"   Instancias activas: {len(estado.get('instancias', []))}")
    
    for inst in estado.get('instancias', []):
        print(f"\n   🌐 Red: {inst.get('red_nombre', 'N/A')}")
        print(f"      Activa: {inst.get('activa', False)}")
        print(f"      Marcado: {inst.get('marcado', {})}")
        if inst.get('token'):
            print(f"      Token: {inst.get('token')}")
    
    session.close()
    return True


def test_instancias_bd(orden_id: int):
    """Prueba 4: Verificar instancias en BD"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 4: Verificar instancias en BD")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    instancias = session.query(InstanciaRed).filter_by(
        orden_id=orden_id, activa=True
    ).all()
    
    print(f"\n📋 Instancias para orden {orden_id}:")
    for inst in instancias:
        print(f"\n   ID: {inst.id}")
        print(f"   Tipo: {inst.tipo}")
        print(f"   Activa: {inst.activa}")
        print(f"   Marcado: {inst.marcado}")
        print(f"   Token O: {inst.token_o}")
        print(f"   Token M: {inst.token_m}")
        print(f"   Recursos ocupados: {inst.recursos_ocupados}")
    
    session.close()
    return True


def test_estado_ruta():
    """Prueba 5: Obtener estado de una ruta"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 5: Obtener estado de ruta")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    rutas = orquestador.obtener_rutas_disponibles()
    if not rutas:
        print("❌ No hay rutas")
        session.close()
        return False
    
    for ruta in rutas:
        estado = orquestador.obtener_estado_ruta(ruta['id'])
        if estado:
            print(f"\n📊 Ruta: {estado['nombre']} v{estado['version']}")
            print(f"   Activa: {estado['activo']}")
            print(f"   Órdenes por estado:")
            for estado_nombre, count in estado['ordenes_por_estado'].items():
                if count > 0:
                    print(f"      - {estado_nombre}: {count}")
            print(f"   Total órdenes: {estado['total_ordenes']}")
    
    session.close()
    return True


def test_simular_evento_simple(orden_id: int):
    """Prueba 6: Simular un evento simple (si hay transiciones disponibles)"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 6: Simular evento simple")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Obtener estado para ver qué eventos están disponibles
    estado = orquestador.obtener_estado_orden(orden_id)
    
    # Buscar alguna transición automática o evento posible
    # Esto depende de tu red específica
    print(f"\n💡 Para probar eventos, necesitas conocer los nombres de las transiciones")
    print(f"   en tus redes. Ejemplo:")
    print(f"   evento = orquestador.procesar_evento_externo(")
    print(f"       orden_id={orden_id},")
    print(f"       red_nombre='integradora',")
    print(f"       nombre_evento='DosificarBase',")
    print(f"       datos={{'recurso': {{'id': 1, 'nombre': 'DOS-01'}}}}")
    print(f"   )")
    
    session.close()
    return True


def test_recuperacion_post_reinicio():
    """Prueba 7: Simular recuperación después de reinicio"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 7: Recuperación post-reinicio")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("\n🔄 Simulando reinicio del sistema...")
    
    # Crear nuevo motor y orquestador (como después de un reinicio)
    motor_nuevo = MotorABTPPN()
    orquestador_nuevo = Orquestador(motor_nuevo, session)
    
    # Cargar órdenes activas
    orquestador_nuevo.cargar_ordenes_activas()
    
    # Verificar instancias recuperadas
    print(f"\n📊 Instancias en memoria después de recuperación:")
    print(f"   Total instancias en motor: {len(motor_nuevo.instancias)}")
    
    for inst_id, inst_mem in motor_nuevo.instancias.items():
        print(f"\n   Instancia ID: {inst_id}")
        print(f"   Orden ID: {inst_mem.orden_id}")
        print(f"   Red: {inst_mem.red.nombre}")
        print(f"   Activa: {inst_mem.activa}")
        print(f"   Marcado: {inst_mem.marcado}")
    
    session.close()
    return True


def test_limpiar_ordenes_antiguas():
    """Limpiar órdenes de prueba antiguas (opcional)"""
    print("\n" + "=" * 60)
    print("🧹 LIMPIEZA: Eliminar órdenes de prueba antiguas")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Buscar órdenes completadas o canceladas
    ordenes = session.query(OrdenProduccion).filter(
        OrdenProduccion.estado.in_(['completada', 'cancelada'])
    ).all()
    
    if ordenes:
        print(f"\n📋 Órdenes para limpieza: {len(ordenes)}")
        for orden in ordenes:
            print(f"   Orden {orden.id}: {orden.estado} - {orden.numero_orden}")
            
            # Opcional: eliminar o archivar
            # session.delete(orden)
        
        # session.commit()
        print("\n⚠️ No se eliminaron automáticamente. Descomenta para eliminar.")
    else:
        print("\n✅ No hay órdenes para limpiar")
    
    session.close()
    return True


def run_all_tests():
    """Ejecuta todas las pruebas en secuencia con el MISMO orquestador"""
    print("\n" + "=" * 60)
    print("🚀 INICIANDO PRUEBAS DE RUTA PRODUCTO")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Crear UN SOLO motor y orquestador
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Prueba 1: Obtener rutas
    rutas = orquestador.obtener_rutas_disponibles()
    if not rutas:
        print("❌ No hay rutas disponibles")
        return
    print(f"✅ Se encontraron {len(rutas)} rutas")
    
    # Prueba 2: Crear orden
    orden_id = orquestador.crear_orden_desde_ruta(
        ruta_producto_id=rutas[0]['id'],
        cantidad=1000.0,
        prioridad=1
    )
    if not orden_id:
        print("❌ No se pudo crear orden")
        return
    print(f"✅ Orden creada: {orden_id}")
    
    # Prueba 3: Verificar instancias en motor
    print(f"\n📊 Instancias en motor: {len(motor.instancias)}")
    for inst_id, inst in motor.instancias.items():
        print(f"   - {inst.red.nombre}: activa={inst.activa}")
    
    # Prueba 4: Procesar automáticas
    print("\n⚙️ Procesando transiciones automáticas...")
    orquestador._procesar_automaticas_orden(orden_id)
    
    # Prueba 5: Mostrar estado final
    estado = orquestador.obtener_estado_orden(orden_id)
    print(f"\n📊 Estado final:")
    for inst in estado.get('instancias', []):
        print(f"   {inst.get('red_nombre')}: {inst.get('marcado', {})}")
    
    # Prueba 6: Verificar eventos
    from modelos.ProcesoOcurrente import EventoRed
    eventos = session.query(EventoRed).filter_by(orden_id=orden_id).all()
    print(f"\n📝 Eventos registrados: {len(eventos)}")
    
    session.close()

def test_simular_con_mismo_orquestador(orquestador, orden_id):
    """Simula eventos usando el mismo orquestador que creó la orden"""
    print("\n🎬 Simulando eventos...")
    
    # Obtener transiciones habilitadas
    for inst_id, inst in orquestador.motor.instancias.items():
        if inst.orden_id == orden_id:
            habilitadas = orquestador.motor.obtener_transiciones_habilitadas(inst_id)
            print(f"\n   Red {inst.red.nombre}:")
            print(f"      Transiciones habilitadas: {habilitadas}")
            for tid in habilitadas:
                trans = inst.red.transitions[tid]
                print(f"         - {trans.nombre} (automática: {trans.trigger_type == 'auto'})")
                
def test_ruta_especifica(ruta_id: int):
    """Prueba una ruta específica por ID"""
    print("\n" + "=" * 60)
    print(f"🧪 PROBANDO RUTA ESPECÍFICA ID: {ruta_id}")
    print("=" * 60)
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Crear orden
    orden_id = orquestador.crear_orden_desde_ruta(
        ruta_producto_id=ruta_id,
        cantidad=500.0,
        prioridad=2
    )
    
    if orden_id:
        print(f"\n✅ Orden {orden_id} creada desde ruta {ruta_id}")
        
        # Mostrar estado
        estado = orquestador.obtener_estado_orden(orden_id)
        print(f"\n📊 Estado inicial:")
        for inst in estado.get('instancias', []):
            print(f"   {inst.get('red_nombre')}: {inst.get('marcado', {})}")
    else:
        print(f"\n❌ No se pudo crear orden desde ruta {ruta_id}")
    
    session.close()
    return orden_id


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Pruebas de RutaProducto')
    parser.add_argument('--test', type=str, 
                       choices=['all', 'rutas', 'crear', 'estado', 'ruta', 'recuperacion', 'simular', 'completo'],
                       default='all', help='Prueba específica a ejecutar')
    parser.add_argument('--orden-id', type=int, help='ID de orden para pruebas específicas')
    parser.add_argument('--ruta-id', type=int, help='ID de ruta específica')
    
    args = parser.parse_args()
    
    if args.test == 'rutas':
        test_obtener_rutas()
    elif args.test == 'crear':
        test_crear_orden_desde_ruta()
    elif args.test == 'estado':
        if args.orden_id:
            test_estado_orden(args.orden_id)
        else:
            print("❌ Necesitas --orden-id para ver estado")
    elif args.test == 'ruta':
        if args.ruta_id:
            test_ruta_especifica(args.ruta_id)
        else:
            print("❌ Necesitas --ruta-id para probar ruta específica")
    elif args.test == 'recuperacion':
        test_recuperacion_post_reinicio()
    elif args.test == 'simular':
        if args.orden_id:
            test_simular_flujo_completo(args.orden_id)
        else:
            print("❌ Necesitas --orden-id para simular eventos")
    elif args.test == 'completo':
        test_crear_y_simular()
    else:  # all
        run_all_tests()