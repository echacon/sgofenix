# scripts/verificar_modelo_ruta.py
"""Verifica la estructura del modelo RutaProducto"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RutaProducto import RutaProducto

engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)
session = Session()

ruta = session.query(RutaProducto).filter_by(activo=True).first()

if ruta:
    print("=" * 70)
    print("📋 Estructura de RutaProducto")
    print("=" * 70)
    print(f"ID: {ruta.id}")
    print(f"Nombre: {ruta.nombre}")
    print(f"Versión: {ruta.version}")
    print(f"Base path: {ruta.base_path}")
    print(f"Activo: {ruta.activo}")
    
    # Ver qué atributos tiene
    print("\n📋 Atributos disponibles:")
    for attr in dir(ruta):
        if not attr.startswith('_') and not callable(getattr(ruta, attr)):
            try:
                value = getattr(ruta, attr)
                if attr in ['config', 'configuracion', 'config_data', 'config_json']:
                    print(f"   - {attr}: {type(value)} = {str(value)[:100]}")
                elif not hasattr(value, '__call__'):
                    print(f"   - {attr}: {type(value).__name__}")
            except:
                pass
    
    # Si no hay atributo config, ver cómo se guarda la configuración
    if hasattr(ruta, 'configuracion'):
        print(f"\n📋 Configuración: {ruta.configuracion}")
    elif hasattr(ruta, 'config_data'):
        print(f"\n📋 Configuración: {ruta.config_data}")
    else:
        print("\n⚠️ No se encontró atributo 'config' en el modelo")
        print("   La configuración podría estar en otro campo o ser manejada de otra forma")

session.close()