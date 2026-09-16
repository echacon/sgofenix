# scripts/diagnosticar_redes_cargadas.py
"""Diagnostica qué redes están realmente cargadas en el motor"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.motor_abtppn_backup import MotorABTPPN
from servicios.orquestador_backup import Orquestador

def diagnosticar():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)
    
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE REDES CARGADAS")
    print("=" * 60)
    
    # Ver qué redes tiene el motor
    print("\n📚 Redes en motor.redes_cargadas:")
    for nombre, red in motor.redes_cargadas.items():
        print(f"   - {nombre}")
        print(f"     Lugares: {list(red.places.keys())[:5]}...")
        print(f"     Transiciones: {list(red.transitions.keys())[:5]}...")
    
    # Crear una orden para ver las instancias
    from modelos.RutaProducto import RutaProducto
    ruta = session.query(RutaProducto).first()
    if ruta:
        print(f"\n📋 Creando orden con ruta: {ruta.nombre}")
        
        orden_id = orquestador.crear_orden_desde_ruta(
            ruta_producto_id=ruta.id,
            cantidad=1000.0,
            prioridad=1
        )
        
        print(f"\n📊 Instancias creadas en memoria:")
        for inst_id, inst in motor.instancias.items():
            print(f"   Instancia {inst_id}:")
            print(f"      Red: {inst.red.nombre}")
            print(f"      Marcado: {inst.marcado}")
            print(f"      Activa: {inst.activa}")
    
    session.close()

if __name__ == "__main__":
    diagnosticar()