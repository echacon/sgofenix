#!/usr/bin/env python3
# scripts/cargar_ontologia.py

import sys
import os
from pathlib import Path
import yaml
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajouter la racine du projet au PYTHONPATH
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modelos.declarative_base import Base
from modelos.Taxonomia import (
    FamiliaProducto, PatronDeRuta, EtapaRuta, TransicionPatron,
    TParcoEnt, TParcoSal, TipoDeOperacion
)
from modelos.Recursos import (
    UnidadNegocio, UnidadFuncional, Recurso, RecursoEquipo, RecursoPersonal,
    Rol, RolJugado, ServicioTecnico, ServicioTecnicoOfrecido,
    ServicioNegocio, ServicioNegocioOfrecido, ConexionFisica
)
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula, ConexionReal
from modelos.RutaProducto import RutaProducto
from modelos.RedPetri import RedPetri
from modelos.DocumentosNegocio import OrdenProduccion, Pedido, DocumentoEstado
from modelos.ProcesoOcurrente import InstanciaRed

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------
# Utilitaires de chargement YAML
# ------------------------------
def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# ------------------------------
# Chargement des patrons (03_patrones.yaml)
# ------------------------------
def cargar_patrones(session, data):
    logger.info("Chargement des patrons de route...")
    for p in data.get('patrones', []):
        patron_nom = p['nombre']
        # Récupérer la famille
        familia = session.query(FamiliaProducto).filter_by(nombre=p['familia']).first()
        if not familia:
            raise ValueError(f"Famille '{p['familia']}' inconnue pour le patron '{patron_nom}'")
        
        patron = session.query(PatronDeRuta).filter_by(nombre=patron_nom).first()
        if not patron:
            patron = PatronDeRuta(
                nombre=patron_nom,
                version=p.get('version', '1.0'),
                descripcion=p.get('descripcion', ''),
                familiaProducto_id=familia.id,
                activo=True
            )
            session.add(patron)
            session.flush()  # pour obtenir l'id
        else:
            # Mise à jour
            patron.version = p.get('version', patron.version)
            patron.descripcion = p.get('descripcion', patron.descripcion)
            patron.familiaProducto_id = familia.id
            # Supprimer les anciennes étapes et transitions (optionnel)
            # Ici on choisit de les recréer proprement
            for etapa in patron.etapasRuta:
                session.delete(etapa)
            for trans in patron.transiciones:
                session.delete(trans)
            session.flush()
        
        # Créer les étapes
        etapas_dict = {}
        for e in p.get('etapas', []):
            tipo_op = session.query(TipoDeOperacion).filter_by(nombre=e['tipo_operacion']).first()
            if not tipo_op:
                raise ValueError(f"Type d'opération '{e['tipo_operacion']}' inconnu")
            etapa = EtapaRuta(
                nombre=e['codigo'],
                patronRuta_id=patron.id,
                tipoDeOperacion_id=tipo_op.id
            )
            session.add(etapa)
            session.flush()
            etapas_dict[e['codigo']] = etapa
        
        # Créer les transitions et arcs
        for t in p.get('transiciones', []):
            trans = TransicionPatron(
                nombre=t['id'],
                patron_id=patron.id
            )
            session.add(trans)
            session.flush()
            # Arcs entrants
            for entrada_nom in t.get('entradas', []):
                etapa = etapas_dict.get(entrada_nom)
                if not etapa:
                    raise ValueError(f"Étape '{entrada_nom}' inconnue pour transition {t['id']}")
                arc_ent = TParcoEnt(
                    nombre=f"arc_ent_{t['id']}_{entrada_nom}",
                    trans_id=trans.id,
                    etapa_id=etapa.id
                )
                session.add(arc_ent)
            # Arcs sortants
            for salida_nom in t.get('salidas', []):
                etapa = etapas_dict.get(salida_nom)
                if not etapa:
                    raise ValueError(f"Étape '{salida_nom}' inconnue pour transition {t['id']}")
                arc_sal = TParcoSal(
                    nombre=f"arc_sal_{t['id']}_{salida_nom}",
                    trans_id=trans.id,
                    etapa_id=etapa.id
                )
                session.add(arc_sal)
        
        session.commit()
        logger.info(f"  ✓ Patron '{patron_nom}' chargé avec {len(etapas_dict)} étapes")

