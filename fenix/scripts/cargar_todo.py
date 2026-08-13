#!/usr/bin/env python3
"""
Script maestro para cargar toda la ontología, recursos, redes y productos en el orden correcto.
Ejecutar: python scripts/cargar_todo.py [--clean] [--confirm]
"""

import sys
import argparse
from pathlib import Path
import logging
from sqlalchemy import text

# Añadir raíz del proyecto
RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from modelos.declarative_base import SessionLocal, engine, Base

# Importar funciones de carga (ajusta según los nombres reales de tus scripts)
from scripts.cargar_ontologia_completo import (
    cargar_unidades_funcionales,
    cargar_tipos_operacion,
    cargar_patrones,
    cargar_conexiones_fisicas
)
from scripts.cargar_recursos import cargar_recursos
from scripts.cargar_rutas_y_encadenamiento import procesar_todas_rutas
from scripts.cargar_productos import cargar_productos
from scripts.cargar_asignaciones import cargar_asignaciones_global

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def limpiar_tablas(session, confirm=False):
    if not confirm:
        logger.warning("Limpieza omitida (use --confirm para borrar datos existentes)")
        return
    logger.warning("Eliminando datos existentes...")
    # Orden inverso por FK
    session.execute(text("DELETE FROM cola_evento"))
    session.execute(text("DELETE FROM evento_red"))
    session.execute(text("DELETE FROM instancia_red"))
    session.execute(text("DELETE FROM mensaje_pendiente"))
    session.execute(text("DELETE FROM orden_produccion"))
    session.execute(text("DELETE FROM asignacion_recurso"))
    session.execute(text("DELETE FROM formula"))
    session.execute(text("DELETE FROM insumo_formula"))
    session.execute(text("DELETE FROM holon_ruta"))
    session.execute(text("DELETE FROM producto"))
    session.execute(text("DELETE FROM red_petri"))
    session.execute(text("DELETE FROM configuracion_encadenamiento"))
    session.execute(text("DELETE FROM recurso_equipo"))
    session.execute(text("DELETE FROM recurso_personal"))
    session.execute(text("DELETE FROM recurso"))
    session.execute(text("DELETE FROM unidad_funcional"))
    session.execute(text("DELETE FROM unidad_negocio"))
    session.execute(text("DELETE FROM patron_de_ruta"))
    session.execute(text("DELETE FROM etapa_ruta"))
    session.execute(text("DELETE FROM transicion_patron"))
    session.execute(text("DELETE FROM tp_arc_ent"))
    session.execute(text("DELETE FROM tp_arc_sal"))
    session.execute(text("DELETE FROM tipo_de_operacion"))
    session.execute(text("DELETE FROM familia_producto"))
    session.execute(text("DELETE FROM conexion_fisica"))
    session.commit()
    logger.info("✅ Datos eliminados correctamente")

def cargar_archivo_yaml(session, path, func):
    """Helper para cargar un YAML si existe"""
    if path.exists():
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        func(session, data)
        logger.info(f"✓ Cargado: {path.name}")
    else:
        logger.warning(f"No se encuentra {path}, omitiendo")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clean', action='store_true', help='Limpia todas las tablas antes de cargar')
    parser.add_argument('--confirm', action='store_true', help='Confirma la limpieza (necesario con --clean)')
    args = parser.parse_args()

    session = SessionLocal()
    try:
        if args.clean:
            limpiar_tablas(session, confirm=args.confirm)
            if not args.confirm:
                return

        # 1. Cargar ontología base (familias, tipos, patrones, unidades, conexiones)
        base_dir = RAIZ / "ontologia" / "empresa"
        cargar_archivo_yaml(session, base_dir / "00_empresa.yaml", cargar_unidades_funcionales)
        cargar_archivo_yaml(session, base_dir / "02_tipos_operacion.yaml", cargar_tipos_operacion)
        cargar_archivo_yaml(session, base_dir / "03_patrones.yaml", cargar_patrones)
        cargar_archivo_yaml(session, base_dir / "04_recursos.yaml", cargar_recursos)
        cargar_archivo_yaml(session, base_dir / "07_conectividad.yaml", cargar_conexiones_fisicas)

        # 2. Cargar rutas (redes, encadenamiento) desde ontologia/rutas/
        logger.info("Cargando redes Petri y encadenamiento...")
        procesar_todas_rutas(session)   # función que recorre directorios

        # 3. Cargar productos
        cargar_archivo_yaml(session, base_dir / "06_productos.yaml", cargar_productos)

        # 4. Cargar asignaciones de recursos por etapa
        logger.info("Cargando asignaciones de recursos...")
        cargar_asignaciones_global(session)   # función que recorre directorios buscando asignaciones_recursos.yaml

        logger.info("✅ CARGA COMPLETA EXITOSA")
    except Exception as e:
        session.rollback()
        logger.exception(f"Error durante la carga: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()