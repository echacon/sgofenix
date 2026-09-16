# scripts/verificar_config.py
"""Verifica y muestra el contenido del config.json"""

from pathlib import Path

ruta_config = Path(__file__).parent.parent / 'rutas_producto' / 'PintucoBaseAgua_V1' / 'config.json'

print("=" * 70)
print("📄 Leyendo config.json")
print("=" * 70)
print(f"Ruta: {ruta_config}")
print(f"¿Existe? {ruta_config.exists()}\n")

if ruta_config.exists():
    with open(ruta_config, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    print("Contenido actual:")
    print("-" * 70)
    print(contenido)
    print("-" * 70)
    
    # Intentar identificar el error
    print("\n🔍 Buscando posibles errores:")
    lineas = contenido.split('\n')
    for i, linea in enumerate(lineas, 1):
        if i >= 33 and i <= 36:  # Mostrar líneas alrededor del error
            print(f"   Línea {i}: {repr(linea)}")