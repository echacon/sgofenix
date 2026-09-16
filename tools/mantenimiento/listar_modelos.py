# scripts/listar_modelos.py
"""Lista todos los modelos definidos en la BD"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

def listar_modelos():
    engine = create_engine('sqlite:///fenix.db')
    inspector = inspect(engine)
    
    print("=" * 60)
    print("📊 TABLAS EN LA BASE DE DATOS")
    print("=" * 60)
    
    tablas = inspector.get_table_names()
    for tabla in sorted(tablas):
        print(f"   - {tabla}")
    
    print(f"\n✅ Total: {len(tablas)} tablas")

if __name__ == "__main__":
    listar_modelos()