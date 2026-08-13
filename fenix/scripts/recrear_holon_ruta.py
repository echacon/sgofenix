# scripts/recrear_holon_ruta.py

#!/usr/bin/env python3
"""
Recrea la tabla holon_ruta sin las columnas viejas.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

def recrear_holon_ruta():
    db_path = Path(__file__).parent.parent / "fenix.db"
    engine = create_engine(f'sqlite:///{db_path}')
    
    with engine.connect() as conn:
        # 1. Verificar columnas actuales
        result = conn.execute(text("PRAGMA table_info(holon_ruta)"))
        columnas_actuales = [row[1] for row in result]
        print(f"📋 Columnas actuales: {columnas_actuales}")
        
        # 2. Crear nueva tabla con estructura correcta
        conn.execute(text("""
            CREATE TABLE holon_ruta_nueva (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                fecha_desde TEXT,
                fecha_hasta TEXT,
                condiciones JSON,
                activa BOOLEAN DEFAULT 1,
                producto_id INTEGER NOT NULL,
                patron_id INTEGER NOT NULL
            )
        """))
        
        # 3. Copiar datos (solo columnas que existen)
        columnas_comunes = ['id', 'nombre', 'descripcion', 'fecha_desde', 'fecha_hasta', 
                           'producto_id', 'patron_id']
        
        # Verificar si condiciones existe
        if 'condiciones' in columnas_actuales:
            columnas_comunes.append('condiciones')
        
        # Verificar si activa existe
        if 'activa' in columnas_actuales:
            columnas_comunes.append('activa')
        elif 'activo' in columnas_actuales:
            columnas_comunes.append('activo')
        
        columnas_select = ', '.join(columnas_comunes)
        conn.execute(text(f"""
            INSERT INTO holon_ruta_nueva ({columnas_select})
            SELECT {columnas_select} FROM holon_ruta
        """))
        
        # 4. Eliminar tabla vieja y renombrar nueva
        conn.execute(text("DROP TABLE holon_ruta"))
        conn.execute(text("ALTER TABLE holon_ruta_nueva RENAME TO holon_ruta"))
        
        conn.commit()
        
        # 5. Verificar resultado
        result = conn.execute(text("PRAGMA table_info(holon_ruta)"))
        nuevas_columnas = [row[1] for row in result]
        print(f"✅ Tabla holon_ruta recreada")
        print(f"   Nuevas columnas: {nuevas_columnas}")
        
        # 6. Mostrar datos existentes
        result = conn.execute(text("SELECT id, nombre, activa FROM holon_ruta"))
        filas = result.fetchall()
        if filas:
            print(f"\n📦 Datos en holon_ruta:")
            for row in filas:
                print(f"   ID: {row[0]}, Nombre: {row[1]}, Activa: {row[2]}")
        else:
            print("\n⚠️ No hay datos en holon_ruta")

if __name__ == "__main__":
    recrear_holon_ruta()