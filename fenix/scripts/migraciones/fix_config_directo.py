# scripts/sync_config_to_db.py
"""Sincroniza la configuración del archivo con la base de datos"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RutaProducto import RutaProducto

def sync_config():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Obtener ruta
    ruta = session.query(RutaProducto).filter_by(activo=True).first()
    if not ruta:
        print("❌ No hay ruta activa")
        return
    
    # Cargar config del archivo
    config_path = Path(__file__).parent.parent / 'rutas_producto' / 'PintucoBaseAgua_V1' / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        nueva_config = json.load(f)
    
    print("=" * 70)
    print("📋 Configuración actual en BD:")
    print(f"   Redes: {list(ruta.config.get('redes', {}).keys())}")
    
    # Actualizar
    ruta.config = nueva_config
    session.commit()
    
    print("\n✅ Configuración actualizada en BD")
    print(f"   Nuevas redes: {list(nueva_config['redes'].keys())}")
    
    # Verificar que existan los archivos
    print("\n🔍 Verificando archivos PNML:")
    for nombre, info in nueva_config['redes'].items():
        pnml_path = Path(ruta.base_path) / info['pnml']
        if pnml_path.exists():
            print(f"   ✅ {nombre} -> {pnml_path.name}")
        else:
            print(f"   ❌ {nombre} -> {pnml_path} NO EXISTE")
    
    session.close()

if __name__ == "__main__":
    sync_config()