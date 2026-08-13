# scripts/agregar_version_ruta_id.py

#!/usr/bin/env python3
"""
Agrega la columna version_ruta_id a la tabla orden_produccion.
Ejecutar después de migrar las tablas de versionamiento.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

def agregar_columna():
    """Agrega la columna version_ruta_id a orden_produccion"""
    
    db_path = Path(__file__).parent.parent / "fenix.db"
    engine = create_engine(f'sqlite:///{db_path}')
    
    with engine.connect() as conn:
        # Verificar si la columna ya existe
        result = conn.execute(text("PRAGMA table_info(orden_produccion)"))
        columnas = [row[1] for row in result]
        
        if 'version_ruta_id' in columnas:
            print("✅ La columna version_ruta_id ya existe")
            return
        
        # Agregar la columna
        print("🔄 Agregando columna version_ruta_id a orden_produccion...")
        conn.execute(text(
            "ALTER TABLE orden_produccion ADD COLUMN version_ruta_id INTEGER REFERENCES version_ruta(id)"
        ))
        conn.commit()
        
        print("✅ Columna version_ruta_id agregada exitosamente")

if __name__ == "__main__":
    agregar_columna()