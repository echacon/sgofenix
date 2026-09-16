#!/usr/bin/env python3
# scripts/cargar_rutas_y_encadenamiento.py
"""
Carga dinámica de rutas, redes Petri y encadenamiento.
Recorre ontologia/rutas/ y procesa cada subcarpeta.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import yaml
import xml.etree.ElementTree as ET
import logging
from modelos.declarative_base import SessionLocal
from modelos.Taxonomia import PatronDeRuta, FamiliaProducto, EtapaRuta
from modelos.RedPetri import RedPetri
from modelos.Producto import HolonRuta
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from utils.parser_pnml import cargar_red_desde_pnml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_pnml(file_path):
    """Extrae lugares, transiciones y arcos de un archivo PNML."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'pnml': 'http://www.pnml.org/version-2009/grammar/pnml'}
    places = {}
    transitions = {}
    arcs = []
    for page in root.findall('.//pnml:page', ns):
        for place in page.findall('pnml:place', ns):
            pid = place.get('id')
            name_elem = place.find('pnml:name/pnml:text', ns)
            name = name_elem.text if name_elem is not None else pid
            places[pid] = {'id': pid, 'name': name}
        for trans in page.findall('pnml:transition', ns):
            tid = trans.get('id')
            name_elem = trans.find('pnml:name/pnml:text', ns)
            name = name_elem.text if name_elem is not None else tid
            transitions[tid] = {'id': tid, 'name': name}
        for arc in page.findall('pnml:arc', ns):
            arcs.append({'source': arc.get('source'), 'target': arc.get('target')})
    return {'places': places, 'transitions': transitions, 'arcs': arcs}

def cargar_o_actualizar_red(session, nombre_red, pnml_path, patron_id=None):
    existing = session.query(RedPetri).filter_by(nombre=nombre_red).first()
    if existing:
        red = existing
        logger.info(f"    Actualizando red '{nombre_red}'")
    else:
        red = RedPetri(nombre=nombre_red, descripcion=f"Red {nombre_red}")
        session.add(red)
    
    # Usar el parser existente
    petri_net = cargar_red_desde_pnml(str(pnml_path))
    if not petri_net:
        logger.error(f"    No se pudo parsear {pnml_path}")
        return None
    
    # Convertir a formato JSON para la BD
    lugares_json = {pid: {'id': p.id, 'name': p.nombre, 'marking_inicial': p.marking_inicial} 
                    for pid, p in petri_net.places.items()}
    transiciones_json = {tid: {'id': t.id, 'name': t.nombre, 'trigger': t.trigger} 
                         for tid, t in petri_net.transitions.items()}
    arcos_json = [{'source': a.source, 'target': a.target, 'peso': a.peso} 
                  for a in petri_net.arcs.values()]
    
    red.lugares = lugares_json
    red.transiciones = transiciones_json
    
    #arcos_dict = {}
    if isinstance(petri_net.arcs, dict):
        arcos_dict = {aid: {'source': a.source, 'target': a.target, 'peso': a.peso}
                    for aid, a in petri_net.arcs.items()}
    else:  # es una lista
        arcos_dict = {f"arc_{i}": {'source': a.source, 'target': a.target, 'peso': a.peso}
                    for i, a in enumerate(petri_net.arcs)}
    red.arcos = arcos_dict


    red.archivo_pnml_origen = str(pnml_path)
    red.activo = True
    if patron_id:
        red.patron_ruta_id = patron_id
    session.commit()
    logger.info(f"      {len(lugares_json)} lugares, {len(transiciones_json)} transiciones")
    return red

