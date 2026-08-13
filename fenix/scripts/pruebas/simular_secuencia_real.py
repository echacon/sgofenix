# scripts/simular_secuencia_real.py
"""Simula la secuencia real probada en la Jornada 18"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import time

import logging
# Configurar logging para mostrar solo WARNING y ERROR
logging.basicConfig(level=logging.WARNING)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.motor_abtppn_backup import MotorABTPPN
from servicios.orquestador_backup import Orquestador
from modelos.ProcesoOcurrente import EventoRed
from modelos.MensajePendiente import MensajePendiente

# Mapeo de nombres lógicos a nombres reales en BD
MAPEO_REDES = {
    "dispersion": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
    "dilucion": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2",
    "integradora": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4"
}

# Secuencia real del escenario normal (25 eventos)
SECUENCIA_NORMAL = [
    {"red": "dispersion", "transicion": "Asignar equipo", "datos": {}},
    {"red": "dispersion", "transicion": "Cargar auto", "datos": {}},
    {"red": "dispersion", "transicion": "Tolva", "datos": {}},
    {"red": "dispersion", "transicion": "Fin solidos", "datos": {}},
    {"red": "dispersion", "transicion": "Chequeo", "datos": {}},
    {"red": "dilucion", "transicion": "Asignar equipo", "datos": {}},
    {"red": "dilucion", "transicion": "Carga auto", "datos": {}},
    {"red": "dilucion", "transicion": "Fin pigable", "datos": {}},
    {"red": "dispersion", "transicion": "Chequeando", "datos": {}},
    {"red": "dispersion", "transicion": "Transportar", "datos": {}},
    {"red": "dilucion", "transicion": "Recibir dispersion", "datos": {}},
    {"red": "dispersion", "transicion": "Transportando", "datos": {}},
    {"red": "dilucion", "transicion": "Fin carga", "datos": {}},
    {"red": "dilucion", "transicion": "Chequeo", "datos": {}},
    {"red": "dispersion", "transicion": "Libre", "datos": {}},
    {"red": "dilucion", "transicion": "Chequeando", "datos": {}},
    {"red": "dilucion", "transicion": "A tinturar", "datos": {}},
    {"red": "dilucion", "transicion": "Tinturacion", "datos": {}},
    {"red": "dilucion", "transicion": "Para ajuste", "datos": {}},
    {"red": "dilucion", "transicion": "Ajustando", "datos": {}},
    {"red": "dilucion", "transicion": "Chequeo", "datos": {}},
    {"red": "dilucion", "transicion": "Chequeando", "datos": {}},
    {"red": "dilucion", "transicion": "No conforme", "datos": {}},
    {"red": "dilucion", "transicion": "Descartar", "datos": {}},
    {"red": "dilucion", "transicion": "Libre", "datos": {}}
]

def simular_secuencia_real():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    print("=" * 60)
    print("🏭 SIMULACIÓN - SECUENCIA REAL (Validada J18)")
    print("=" * 60)
    
    # Crear orden
    from modelos.RutaProducto import RutaProducto
    ruta = session.query(RutaProducto).first()
    if not ruta:
        print("❌ No hay ruta registrada")
        return
    
    orden_id = orquestador.crear_orden_desde_ruta(
        ruta_producto_id=ruta.id,
        cantidad=1000.0,
        prioridad=1
    )
    
    if not orden_id:
        print("❌ Falló la creación de la orden")
        return
    
    print(f"\n✅ Orden {orden_id} creada")
    
    # Ejecutar secuencia
    print(f"\n🎬 Ejecutando {len(SECUENCIA_NORMAL)} eventos...")
    print("-" * 60)
    
    exitos = 0
    fallos = 0
    
    for i, evento in enumerate(SECUENCIA_NORMAL, 1):
        red_logica = evento["red"]
        red_real = MAPEO_REDES.get(red_logica, red_logica)
        transicion = evento["transicion"]
        
        print(f"\n🔹 Evento {i:2d}: {red_logica} → {red_real}.{transicion}")
        
        exito, mensaje = orquestador.procesar_evento_externo(
            orden_id=orden_id,
            red_nombre=red_real,
            nombre_evento=transicion,
            datos={"recurso": {"id": 1, "nombre": f"REC-{red_logica.upper()}"}}
        )

        orquestador._procesar_cadena_completa_hasta_estabilizar(orden_id)
        
        if exito:
            print(f"   ✅ OK")
            exitos += 1
        else:
            print(f"   ❌ {mensaje}")
            fallos += 1
        
        # Pequeña pausa para ver el progreso
        time.sleep(0.2)
    
    # Resultados
    print("\n" + "=" * 60)
    print("📊 RESULTADOS DE LA SIMULACIÓN")
    print("=" * 60)
    
    print(f"\n📈 Estadísticas:")
    print(f"   Eventos exitosos: {exitos}")
    print(f"   Eventos fallidos: {fallos}")
    print(f"   Total: {len(SECUENCIA_NORMAL)}")
    
    # Estado final de las instancias
    print("\n📊 Estado final:")
    for inst_id, inst in motor.instancias.items():
        if inst.orden_id == orden_id:
            # Obtener nombre lógico
            red_logica = "DESCONOCIDA"
            for logica, real in MAPEO_REDES.items():
                if real == inst.red.nombre:
                    red_logica = logica
                    break
            print(f"   {red_logica} ({inst.red.nombre}):")
            print(f"      Activa: {inst.activa}")
            print(f"      Marcado: {inst.marcado}")
            print(f"      Token: {inst.token.material if inst.token else 'N/A'}")
    
    # Eventos registrados en BD
    eventos_bd = session.query(EventoRed).filter_by(orden_id=orden_id).all()
    print(f"\n📝 Eventos registrados en BD: {len(eventos_bd)}")
    
    # Mensajes pendientes
    mensajes = session.query(MensajePendiente).filter_by(orden_id=orden_id, consumido=False).all()
    print(f"📨 Mensajes pendientes: {len(mensajes)}")
    
    # Verificar si la orden terminó
    orden = session.query(type(ruta).__bases__[0]).filter_by(id=orden_id).first()
    if orden:
        print(f"\n🏁 Estado de la orden: {orden.estado}")
    
    session.close()
    
    print("\n" + "=" * 60)
    print("✅ SIMULACIÓN COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    simular_secuencia_real()