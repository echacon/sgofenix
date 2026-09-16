# scripts/verificar_ruta_y_marcados.py
"""Verifica que la ruta y los marcados sean correctos"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RutaProducto import RutaProducto
from utils.parser_pnml import cargar_red_desde_pnml

def verificar():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    ruta = session.query(RutaProducto).filter_by(activo=True).first()
    if not ruta:
        print("❌ No hay ruta activa")
        return
    
    print(f"📋 Ruta: {ruta.nombre}")
    print(f"   Base path: {ruta.base_path}")
    
    config = ruta.obtener_config()
    redes = config.get('redes', {})
    
    print("\n" + "=" * 60)
    print("🔍 VERIFICANDO CADA RED")
    print("=" * 60)
    
    for nombre, info in redes.items():
        pnml_path = Path(ruta.base_path) / info.get('pnml', '')
        print(f"\n📍 {nombre}")
        print(f"   PNML: {pnml_path}")
        print(f"   ¿Existe? {pnml_path.exists()}")
        
        if pnml_path.exists():
            red = cargar_red_desde_pnml(str(pnml_path))
            if red:
                marcado = {}
                for pid, place in red.places.items():
                    if place.marking_inicial > 0:
                        marcado[pid] = place.marking_inicial
                print(f"   Marcado inicial desde PNML: {marcado}")
                
                # Validaciones específicas
                if "integradora" in nombre.lower() or "IntegracionRedes" in nombre:
                    if marcado.get('p1') == 1:
                        print(f"   ✅ CORRECTO: p1=1")
                    else:
                        print(f"   ❌ ERROR: debería tener p1=1, tiene {marcado}")
                
                if "dispersion" in nombre.lower():
                    if marcado.get('p14') == 1:
                        print(f"   ✅ CORRECTO: p14=1")
                    else:
                        print(f"   ❌ ERROR: debería tener p14=1, tiene {marcado}")
                
                if "dilucion" in nombre.lower():
                    if marcado.get('p14') == 1:
                        print(f"   ✅ CORRECTO: p14=1")
                    else:
                        print(f"   ❌ ERROR: debería tener p14=1, tiene {marcado}")
            else:
                print(f"   ❌ No se pudo cargar la red")
    
    session.close()

if __name__ == "__main__":
    verificar()