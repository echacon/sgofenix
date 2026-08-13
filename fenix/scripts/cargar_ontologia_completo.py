#!/usr/bin/env python3
# scripts/cargar_ontologia_completo.py
"""
Carga completa de la ontología:
- Unidades funcionales y de negocio (00_empresa.yaml)
- Tipos de operación (02_tipos_operacion.yaml)
- Patrones de ruta (03_patrones.yaml)
- Recursos (04_recursos.yaml) - asumiendo que ya existe o se carga aparte
- Conexiones físicas (07_conectividad.yaml)
- Asignaciones de recursos a redes (asignaciones_recursos.yaml)
- Vinculación de redes Petri a patrones y etapas (desde carpetas en ontologia/rutas/)
"""

import sys
import os
from pathlib import Path
import yaml
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajusta la ruta raíz de tu proyecto
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modelos.declarative_base import Base, engine, SessionLocal
from modelos.Taxonomia import (
    FamiliaProducto, PatronDeRuta, EtapaRuta, TransicionPatron,
    TParcoEnt, TParcoSal, TipoDeOperacion
)
from modelos.Recursos import (
    UnidadNegocio, UnidadFuncional, Recurso, RecursoEquipo, RecursoPersonal,
    Rol, RolJugado, ConexionFisica
)
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula, ConexionReal
from modelos.RedPetri import RedPetri
from modelos.RutaProducto import RutaProducto
from modelos.DocumentosNegocio import OrdenProduccion, Pedido, DocumentoEstado
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.Encadenamiento import ConfiguracionEncadenamiento

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_unidades_funcionales(session, data):
    """Carga desde 00_empresa.yaml"""
    logger.info("Cargando unidades funcionales...")
    for uf in data.get('unidades_funcionales', []):
        codigo = uf['codigo']
        # Verificar si ya existe
        existing = session.query(UnidadFuncional).filter_by(codigo=codigo).first()
        if existing:
            logger.info(f"  Unidad funcional {codigo} ya existe, actualizando...")
            existing.nombre = uf['nombre']
            existing.descripcion = uf.get('descripcion', '')
        else:
            nueva = UnidadFuncional(
                codigo=codigo,
                nombre=uf['nombre'],
                descripcion=uf.get('descripcion', '')
            )
            session.add(nueva)
            session.flush()
            # Manejar padre después de tener el id
            if 'unidad_padre' in uf and uf['unidad_padre']:
                padre = session.query(UnidadFuncional).filter_by(codigo=uf['unidad_padre']).first()
                if padre:
                    nueva.unidadPadre_id = padre.id
            # Si es unidad de negocio, crear también en UnidadNegocio?
            if uf.get('es_unidad_negocio', False):
                neg_exist = session.query(UnidadNegocio).filter_by(codigo=codigo).first()
                if not neg_exist:
                    neg = UnidadNegocio(
                        codigo=codigo,
                        nombre=uf['nombre'],
                        descripcion=uf.get('descripcion', '')
                    )
                    session.add(neg)
                    session.flush()
                    # Vincular la unidad funcional a esta unidad de negocio
                    nueva.unidadNegocio_id = neg.id
    session.commit()
    logger.info("✓ Unidades funcionales cargadas")

def cargar_tipos_operacion(session, data):
    """Carga desde 02_tipos_operacion.yaml"""
    logger.info("Cargando tipos de operación...")
    for op in data.get('tipos_operacion', []):
        nombre = op['nombre']
        existing = session.query(TipoDeOperacion).filter_by(nombre=nombre).first()
        if not existing:
            nuevo = TipoDeOperacion(
                nombre=nombre,
                codigo=nombre,  # usamos el nombre como código
                descripcion=op.get('descripcion', '')
            )
            session.add(nuevo)
    session.commit()
    logger.info("✓ Tipos de operación cargados")