def procesar_ruta(session, ruta_path):
    """Procesa una carpeta de ruta (con metadatos.yaml, opcional encadenamiento.yaml)."""
    meta_path = ruta_path / "metadatos.yaml"
    if not meta_path.exists():
        logger.warning(f"  {ruta_path.name}: falta metadatos.yaml, omitiendo")
        return
    meta = load_yaml(meta_path)
    
    patron_nombre = meta.get('patron')
    if not patron_nombre:
        logger.warning(f"  {ruta_path.name}: metadatos.yaml sin 'patron', omitiendo")
        return
    redes_por_etapa = meta.get('redes_por_etapa', {})
    if not redes_por_etapa:
        logger.warning(f"  {ruta_path.name}: no hay 'redes_por_etapa'")
        return
    
    # Obtener o crear familia
    familia_nombre = meta.get('familia')
    familia = None
    if familia_nombre:
        familia = session.query(FamiliaProducto).filter_by(nombre=familia_nombre).first()
        if not familia:
            familia = FamiliaProducto(nombre=familia_nombre, descripcion=f"Familia {familia_nombre}")
            session.add(familia)
            session.flush()
            logger.info(f"    Creada familia '{familia_nombre}'")
    
    # Buscar patrón
    patron = session.query(PatronDeRuta).filter_by(nombre=patron_nombre).first()
    if not patron:
        logger.error(f"    Patrón '{patron_nombre}' no encontrado. Ejecuta primero carga de patrones (03_patrones.yaml).")
        return
    
    # Crear o actualizar HolonRuta
    holon = session.query(HolonRuta).filter_by(nombre=ruta_path.name).first()
    if not holon:
        holon = HolonRuta(
            nombre=ruta_path.name,
            descripcion=meta.get('descripcion', ''),
            patron_id=patron.id,
            familia_id=familia.id if familia else None,
            activa=meta.get('activo', True),
            condiciones=meta.get('condiciones', {})
        )
        session.add(holon)
        session.flush()
        logger.info(f"  Creada HolonRuta '{ruta_path.name}'")
    else:
        holon.patron_id = patron.id
        holon.familia_id = familia.id if familia else None
        holon.activa = meta.get('activo', True)
        holon.condiciones = meta.get('condiciones', {})
        session.commit()
        logger.info(f"  Actualizada HolonRuta '{ruta_path.name}'")
    
    # Procesar archivos PNML
    redes_dir = ruta_path / "redes"
    if not redes_dir.exists():
        logger.warning(f"    No existe subcarpeta 'redes'")
        return
    
    # Diccionario para guardar el nombre real de cada red (para encadenamiento)
    nombre_red_real = {}
    
    for etapa_codigo, archivo_pnml in redes_por_etapa.items():
        pnml_path = redes_dir / archivo_pnml
        if not pnml_path.exists():
            logger.warning(f"    Archivo {archivo_pnml} no encontrado para etapa {etapa_codigo}")
            continue
        
        etapa = session.query(EtapaRuta).filter_by(patronRuta_id=patron.id, nombre=etapa_codigo).first()
        if not etapa:
            logger.warning(f"    Etapa '{etapa_codigo}' no existe en patrón '{patron_nombre}'")
            continue
        
        # Nombre de la red: por defecto el nombre del archivo sin extensión
        nombre_red = pnml_path.stem
        # Si metadatos tiene un override, usarlo
        nombre_red = meta.get('nombre_red_override', {}).get(etapa_codigo, nombre_red)
        nombre_red_real[etapa_codigo] = nombre_red
        
        # Cargar red
        cargar_o_actualizar_red(session, nombre_red, pnml_path, patron.id)
    for red_logica, archivo_pnml in meta.get('redes_adicionales', {}).items():
        pnml_path = redes_dir / archivo_pnml
        if not pnml_path.exists():
            logger.warning(f"    Archivo adicional {archivo_pnml} no encontrado para red '{red_logica}'")
            continue
        nombre_red = meta.get('nombre_red_override', {}).get(red_logica, pnml_path.stem)
        nombre_red_real[red_logica] = nombre_red
        cargar_o_actualizar_red(session, nombre_red, pnml_path, patron.id)
    
    # Procesar encadenamiento (si existe)
    enc_path = ruta_path / "encadenamiento.yaml"
    if enc_path.exists():
        procesar_encadenamiento(session, enc_path, patron.id, nombre_red_real)
    else:
        logger.info(f"    Sin archivo encadenamiento.yaml")
    
    logger.info(f"✓ Ruta '{ruta_path.name}' procesada")

