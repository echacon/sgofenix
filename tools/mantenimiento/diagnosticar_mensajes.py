# scripts/diagnosticar_mensajes.py
"""Diagnostica los mensajes pendientes"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.MensajePendiente import MensajePendiente

def diagnosticar():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=" * 60)
    print("📨 MENSAJES PENDIENTES")
    print("=" * 60)
    
    # Ver últimos mensajes no consumidos
    mensajes = session.query(MensajePendiente).filter_by(consumido=False).order_by(MensajePendiente.id.desc()).limit(10).all()
    
    if not mensajes:
        print("✅ No hay mensajes pendientes")
    else:
        print(f"📨 {len(mensajes)} mensajes pendientes:\n")
        for msg in mensajes:
            print(f"   ID: {msg.id}")
            print(f"   Orden: {msg.orden_id}")
            print(f"   De: {msg.red_origen}.{msg.transicion_origen}")
            print(f"   Para: {msg.red_destino}.{msg.evento}")
            print(f"   Datos: {msg.datos}")
            print(f"   Consumido: {msg.consumido}")
            print("-" * 40)
    
    session.close()

if __name__ == "__main__":
    diagnosticar()