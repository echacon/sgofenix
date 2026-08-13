# scripts/fix_db_schema.py
"""Corrige el esquema de la base de datos agregando la columna faltante"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def fix_schema():
    engine = create_engine('sqlite:///fenix.db')
    
    with engine.connect() as conn:
        # Verificar si la columna existe
        result = conn.execute(text("PRAGMA table_info(patron_de_ruta)"))
        columnas = [row[1] for row in result]
        
        print("=" * 70)
        print("📋 Columnas en patron_de_ruta:")
        for col in columnas:
            print(f"   - {col}")
        
        if 'version' not in columnas:
            print("\n⚠️ Columna 'version' no encontrada. Agregando...")
            conn.execute(text("ALTER TABLE patron_de_ruta ADD COLUMN version VARCHAR(50) DEFAULT '1.0'"))
            conn.commit()
            print("✅ Columna 'version' agregada")
        else:
            print("\n✅ Columna 'version' ya existe")
        
        # También verificar config_cache en ruta_producto
        result = conn.execute(text("PRAGMA table_info(ruta_producto)"))
        columnas_ruta = [row[1] for row in result]
        
        print("\n📋 Columnas en ruta_producto:")
        for col in columnas_ruta:
            print(f"   - {col}")
        
        if 'config_cache' not in columnas_ruta:
            print("\n⚠️ Columna 'config_cache' no encontrada. Agregando...")
            conn.execute(text("ALTER TABLE ruta_producto ADD COLUMN config_cache TEXT"))
            conn.commit()
            print("✅ Columna 'config_cache' agregada")

if __name__ == "__main__":
    fix_schema()