def procesar_encadenamiento(session, enc_path, patron_id, nombre_red_real):
    """Carga o actualiza la configuración de encadenamiento a partir del YAML."""
    enc_data = load_yaml(enc_path)
    enc_nombre = enc_data.get('nombre', enc_path.parent.name + "_encadenamiento")
    red_principal = enc_data.get('red_principal', '')
    reglas_raw = enc_data.get('reglas', {})
    
    # Reemplazar nombres de red en las claves de reglas si es necesario
    # Las claves tienen formato "red_nombre.transicion" (ej: "dispersion.t1")
    # donde "red_nombre" es el nombre lógico que usamos en metadatos (etapa).
    # Debemos mapear a los nombres reales de las redes cargadas.
    reglas_procesadas = {}
    for clave, valor in reglas_raw.items():
        if '.' in clave:
            red_logica, trans = clave.split('.', 1)
            # Buscar el nombre real de esa red
            real_red = None
            for etapa, nombre_real in nombre_red_real.items():
                # Podríamos tener un mapeo explícito en metadatos, o asumir que el nombre lógico
                # es el código de etapa (ej: "DIS") y el real es el nombre del archivo.
                # Por simplicidad, permitimos que el usuario ponga directamente el nombre real
                # o usamos un mapeo configurable.
                # Aquí hacemos: si red_logica es igual al nombre real (por si ya viene correcto),
                # o si coincide con algún código de etapa.
                if red_logica == nombre_real:
                    real_red = nombre_real
                    break
                for etapa_cod, real in nombre_red_real.items():
                    if red_logica == etapa_cod or red_logica == real:
                        real_red = real
                        break
            if real_red:
                nueva_clave = f"{real_red}.{trans}"
                reglas_procesadas[nueva_clave] = valor
            else:
                logger.warning(f"      No se encontró red real para '{red_logica}' en encadenamiento, se deja como está")
                reglas_procesadas[clave] = valor
        else:
            reglas_procesadas[clave] = valor
    
    # Buscar si ya existe una configuración con este nombre
    config = session.query(ConfiguracionEncadenamiento).filter_by(nombre=enc_nombre).first()
    if not config:
        config = ConfiguracionEncadenamiento(
            nombre=enc_nombre,
            red_principal_pnml=red_principal,
            descripcion=f"Encadenamiento para {enc_path.parent.name}",
            reglas=reglas_procesadas,
            patron_ruta_id=patron_id,
            activo=True
        )
        session.add(config)
        logger.info(f"    Creada configuración de encadenamiento '{enc_nombre}'")
    else:
        config.reglas = reglas_procesadas
        config.red_principal_pnml = red_principal
        config.patron_ruta_id = patron_id
        config.activo = True
        session.commit()
        logger.info(f"    Actualizada configuración de encadenamiento '{enc_nombre}'")


def procesar_todas_rutas(session):
    rutas_base = Path(__file__).parent.parent / "ontologia" / "rutas"
    if not rutas_base.exists():
        logger.error(f"No existe el directorio {rutas_base}")
        return
        
    # Recorrer todas las subcarpetas de primer nivel (cada una es una ruta)
    for item in rutas_base.iterdir():
        if not item.is_dir():
            continue
        logger.info(f"Procesando: {item.name}")
        procesar_ruta(session, item)
        
    logger.info("✅ Carga completa de rutas, redes y encadenamiento")



def main():
    session = SessionLocal()
    try:
        rutas_base = Path(__file__).parent.parent / "ontologia" / "rutas"
        if not rutas_base.exists():
            logger.error(f"No existe el directorio {rutas_base}")
            return
        
        # Recorrer todas las subcarpetas de primer nivel (cada una es una ruta)
        for item in rutas_base.iterdir():
            if not item.is_dir():
                continue
            logger.info(f"Procesando: {item.name}")
            procesar_ruta(session, item)
        
        logger.info("✅ Carga completa de rutas, redes y encadenamiento")
    except Exception as e:
        session.rollback()
        logger.exception(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()