# scripts/diagnosticar_pnml.py
"""Diagnostica el formato del archivo PNML"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def diagnosticar():
    pnml_path = Path("rutas_producto/PintucoBaseAgua_V1/redes/integradora.pnml")
    
    if not pnml_path.exists():
        print(f"❌ No existe: {pnml_path}")
        return
    
    with open(pnml_path, 'r', encoding='utf-8') as f:
        primeras_lineas = f.readlines()[:5]
    
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DEL PNML")
    print("=" * 60)
    print(f"\nArchivo: {pnml_path}")
    print("\nPrimeras líneas:")
    for i, line in enumerate(primeras_lineas, 1):
        print(f"{i}: {line.rstrip()}")

if __name__ == "__main__":
    diagnosticar()