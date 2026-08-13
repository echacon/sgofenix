# scripts/verificar_archivos_redes.py
"""Verifica qué archivos existen en el directorio de redes"""

from pathlib import Path

ruta_redes = Path(__file__).parent.parent / 'rutas_producto' / 'PintucoBaseAgua_V1' / 'redes'

print("=" * 70)
print(f"📁 Directorio: {ruta_redes}")
print(f"¿Existe? {ruta_redes.exists()}")
print("=" * 70)

if ruta_redes.exists():
    archivos = list(ruta_redes.glob("*.pnml"))
    
    if archivos:
        print("\n📄 Archivos PNML encontrados:")
        for archivo in archivos:
            print(f"   - {archivo.name}")
    else:
        print("\n❌ No se encontraron archivos .pnml")
        
    # También verificar en static/archivospnml
    static_redes = Path(__file__).parent.parent / 'static' / 'archivospnml'
    print(f"\n📁 Directorio alternativo: {static_redes}")
    if static_redes.exists():
        archivos_static = list(static_redes.glob("*.pnml"))
        if archivos_static:
            print("   Archivos encontrados:")
            for archivo in archivos_static:
                print(f"      - {archivo.name}")
        else:
            print("   No hay archivos .pnml")
else:
    print("❌ El directorio no existe")

print("\n" + "=" * 70)
print("💡 Sugerencia:")
print("   Los archivos deben estar en rutas_producto/PintucoBaseAgua_V1/redes/")
print("   Y deben tener los nombres que coinciden con el config.json")