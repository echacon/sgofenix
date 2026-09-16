#!/usr/bin/env python3
# scripts/cargar_recursos.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import yaml
import logging
from modelos.declarative_base import SessionLocal
from modelos.Recursos import Recurso, RecursoEquipo, RecursoPersonal, UnidadFuncional, UnidadNegocio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_recursos(session, data):
    for r in data.get('recursos', []):
        codigo = r['codigo']
        nombre = r['nombre']
        tipo = r['tipo']
        descripcion = r.get('descripcion', '')
        
        existing = session.query(Recurso).filter_by(codigo=codigo).first()
        if existing:
            logger.info(f"Recurso {codigo} ya existe, omitiendo")
            continue
        
        recurso = Recurso(codigo=codigo, nombre=nombre, tipo=tipo, descripcion=descripcion)
        session.add(recurso)
        session.flush()  # para obtener el id
        
        # Datos específicos según tipo
        if tipo == 'equipo':
            # Buscar unidad funcional por nombre (cadena como "Producción/Pinturas base agua")
            unidad_codigo = r.get('unidad_codigo') or r.get('unidad_cod')  # opción flexible
            if not unidad_codigo:
                # Si no viene código, intentamos mapear desde el nombre (compatibilidad)
                unidad_codigo = {
                    "Producción/Pinturas base agua": "AGUA_001",
                    "Producción": "PROD_001"
                }.get(r.get('unidad'))
            unidad = None
            if unidad_codigo:
                unidad = session.query(UnidadFuncional).filter_by(codigo=unidad_codigo).first()
                if not unidad:
                    logger.warning(f"Unidad funcional con código '{unidad_codigo}' no encontrada")
            else:
                logger.warning(f"No se pudo determinar código de unidad para recurso {codigo}")
            params = r.get('parametros', {})
            equipo = RecursoEquipo(
                id=recurso.id,
                modelo=r.get('modelo', ''),
                unidad_id=unidad.id if unidad else None,
                capacidad_maxima=params.get('capacidad_maxima_litros'),
                velocidad_procesamiento=params.get('velocidad_procesamiento'),
                consumo_energia_kw=params.get('consumo_energia_kw', 0),
                costo_depreciacion_hora=params.get('costo_hora', 0),
                disponible=True
            )
            session.add(equipo)
            logger.info(f"  Equipo {codigo} cargado")
        
        elif tipo == 'personal':
            params = r.get('parametros', {})
            personal = RecursoPersonal(
                id=recurso.id,
                costo_por_hora=params.get('costo_hora', 0),
                especialidad=params.get('especialidad'),
                disponible=True
            )
            session.add(personal)
            logger.info(f"  Personal {codigo} cargado")
    
    session.commit()

if __name__ == "__main__":
    session = SessionLocal()
    try:
        path_recursos = Path(__file__).parent.parent / "ontologia" / "empresa" / "04_recursos.yaml"
        if not path_recursos.exists():
            logger.error(f"No se encuentra {path_recursos}")
            sys.exit(1)
        data = load_yaml(path_recursos)
        cargar_recursos(session, data)
        logger.info("✅ Recursos cargados exitosamente")
    except Exception as e:
        session.rollback()
        logger.exception(f"Error: {e}")
    finally:
        session.close()