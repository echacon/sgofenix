# scripts/inicializar_ruta_producto.py
"""Script completo para inicializar y probar RutaProducto"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.Producto import Producto
from modelos.RutaProducto import RutaProducto
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.RedPetri import RedPetri

def inicializar():
    """Inicializa todo el entorno de RutaProducto"""
    
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=" * 60)
    print("INICIALIZACIÓN DE RUTA PRODUCTO")
    print("=" * 60)
    
    # 1. Verificar/crear producto
    producto = session.query(Producto).first()
    if not producto:
        print("\n📦 Creando producto de ejemplo...")
        producto = Producto(
            nombre="Pintuco Base Agua",
            descripcion="Pintura base agua para interiores",
            familia_id=1,
            activo=True
        )
        session.add(producto)
        session.commit()
        print(f"   ✅ Producto creado: ID={producto.id}")
    else:
        print(f"\n📦 Producto existente: {producto.nombre} (ID={producto.id})")
    
    # 2. Verificar/crear redes Petri
    redes_necesarias = [
        "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
        "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
        "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2"
    ]
    
    print("\n🔧 Verificando redes Petri...")
    for red_nombre in redes_necesarias:
        red = session.query(RedPetri).filter_by(nombre=red_nombre, activo=True).first()
        if red:
            print(f"   ✅ Red encontrada: {red_nombre} (ID={red.id})")
        else:
            print(f"   ⚠️ Red no encontrada: {red_nombre}")
    
    # 3. Crear directorios de ruta
    base_path = Path("rutas_producto/PintucoBaseAgua_V1")
    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "redes").mkdir(exist_ok=True)
    (base_path / "recursos").mkdir(exist_ok=True)
    (base_path / "encadenamiento").mkdir(exist_ok=True)
    (base_path / "metadatos").mkdir(exist_ok=True)
    
    # 4. Crear config.json
    config_path = base_path / "config.json"
    config = {
        "id": "ruta_pintuco_base_agua_v1",
        "nombre": "Pintuco Base Agua",
        "version": "1.0.0",
        "producto_id": producto.id,
        "patron_ruta_id": None,
        "redes": {
            "integradora": {
                "pnml": "redes/integradora.pnml",
                "recursos": "recursos/integradora_recursos.json",
                "tipo": "padre",
                "marcado_inicial": {},
                "recursos_iniciales": {}
            },
            "dispersion": {
                "pnml": "redes/dispersion.pnml",
                "recursos": "recursos/dispersion_recursos.json",
                "tipo": "hija",
                "marcado_inicial": {},
                "recursos_iniciales": {}
            },
            "dilucion": {
                "pnml": "redes/dilucion.pnml",
                "recursos": "recursos/dilucion_recursos.json",
                "tipo": "hija",
                "marcado_inicial": {},
                "recursos_iniciales": {}
            }
        },
        "encadenamiento": "encadenamiento/reglas.json",
        "estados_finales": {
            "integradora": ["p_terminado"],
            "dispersion": ["p_fin_dispersion"],
            "dilucion": ["p_fin_dilucion"]
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Config creado: {config_path}")
    
    # 5. Crear registro en BD
    ruta = session.query(RutaProducto).filter_by(nombre=config["nombre"]).first()
    if not ruta:
        ruta = RutaProducto(
            nombre=config["nombre"],
            version=config["version"],
            descripcion="Ruta de producción para Pintuco Base Agua",
            config_path=str(config_path),
            base_path=str(base_path),
            producto_id=producto.id,
            patron_ruta_id=None,
            activo=True,
            config_cache=config
        )
        session.add(ruta)
        session.commit()
        print(f"\n✅ Ruta creada: ID={ruta.id}")
    else:
        # Actualizar cache
        ruta.config_cache = config
        ruta.config_path = str(config_path)
        session.commit()
        print(f"\n✅ Ruta actualizada: ID={ruta.id}")
    
    # 6. Mostrar resumen
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"Producto: {producto.nombre} (ID={producto.id})")
    print(f"Ruta: {ruta.nombre} v{ruta.version} (ID={ruta.id})")
    print(f"Config path: {ruta.config_path}")
    print(f"Base path: {ruta.base_path}")
    
    session.close()
    
    return ruta.id


if __name__ == "__main__":
    ruta_id = inicializar()
    print(f"\n🎯 Listo para crear órdenes con: ruta_id={ruta_id}")
    print("\nEjecuta ahora:")
    print("  python scripts/test_ruta_producto.py")