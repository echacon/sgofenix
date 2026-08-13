# test_import_metadatos.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.RedPetri import RedPetri

engine = create_engine('sqlite:///fenix.db')
session = sessionmaker(bind=engine)()

expected = {
    "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1": {"exito": ["p8"], "fallo": ["p4"]},
    "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2": {"exito": ["p24"], "fallo": ["p22"]},
    "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4": {"exito": ["p6"], "fallo": ["p11"]},
}

ok = True
for nombre, esperado in expected.items():
    red = session.query(RedPetri).filter_by(nombre=nombre).first()
    if not red:
        print(f"❌ Red no encontrada: {nombre}")
        ok = False
        continue
    metadatos = red.metadatos or {}
    estados = metadatos.get('estados_finales', {})
    if estados.get('exito') != esperado.get('exito') or estados.get('fallo') != esperado.get('fallo'):
        print(f"❌ {nombre}: esperado {esperado}, obtenido {estados}")
        ok = False
    else:
        print(f"✅ {nombre}: correcto")

if ok:
    print("\n✅ Todos los metadatos están correctos")
else:
    print("\n⚠️ Hay errores en los metadatos. Revisa el importador.")
session.close()