# ------------------------------
# Chargement des routes (dossiers dans rutas/)
# ------------------------------
def cargar_rutas(session, rutas_path):
    logger.info("Carga de las rutas y enlaces con los patrones...")
    for ruta_dir in rutas_path.iterdir():
        if not ruta_dir.is_dir():
            continue
        meta_path = ruta_dir / "metadatos.yaml"
        if not meta_path.exists():
            logger.warning(f"  ⚠ no hay metadatoss.yaml dans {ruta_dir.name}, ignorado")
            continue
        
        meta = load_yaml(meta_path)
        patron_nom = meta.get('patron')
        if not patron_nom:
            logger.warning(f"  ⚠ No hay patrón especificado en {ruta_dir.name}/metadatos.yaml")
            continue
        
        patron = session.query(PatronDeRuta).filter_by(nombre=patron_nom).first()
        if not patron:
            raise ValueError(f"Patron '{patron_nom}' inconnu pour la route {ruta_dir.name}")
        
        # Lire la configuration des réseaux par étape
        redes_por_etapa = meta.get('redes_por_etapa', {})
        redes_dir = ruta_dir / "redes"
        if not redes_dir.exists():
            logger.warning(f"  ⚠ Fichero redes/ ausente en {ruta_dir.name}")
            continue
        
        # Pour chaque (codigo_etapa, nom_red) on cherche la red Petri
        for codigo_etapa, red_nombre in redes_por_etapa.items():
            # Trouver l'étape correspondante dans le patron
            etapa = session.query(EtapaRuta).join(PatronDeRuta).filter(
                PatronDeRuta.id == patron.id,
                EtapaRuta.nombre == codigo_etapa
            ).first()
            if not etapa:
                raise ValueError(f"Etapa '{codigo_etapa}' del patrón '{patron_nom}' no encontrado para la red '{red_nombre}'")
            
            # Chercher la red Petri dans la base (déjà chargée par le script existant)
            red = session.query(RedPetri).filter_by(nombre=red_nombre).first()
            if not red:
                logger.warning(f"  ⚠ Red Petri '{red_nombre}' no encontrada en la base (archivo .pnml falta ?)")
                continue
            
            # Lier la red au patron et à l'étape
            red.patron_ruta_id = patron.id
            # Optionnel : ajouter un champ etapa_ruta_id dans RedPetri ? Sinon, on peut stocker ailleurs.
            # Pour l'instant on met juste le patron.
            logger.info(f"  ✓ Enlazado red '{red_nombre}' → patrón '{patron_nom}', etapa '{codigo_etapa}'")
        
        session.commit()
        logger.info(f"  ✓ Rota {ruta_dir.name} completada")

# ------------------------------
# Chargement principal (appelé par l'existant)
# ------------------------------
def cargar_todo():
    engine = create_engine('sqlite:///fenix.db')
    Base.metadata.create_all(engine)  # crée les tables si besoin
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Charger dans l'ordre (à adapter selon vos fichiers existants)
        # On suppose que les autres fichiers sont déjà chargés par une autre fonction.
        # Ici on ajoute juste les patrons et les liens.
        
        # 1. Patrones
        patrones_path = ROOT / "ontologia" / "empresa" / "03_patrones.yaml"
        if patrones_path.exists():
            data = load_yaml(patrones_path)
            cargar_patrones(session, data)
        else:
            logger.warning("Archivo 03_patrones.yaml no encontrado, no se cargan los patrones")
        
        # 2. Routes
        rutas_path = ROOT / "ontologia" / "rutas"
        if rutas_path.exists():
            cargar_rutas(session, rutas_path)
        else:
            logger.warning("Directorio 'rutas' no encontrado")
        
    except Exception as e:
        session.rollback()
        logger.exception(f"Error en la carga: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    cargar_todo()