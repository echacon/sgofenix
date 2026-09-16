# scripts/update_ruta_config.py
"""Actualiza la configuración de la ruta en la base de datos"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RutaProducto import RutaProducto

def update_config():
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Obtener ruta
    ruta = session.query(RutaProducto).filter_by(activo=True).first()
    if not ruta:
        print("❌ No hay ruta activa")
        return
    
    print("=" * 70)
    print(f"📋 Ruta: {ruta.nombre}")
    print(f"   Base path: {ruta.base_path}")
    
    # Cargar configuración del archivo
    config_path = Path(ruta.base_path) / 'config.json'
    
    if not config_path.exists():
        print(f"❌ Archivo config.json no encontrado en {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"\n📋 Configuración cargada del archivo:")
    print(f"   Redes: {list(config.get('redes', {}).keys())}")
    
    # Guardar en config_cache
    ruta.config_cache = config
    session.commit()
    
    print("\n✅ Configuración guardada en config_cache")
    
    # Verificar
    print("\n🔍 Verificación:")
    print(f"   config_cache tipo: {type(ruta.config_cache)}")
    if ruta.config_cache:
        print(f"   Redes en cache: {list(ruta.config_cache.get('redes', {}).keys())}")
    
    session.close()

if __name__ == "__main__":
    update_config()
    