def cargar_patrones(session, data):
    """Carga desde 03_patrones.yaml (estructura con operaciones y transiciones)"""
    logger.info("Cargando patrones de ruta...")
    for p in data.get('patrones', []):
        patron_nom = p['nombre']
        familia_nom = p.get('familia')
        if not familia_nom:
            logger.warning(f"Patrón {patron_nom} sin familia, se omite")
            continue
        familia = session.query(FamiliaProducto).filter_by(nombre=familia_nom).first()
        if not familia:
            # Crear familia si no existe
            familia = FamiliaProducto(nombre=familia_nom, descripcion=f"Familia para {patron_nom}")
            session.add(familia)
            session.flush()
            logger.info(f"  Creada familia {familia_nom}")
        
        # Buscar o crear patrón
        patron = session.query(PatronDeRuta).filter_by(nombre=patron_nom).first()
        if patron:
            logger.info(f"  Actualizando patrón {patron_nom}")
            # Limpiar etapas y transiciones antiguas para recrear
            for etapa in patron.etapasRuta:
                session.delete(etapa)
            for trans in patron.transiciones:
                session.delete(trans)
            session.flush()
        else:
            patron = PatronDeRuta(
                nombre=patron_nom,
                version=p.get('version', '1.0'),
                descripcion=p.get('descripcion', ''),
                familiaProducto_id=familia.id,
                activo=True
            )
            session.add(patron)
            session.flush()
            logger.info(f"  Creado patrón {patron_nom}")
        
        # Crear etapas a partir de la lista 'operaciones'
        etapas_dict = {}
        for op_codigo in p.get('operaciones', []):
            # Buscar tipo de operación por nombre (código)
            tipo_op = session.query(TipoDeOperacion).filter_by(nombre=op_codigo).first()
            if not tipo_op:
                logger.warning(f"  Tipo de operación {op_codigo} no existe, se crea automáticamente")
                tipo_op = TipoDeOperacion(nombre=op_codigo, codigo=op_codigo, descripcion="")
                session.add(tipo_op)
                session.flush()
            etapa = EtapaRuta(
                nombre=op_codigo,
                patronRuta_id=patron.id,
                tipoDeOperacion_id=tipo_op.id
            )
            session.add(etapa)
            session.flush()
            etapas_dict[op_codigo] = etapa
            logger.debug(f"    Etapa {op_codigo} creada")
        
        # Crear transiciones según el array 'transiciones'
        for idx, t in enumerate(p.get('transiciones', [])):
            trans_nom = t.get('nombre', f"T{idx+1}")
            desde = t.get('desde')
            hacia = t.get('hacia')
            if not desde or not hacia:
                logger.warning(f"  Transición {trans_nom} sin desde/hacia, ignorada")
                continue
            if desde not in etapas_dict or hacia not in etapas_dict:
                logger.warning(f"  Etapa {desde} o {hacia} no existe en patrón {patron_nom}")
                continue
            
            trans = TransicionPatron(
                nombre=trans_nom,
                patron_id=patron.id
            )
            session.add(trans)
            session.flush()
            
            # Arco de entrada: desde la etapa origen a la transición
            arc_ent = TParcoEnt(
                nombre=f"{trans_nom}_ent_{desde}",
                trans_id=trans.id,
                etapa_id=etapas_dict[desde].id
            )
            session.add(arc_ent)
            # Arco de salida: desde la transición a la etapa destino
            arc_sal = TParcoSal(
                nombre=f"{trans_nom}_sal_{hacia}",
                trans_id=trans.id,
                etapa_id=etapas_dict[hacia].id
            )
            session.add(arc_sal)
        
        session.commit()
        logger.info(f"  ✓ Patrón '{patron_nom}' con {len(etapas_dict)} etapas")
    session.commit()

def cargar_conexiones_fisicas(session, data):
    """Carga desde 07_conectividad.yaml"""
    logger.info("Cargando conexiones físicas...")
    for conn in data.get('conexiones_fisicas', []):
        origen_cod = conn['origen']
        destino_cod = conn['destino']
        # Buscar recursos por código
        origen = session.query(Recurso).filter_by(codigo=origen_cod).first()
        destino = session.query(Recurso).filter_by(codigo=destino_cod).first()
        if not origen or not destino:
            logger.warning(f"  Recurso origen o destino no encontrado: {origen_cod} -> {destino_cod}")
            continue
        existing = session.query(ConexionFisica).filter_by(
            recurso_origen_id=origen.id, recurso_destino_id=destino.id
        ).first()
        if existing:
            existing.tipo = conn.get('tipo', existing.tipo)
            existing.diametro_pulgadas = conn.get('diametro_pulgadas')
            existing.flujo_maximo_lps = conn.get('flujo_maximo_lps')
            existing.perdida_material_pct = conn.get('perdida_material_pct', 0.0)
            existing.requiere_bombeo = conn.get('requiere_bombeo', False)
            existing.requiere_operador = conn.get('requiere_operador', False)
        else:
            nueva = ConexionFisica(
                recurso_origen_id=origen.id,
                recurso_destino_id=destino.id,
                tipo=conn.get('tipo', 'MANUAL'),
                diametro_pulgadas=conn.get('diametro_pulgadas'),
                flujo_maximo_lps=conn.get('flujo_maximo_lps'),
                perdida_material_pct=conn.get('perdida_material_pct', 0.0),
                requiere_bombeo=conn.get('requiere_bombeo', False),
                requiere_operador=conn.get('requiere_operador', False),
                activa=True
            )
            session.add(nueva)
    session.commit()
    logger.info("✓ Conexiones físicas cargadas")

