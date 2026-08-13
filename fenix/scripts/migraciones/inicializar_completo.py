# scripts/inicializar_completo.py
"""
Inicialización completa del sistema:
- Crea tablas
- Crea usuarios
- Migra redes PNML
- Prueba el motor
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# 1. Inicializar BD y migrar redes
from scripts.init_db import init_database
init_database()

# 2. Probar persistencia
print("\n" + "="*60)
print("🧪 PROBANDO PERSISTENCIA DEL MOTOR")
print("="*60)
from scripts.probar_persistencia import main as test_main
test_main()