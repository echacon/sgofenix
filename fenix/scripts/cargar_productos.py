#!/usr/bin/env python3
# scripts/cargar_productos.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import logging
from modelos.declarative_base import SessionLocal
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta
from modelos.Producto import Producto, HolonRuta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_productos(session, data):
    for prod_data in data.get('productos', []):
        codigo = prod_data['codigo']
        nombre = prod_data['nombre']
        familia_nombre = prod_data.get('familia')
        patron_nombre = prod_data.get('patron')
        
        # Buscar familia
        familia = None
        if familia_nombre:
            familia = session.query(FamiliaProducto).filter_by(nombre=familia_nombre).first()
            if not familia:
                logger.warning(f"Familia '{familia_nombre}' no existe, se creará automáticamente")
                familia = FamiliaProducto(nombre=familia_nombre, descripcion=f"Familia {familia_nombre}")
                session.add(familia)
                session.flush()
        
        # Buscar patrón (debe existir previamente)
        patron = None
        if patron_nombre:
            patron = session.query(PatronDeRuta).filter_by(nombre=patron_nombre).first()
            if not patron:
                logger.error(f"Patrón '{patron_nombre}' no encontrado. Ejecuta primero la carga de patrones.")
                continue
        
        # Crear o actualizar producto
        producto = session.query(Producto).filter_by(codigo=codigo).first()
        if not producto:
            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=prod_data.get('descripcion', ''),
                es_fabricado=prod_data.get('es_fabricado', True),
                es_adquirido=prod_data.get('es_adquirido', False),
                es_final=prod_data.get('es_final', True),
                es_insumo=prod_data.get('es_insumo', False),
                es_intermedio=prod_data.get('es_intermedio', False),
                familia_id=familia.id if familia else None
            )
            session.add(producto)
            session.flush()
            logger.info(f"Producto '{codigo}' creado")
            if producto.familia_id:
                # Buscar holones de la misma familia que aún no tienen producto asignado
                holones = session.query(HolonRuta).filter_by(
                    familia_id=producto.familia_id,
                    producto_id=None
                ).all()
                for holon in holones:
                    holon.producto_id = producto.id
                    logger.info(f"  Ruta '{holon.nombre}' vinculada a producto {producto.codigo} (por familia)")
                session.commit()
        else:
            producto.nombre = nombre
            producto.descripcion = prod_data.get('descripcion', '')
            producto.familia_id = familia.id if familia else None
            # actualizar otros flags si es necesario
            session.commit()
            logger.info(f"Producto '{codigo}' actualizado")
        
        # Procesar rutas concretas (HolonRuta)
        for ruta_data in prod_data.get('rutas', []):
            ruta_nombre = ruta_data.get('nombre')
            if not ruta_nombre:
                logger.warning(f"Producto {codigo}: ruta sin nombre, omitida")
                continue
            
            # Buscar si ya existe un HolonRuta con ese nombre (y opcionalmente asociado a este producto)
            holon = session.query(HolonRuta).filter_by(nombre=ruta_nombre).first()
            if not holon:
                holon = HolonRuta(
                    nombre=ruta_nombre,
                    descripcion=ruta_data.get('descripcion', ''),
                    producto_id=producto.id,
                    patron_id=patron.id if patron else None,
                    familia_id=familia.id if familia else None,
                    activa=ruta_data.get('activa', True),
                    condiciones=ruta_data.get('condiciones', {})
                )
                session.add(holon)
                logger.info(f"  HolonRuta '{ruta_nombre}' creada para producto {codigo}")
            else:
                # Actualizar si es necesario (por ejemplo, cambiar condiciones)
                holon.producto_id = producto.id
                holon.patron_id = patron.id if patron else holon.patron_id
                holon.familia_id = familia.id if familia else holon.familia_id
                holon.activa = ruta_data.get('activa', True)
                holon.condiciones = ruta_data.get('condiciones', {})
                session.commit()
                logger.info(f"  HolonRuta '{ruta_nombre}' actualizada")
            
            # Nota: Las asignaciones de recursos (duración, recurso específico) que aparecen en
            # el YAML bajo 'asignaciones' deben cargarse en la tabla `AsignacionRecurso`.
            # Si tu YAML las incluye, necesitarás procesarlas aquí.
            # Por ahora, asumimos que las asignaciones ya se cargaron con las rutas desde
            # el script de rutas (cargar_rutas_y_encadenamiento.py) o que se agregarán después.
            # Si quieres, puedo ampliar esta función para manejar asignaciones.

    session.commit()
    logger.info("✅ Productos cargados exitosamente")

def main():
    session = SessionLocal()
    try:
        path = Path(__file__).parent.parent / "ontologia" / "empresa" / "06_productos.yaml"
        if not path.exists():
            logger.error(f"No se encuentra {path}")
            return
        data = load_yaml(path)
        cargar_productos(session, data)
    except Exception as e:
        session.rollback()
        logger.exception(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()