def vincular_redes_a_patrones(session, rutas_path):
    """
    Recorre cada subcarpeta en ontologia/rutas/ y lee su metadatos.yaml
    para vincular redes Petri (por nombre) a un patrón y a una etapa específica.
    """
    logger.info("Vinculando redes Petri a patrones y etapas...")
    if not rutas_path.exists():
        logger.warning(f"Directorio {rutas_path} no existe, omitiendo vinculación")
        return
    
    for ruta_dir in rutas_path.iterdir():
        if not ruta_dir.is_dir():
            continue
        meta_path = ruta_dir / "metadatos.yaml"
        if not meta_path.exists():
            logger.warning(f"  No hay metadatos.yaml en {ruta_dir.name}, se omite")
            continue
        
        meta = load_yaml(meta_path)
        patron_nom = meta.get('patron')
        if not patron_nom:
            logger.warning(f"  metadatos.yaml en {ruta_dir.name} no tiene 'patron'")
            continue
        
        patron = session.query(PatronDeRuta).filter_by(nombre=patron_nom).first()
        if not patron:
            logger.warning(f"  Patrón '{patron_nom}' no encontrado en BD")
            continue
        
        redes_por_etapa = meta.get('redes_por_etapa', {})
        # redes_por_etapa ejemplo: {"DIS": "DIS_DIL_dispersion", "DIL": "DIS_DIL_dilucion"}
        for codigo_etapa, red_nombre in redes_por_etapa.items():
            # Buscar la etapa en el patrón
            etapa = session.query(EtapaRuta).filter_by(
                patronRuta_id=patron.id, nombre=codigo_etapa
            ).first()
            if not etapa:
                logger.warning(f"  Etapa '{codigo_etapa}' no existe en patrón {patron_nom}")
                continue
            # Buscar la red Petri por nombre
            red = session.query(RedPetri).filter_by(nombre=red_nombre).first()
            if not red:
                logger.warning(f"  Red Petri '{red_nombre}' no encontrada en BD")
                continue
            # Asignar el patrón a la red (si no lo tiene)
            if red.patron_ruta_id is None:
                red.patron_ruta_id = patron.id
                logger.info(f"    Red '{red_nombre}' vinculada a patrón {patron_nom} (etapa {codigo_etapa})")
            else:
                logger.debug(f"    Red '{red_nombre}' ya tenía patrón asignado")
        
        # También cargar encadenamiento si existe
        enc_path = ruta_dir / "encadenamiento.yaml"
        if enc_path.exists():
            enc_data = load_yaml(enc_path)
            # Buscar o crear ConfiguracionEncadenamiento
            enc_nombre = enc_data.get('nombre', f"Encadenamiento_{ruta_dir.name}")
            conf_enc = session.query(ConfiguracionEncadenamiento).filter_by(nombre=enc_nombre).first()
            if not conf_enc:
                conf_enc = ConfiguracionEncadenamiento(
                    nombre=enc_nombre,
                    red_principal_pnml=enc_data.get('red_principal', ''),
                    descripcion=f"Encadenamiento para {ruta_dir.name}",
                    reglas=enc_data.get('reglas', {}),
                    patron_ruta_id=patron.id,
                    activo=True
                )
                session.add(conf_enc)
                logger.info(f"  Creada configuración de encadenamiento '{enc_nombre}'")
            else:
                conf_enc.reglas = enc_data.get('reglas', conf_enc.reglas)
                conf_enc.patron_ruta_id = patron.id
                logger.info(f"  Actualizado encadenamiento '{enc_nombre}'")
        
        session.commit()
        logger.info(f"✓ Ruta {ruta_dir.name} procesada")

def cargar_todo():
    """Función principal que orquesta toda la carga"""
    session = SessionLocal()
    try:
        # 1. Cargar unidades funcionales
        path_empresa = ROOT / "ontologia" / "empresa" / "00_empresa.yaml"
        if path_empresa.exists():
            data_emp = load_yaml(path_empresa)
            cargar_unidades_funcionales(session, data_emp)
        else:
            logger.warning("No se encuentra 00_empresa.yaml")
        
        # 2. Cargar tipos de operación
        path_tipos = ROOT / "ontologia" / "empresa" / "02_tipos_operacion.yaml"
        if path_tipos.exists():
            data_tipos = load_yaml(path_tipos)
            cargar_tipos_operacion(session, data_tipos)
        else:
            logger.warning("No se encuentra 02_tipos_operacion.yaml")
        
        # 3. Cargar patrones de ruta (03_patrones.yaml)
        path_patrones = ROOT / "ontologia" / "empresa" / "03_patrones.yaml"
        if path_patrones.exists():
            data_pat = load_yaml(path_patrones)
            cargar_patrones(session, data_pat)
        else:
            logger.warning("No se encuentra 03_patrones.yaml")
        
        # 4. Cargar conexiones físicas (07_conectividad.yaml)
        path_conex = ROOT / "ontologia" / "empresa" / "07_conectividad.yaml"
        if path_conex.exists():
            data_conex = load_yaml(path_conex)
            cargar_conexiones_fisicas(session, data_conex)
        else:
            logger.warning("No se encuentra 07_conectividad.yaml")
        
        # 5. Vincular redes Petri a patrones usando las carpetas de rutas
        rutas_path = ROOT / "ontologia" / "rutas"
        vincular_redes_a_patrones(session, rutas_path)
        
        logger.info("✅ CARGA COMPLETA EXITOSA")
        
    except Exception as e:
        session.rollback()
        logger.exception(f"Error durante la carga: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    cargar_todo()