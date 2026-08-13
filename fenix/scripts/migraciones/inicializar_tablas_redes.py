#!/usr/bin/env python3
"""Inicializa las tablas red_petri y suscripcion_evento"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.RedPetri import RedPetri
from modelos.SuscripcionEvento import SuscripcionEvento

def inicializar_tablas():
    engine = create_engine('sqlite:///fenix.db')
    
    # Crear todas las tablas que faltan
    print("📦 Creando tablas faltantes...")
    Base.metadata.create_all(engine)
    
    # Verificar tablas creadas
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    
    print("\n✅ Tablas existentes:")
    for tabla in sorted(tablas):
        print(f"   - {tabla}")
    
    # Verificar específicamente las que nos interesan
    if 'red_petri' in tablas:
        print("\n✅ Tabla 'red_petri' creada exitosamente")
    else:
        print("\n❌ Error: 'red_petri' no fue creada")
    
    if 'suscripcion_evento' in tablas:
        print("✅ Tabla 'suscripcion_evento' creada exitosamente")
    else:
        print("❌ Error: 'suscripcion_evento' no fue creada")

if __name__ == "__main__":
    inicializar_tablas()