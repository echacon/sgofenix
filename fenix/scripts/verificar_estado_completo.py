# verificar_estado_completo.py (versión mejorada)
"""Verifica el estado de una orden específica o todas las órdenes activas"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.ProcesoOcurrente import InstanciaRed

def verificar_estado(orden_id: int = None):
    engine = create_engine("sqlite:///fenix.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    if orden_id:
        instancias = session.query(InstanciaRed).filter_by(orden_id=orden_id, activa=True).all()
        print(f"\n📊 ESTADO DE LA ORDEN {orden_id}")
        print("=" * 50)
    else:
        instancias = session.query(InstanciaRed).filter_by(activa=True).all()
        print(f"\n📊 ESTADO DE TODAS LAS ÓRDENES ACTIVAS")
        print("=" * 50)
    
    current_orden = None
    for inst in instancias:
        if inst.orden_id != current_orden:
            current_orden = inst.orden_id
            print(f"\n📍 ORDEN {current_orden}:")
            print("-" * 30)
        
        print(f"\n   📊 {inst.tipo}:")
        print(f"      Marcado: {inst.marcado}")
        print(f"      Token: {inst.token_m:.2f} kg, ${inst.token_c:.2f}")
    
    session.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--orden", type=int, help="ID de la orden (opcional, muestra todas si no se especifica)")
    args = parser.parse_args()
    
    verificar_estado(args.orden)