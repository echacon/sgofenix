# scripts/renombrar_pnml_a_nombres_originales.py
"""Renombra los archivos PNML a sus nombres originales"""

import os
from pathlib import Path

def renombrar_archivos():
    base_dir = Path(__file__).parent.parent / 'static' / 'archivospnml'
    
    # Mapeo de nombres actuales a nombres deseados
    renombres = {
        "integradora.pnml": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml",
        "dispersion.pnml": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml",
        "dilucion.pnml": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2.pnml"
    }
    
    print("=" * 60)
    print("📝 Renombrando archivos PNML")
    print("=" * 60)
    
    for old_name, new_name in renombres.items():
        old_path = base_dir / old_name
        new_path = base_dir / new_name
        
        if old_path.exists():
            os.rename(old_path, new_path)
            print(f"✅ {old_name} → {new_name}")
        else:
            print(f"⚠️ {old_name} no encontrado")
    
    print("\n✅ Archivos renombrados correctamente")
    
    # Listar archivos finales
    print("\n📁 Archivos en static/archivospnml:")
    for f in base_dir.glob("*.pnml"):
        print(f"   - {f.name}")

if __name__ == "__main__":
    renombrar_archivos()