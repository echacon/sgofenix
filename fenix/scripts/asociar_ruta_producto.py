# scripts/asociar_ruta_producto.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from modelos.declarative_base import SessionLocal
from modelos.Producto import Producto, HolonRuta

db = SessionLocal()
producto = db.query(Producto).filter_by(codigo="TPL_LATEX").first()
if not producto:
    print("Producto TPL_LATEX no encontrado")
    sys.exit(1)

holon = db.query(HolonRuta).filter_by(nombre="BASEAGUA_DIS_DIL").first()
if not holon:
    print("HolonRuta BASEAGUA_DIS_DIL no encontrada")
    sys.exit(1)

holon.producto_id = producto.id
db.commit()
print(f"✅ Ruta '{holon.nombre}' asociada al producto '{producto.codigo}'")
db.close()