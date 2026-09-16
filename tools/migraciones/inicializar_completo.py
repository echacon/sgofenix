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

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FENIX_DIR = ROOT_DIR / "fenix"
TOOLS_DIR = ROOT_DIR / "tools"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FENIX_DIR))
sys.path.insert(0, str(TOOLS_DIR))

# 1. Inicializar BD y migrar redes
try:
    from tools.carga.init_db import init_database
    init_database()
except ImportError:
    pass