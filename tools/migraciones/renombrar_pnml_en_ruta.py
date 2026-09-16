# scripts/renombrar_pnml_en_ruta.py
"""Renombra los archivos PNML en la estructura de la ruta a sus nombres originales"""

import os
from pathlib import Path

def renombrar_en_ruta():
    # Directorio donde están los PNML actuales
    ruta_redes = Path(__file__).parent.parent / 'rutas_producto' / 'PintucoBaseAgua_V1' / 'redes'
    
    if not ruta_redes.exists():
        print(f"❌ Directorio no encontrado: {ruta_redes}")
        return
    
    # Mapeo de nombres actuales a nombres originales
    renombres = {
        "integradora.pnml": "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml",
        "dispersion.pnml": "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml",
        "dilucion.pnml": "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2.pnml"
    }
    
    print("=" * 70)
    print("📝 Renombrando archivos PNML en la ruta del producto")
    print("=" * 70)
    print(f"📁 Directorio: {ruta_redes}\n")
    
    for old_name, new_name in renombres.items():
        old_path = ruta_redes / old_name
        new_path = ruta_redes / new_name
        
        if old_path.exists():
            os.rename(old_path, new_path)
            print(f"✅ {old_name} → {new_name}")
        else:
            print(f"⚠️ {old_name} no encontrado")
    
    print("\n" + "=" * 70)
    print("📁 Archivos finales en redes/:")
    print("=" * 70)
    for f in sorted(ruta_redes.glob("*.pnml")):
        print(f"   - {f.name}")
    
    print("\n" + "=" * 70)
    print("📝 Ahora actualiza el config.json con estos nombres:")
    print("=" * 70)
    print("""
{
  "redes": {
    "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4": {
      "pnml": "redes/Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml",
      "tipo": "padre"
    },
    "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1": {
      "pnml": "redes/Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml",
      "tipo": "hija"
    },
    "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2": {
      "pnml": "redes/Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2.pnml",
      "tipo": "hija"
    }
  }
}
    """)

if __name__ == "__main__":
    renombrar_en_ruta()