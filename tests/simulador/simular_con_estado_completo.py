# scripts/simular_con_estado_completo.py
"""Simula mostrando el estado completo después de cada evento"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import time
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.motor_abtppn_backup import MotorABTPPN
from servicios.orquestador_backup import Orquestador
from modelos.RutaProducto import RutaProducto

# Mapeo de nombres lógicos a reales
MAPEO_REDES = {
    "dispersion": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
    "dilucion": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2",
    "integradora": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4"
}

# Secuencia de eventos (ajustar según necesidad)
SECUENCIA = [
    ("dispersion", "Asignar equipo"),
    ("dispersion", "Cargar auto"),
    ("dispersion", "Tolva"),
    ("dispersion", "Fin solidos"),
    ("dispersion", "Chequeo"),
    ("dilucion", "Asignar equipo"),
    ("dilucion", "Carga auto"),
    ("dilucion", "Fin pigable"),
    ("dispersion", "Chequeando"),
    ("dispersion", "Transportar"),
    ("dilucion", "Recibir dispersion"),
    ("dispersion", "Transportando"),
    ("dilucion", "Fin carga"),
    ("dilucion", "Chequeo"),
    ("dispersion", "Libre"),
    ("dilucion", "Chequeando"),
    ("dilucion", "A tinturar"),
    ("dilucion", "Tinturacion"),
    ("dilucion", "Para ajuste"),
    ("dilucion", "Ajustando"),
    ("dilucion", "Chequeo"),
    ("dilucion", "Chequeando"),
    ("dilucion", "No conforme"),
    ("dilucion", "Descartar"),
    ("dilucion", "Libre"),
]

def mostrar_estado(motor, orden_id, paso_numero, evento_desc):
    """Muestra el estado completo de todas las redes"""
    print(f"\n{'='*60}")
    print(f"📊 ESTADO DESPUÉS DE EVENTO {paso_numero}: {evento_desc}")
    print(f"{'='*60}")
    
    for nombre_logico, nombre_real in MAPEO_REDES.items():
        # Buscar instancia
        instancia = None
        for inst_id, inst in motor.instancias.items():
            if inst.orden_id == orden_id and inst.red.nombre == nombre_real:
                instancia = inst
                break
        
        if instancia:
            print(f"\n📍 {nombre_logico.upper()} ({nombre_real}):")
            print(f"   Activa: {instancia.activa}")
            print(f"   Marcado: {instancia.marcado}")
            if instancia.token:
                print(f"   Token: {instancia.token.material}")
            
            # Mostrar transiciones habilitadas (próximos pasos posibles)
            habilitadas = motor.obtener_transiciones_habilitadas(inst_id)
            if habilitadas:
                print(f"   Próximas habilitadas:")
                for tid in habilitadas[:5]:
                    trans = instancia.red.transitions[tid]
                    print(f"      - {trans.nombre} ({trans.trigger_type})")
        else:
            print(f"\n📍 {nombre_logico.upper()}: No encontrada")
    
    print(f"\n{'-'*60}")

def simular_con_estado():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    # Obtener ruta
    ruta = session.query(RutaProducto).first()
    if not ruta:
        print("❌ No hay ruta")
        return
    
    print("=" * 60)
    print("🏭 SIMULACIÓN CON ESTADO COMPLETO")
    print("=" * 60)
    
    # Crear orden
    orden_id = orquestador.crear_orden_desde_ruta(ruta.id, 1000.0)
    if not orden_id:
        print("❌ No se pudo crear orden")
        return
    
    print(f"\n✅ Orden {orden_id} creada")
    
    # Mostrar estado inicial
    mostrar_estado(motor, orden_id, 0, "INICIAL")
    
    # Ejecutar eventos
    exitos = 0
    fallos = 0
    
    for i, (red_logica, evento) in enumerate(SECUENCIA, 1):
        red_real = MAPEO_REDES[red_logica]
        
        print(f"\n🔹 EVENTO {i}: {red_logica}.{evento}")
        
        exito, msg = orquestador.procesar_evento_externo(
            orden_id, red_real, evento, {"recurso": {"id": 1, "nombre": "TEST"}}
        )
        
        if exito:
            print(f"   ✅ OK")
            exitos += 1
        else:
            print(f"   ❌ {msg}")
            fallos += 1
        
        # Mostrar estado COMPLETO después de cada evento
        mostrar_estado(motor, orden_id, i, f"{red_logica}.{evento}")
        
        time.sleep(0.5)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"   Eventos exitosos: {exitos}")
    print(f"   Eventos fallidos: {fallos}")
    print(f"   Total: {len(SECUENCIA)}")
    
    session.close()

if __name__ == "__main__":
    simular_con_estado()