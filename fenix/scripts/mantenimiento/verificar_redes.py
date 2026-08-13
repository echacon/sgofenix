# scripts/verificar_redes.py
"""Verifica que los archivos PNML existen donde deben"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RutaProducto import RutaProducto

def verificar():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    ruta = session.query(RutaProducto).filter_by(activo=True).first()
    if not ruta:
        print("❌ No hay ruta activa")
        return
    
    # Obtener config del cache
    config = ruta.config_cache
    if not config:
        print("❌ No hay configuración en cache")
        return
    
    print("=" * 70)
    print("🔍 Verificando archivos PNML")
    print("=" * 70)
    
    redes = config.get('redes', {})
    
    for nombre, info in redes.items():
        pnml_rel = info.get('pnml')
        pnml_path = Path(ruta.base_path) / pnml_rel
        
        print(f"\n📄 Red: {nombre}")
        print(f"   Ruta esperada: {pnml_path}")
        
        if pnml_path.exists():
            print(f"   ✅ Archivo existe")
            # Leer marcado inicial
            from utils.parser_pnml import cargar_red_desde_pnml
            red = cargar_red_desde_pnml(str(pnml_path))
            if red:
                marcado = {}
                for pid, place in red.places.items():
                    if place.marking_inicial > 0:
                        marcado[pid] = place.marking_inicial
                print(f"   Marcado inicial: {marcado}")
        else:
            print(f"   ❌ Archivo NO existe")
            # Buscar en directorio redes
            alt_path = Path(ruta.base_path) / 'redes' / f"{nombre}.pnml"
            if alt_path.exists():
                print(f"   💡 Pero existe como: {alt_path.name}")
            else:
                # Listar archivos disponibles
                redes_dir = Path(ruta.base_path) / 'redes'
                if redes_dir.exists():
                    disponibles = list(redes_dir.glob("*.pnml"))
                    if disponibles:
                        print(f"   📁 Archivos disponibles en redes/:")
                        for f in disponibles:
                            print(f"      - {f.name}")

if __name__ == "__main__":
    verificar()