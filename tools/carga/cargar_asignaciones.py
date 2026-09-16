#!/usr/bin/env python3
# scripts/cargar_asignaciones.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import yaml
import logging
from modelos.declarative_base import SessionLocal
from modelos.Producto import HolonRuta, AsignacionRecurso
from modelos.Taxonomia import EtapaRuta, PatronDeRuta
from modelos.Recursos import Recurso

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_asignaciones(session, ruta_nombre, asignaciones_data):
    # Buscar la HolonRuta por nombre
    holon = session.query(HolonRuta).filter_by(nombre=ruta_nombre).first()
    if not holon:
        logger.error(f"HolonRuta '{ruta_nombre}' no encontrada")
        return
    
    patron = holon.patron
    if not patron:
        logger.error(f"La ruta '{ruta_nombre}' no tiene patrón asociado")
        return
    
    for asig in asignaciones_data.get('etapas', []):
        etapa_codigo = asig.get('codigo')
        if not etapa_codigo:
            continue
        etapa = session.query(EtapaRuta).filter_by(patronRuta_id=patron.id, nombre=etapa_codigo).first()
        if not etapa:
            logger.warning(f"Etapa '{etapa_codigo}' no existe en patrón '{patron.nombre}'")
            continue
        
        recurso_codigo = asig.get('recurso_codigo')
        recurso = None
        if recurso_codigo:
            recurso = session.query(Recurso).filter_by(codigo=recurso_codigo).first()
            if not recurso:
                logger.warning(f"Recurso '{recurso_codigo}' no encontrado")
        
        # Operador (opcional)
        operador_codigo = asig.get('operador_codigo')
        operador = None
        if operador_codigo:
            operador = session.query(Recurso).filter_by(codigo=operador_codigo).first()
            if not operador:
                logger.warning(f"Operador '{operador_codigo}' no encontrado")
        
        # Buscar si ya existe asignación para esta etapa en esta ruta
        asignacion = session.query(AsignacionRecurso).filter_by(
            holon_ruta_id=holon.id, etapa_ruta_id=etapa.id
        ).first()
        if not asignacion:
            asignacion = AsignacionRecurso(
                holon_ruta_id=holon.id,
                etapa_ruta_id=etapa.id,
                recurso_id=recurso.id if recurso else None,
                duracion_estimada_min=asig.get('duracion_estimada_min', 0),
                costo_por_hora_real=asig.get('costo_por_hora', 0),
                eficiencia_real=asig.get('eficiencia', 1.0),
                capacidad_maxima_lote=asig.get('capacidad_maxima_litros')
            )
            session.add(asignacion)
            logger.info(f"  Asignación creada: etapa {etapa_codigo} -> recurso {recurso_codigo}")
        else:
            asignacion.recurso_id = recurso.id if recurso else None
            asignacion.duracion_estimada_min = asig.get('duracion_estimada_min', 0)
            asignacion.costo_por_hora_real = asig.get('costo_por_hora', 0)
            asignacion.eficiencia_real = asig.get('eficiencia', 1.0)
            asignacion.capacidad_maxima_lote = asig.get('capacidad_maxima_litros')
            session.commit()
            logger.info(f"  Asignación actualizada: etapa {etapa_codigo}")
    
    session.commit()

def cargar_asignaciones_global(session):
    rutas_base = Path(__file__).parent.parent / "ontologia" / "rutas"
    if not rutas_base.exists():
        logger.error(f"No existe {rutas_base}")
        return
    
    for ruta_dir in rutas_base.iterdir():
        if not ruta_dir.is_dir():
            continue
        asignaciones_path = ruta_dir / "asignaciones_recursos.yaml"
        if not asignaciones_path.exists():
            logger.info(f"{ruta_dir.name}: no tiene asignaciones_recursos.yaml, omitiendo")
            continue
        data = load_yaml(asignaciones_path)
        cargar_asignaciones(session, ruta_dir.name, data)
    logger.info("✅ Carga de asignaciones completada")

def main():
    session = SessionLocal()
    try:
        rutas_base = Path(__file__).parent.parent / "ontologia" / "rutas"
        if not rutas_base.exists():
            logger.error(f"No existe {rutas_base}")
            return
        
        for ruta_dir in rutas_base.iterdir():
            if not ruta_dir.is_dir():
                continue
            asignaciones_path = ruta_dir / "asignaciones_recursos.yaml"
            if not asignaciones_path.exists():
                logger.info(f"{ruta_dir.name}: no tiene asignaciones_recursos.yaml, omitiendo")
                continue
            data = load_yaml(asignaciones_path)
            cargar_asignaciones(session, ruta_dir.name, data)
        logger.info("✅ Carga de asignaciones completada")
    except Exception as e:
        session.rollback()
        logger.exception(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()