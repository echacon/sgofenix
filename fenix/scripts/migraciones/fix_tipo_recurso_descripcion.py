# scripts/fix_tipo_recurso_descripcion.py

from sqlalchemy import create_engine, text
from modelos.declarative_base import Base

engine = create_engine('sqlite:///fenix.db', echo=True)

with engine.connect() as conn:
    # Verificar si la columna permite NULL
    conn.execute(text("ALTER TABLE tipo_recurso ADD COLUMN descripcion_temp VARCHAR(256)"))
    conn.execute(text("UPDATE tipo_recurso SET descripcion_temp = descripcion"))
    conn.execute(text("ALTER TABLE tipo_recurso DROP COLUMN descripcion"))
    conn.execute(text("ALTER TABLE tipo_recurso RENAME COLUMN descripcion_temp TO descripcion"))
    conn.commit()
    print("✅ Columna descripcion modificada a nullable")