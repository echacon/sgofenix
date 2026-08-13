# utils/parser_pnml.py - Versión simplificada para PNML sin namespace

import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Place:
    id: str
    nombre: str
    marking_inicial: int = 0


@dataclass
class Transition:
    id: str
    nombre: str
    trigger: Optional[str] = None  # None, '200', '201', '202'


@dataclass
class Arc:
    id: str
    source: str
    target: str
    peso: int = 1


@dataclass
class PetriNet:
    nombre: str
    places: Dict[str, Place]
    transitions: Dict[str, Transition]
    arcs: Dict[str, Arc]


def cargar_red_desde_pnml(archivo_path: str) -> Optional[PetriNet]:
    """Carga una red PNML desde archivo"""
    try:
        tree = ET.parse(archivo_path)
        root = tree.getroot()
        
        # Namespace (típico de PNML)
        ns = {'pnml': 'http://www.pnml.org/version-2009/grammar/pnml'}
        
        # Buscar la red
        net_elem = root.find('.//pnml:net', ns)
        if net_elem is None:
            net_elem = root.find('.//net')
        
        # Obtener nombre de la red
        net_id = net_elem.get('id')
        if net_id and net_id != 'noID':
            net_name = net_id
        else:
            # Usar nombre del archivo sin extensión
            net_name = Path(archivo_path).stem
            logger.warning(f"   Usando nombre de archivo como fallback: {net_name}")
        
        places = {}
        transitions = {}
        arcs = {}
        
        # Cargar lugares
        for place_elem in net_elem.findall('.//place'):
            place_id = place_elem.get('id')
            name_elem = place_elem.find('.//name/text')
            place_name = name_elem.text if name_elem is not None else place_id
            
            # Marcardo inicial
            marking_inicial = 0
            initial_marking = place_elem.find('.//initialMarking/text')
            if initial_marking is not None and initial_marking.text:
                try:
                    marking_inicial = int(initial_marking.text)
                except:
                    marking_inicial = 0
            
            places[place_id] = Place(
                id=place_id,
                nombre=place_name,
                marking_inicial=marking_inicial
            )
        
        # Cargar transiciones
        for trans_elem in net_elem.findall('.//transition'):
            trans_id = trans_elem.get('id')
            name_elem = trans_elem.find('.//name/text')
            trans_name = name_elem.text if name_elem is not None else trans_id
            
            # ✅ Leer trigger como en Java
            trigger = None
            
            toolspecific = trans_elem.find('.//toolspecific')
            if toolspecific is not None:
                # Buscar la etiqueta <trigger>
                trigger_elem = toolspecific.find('.//trigger')
                if trigger_elem is not None:
                    # Leer el atributo 'type' (como en el código Java)
                    trigger_type = trigger_elem.get('type')
                    if trigger_type:
                        trigger = trigger_type
                    else:
                        # Fallback: leer el texto
                        trigger_text = trigger_elem.text
                        if trigger_text and trigger_text.strip() in ['200', '201', '202']:
                            trigger = trigger_text.strip()
            
            transitions[trans_id] = Transition(
                id=trans_id,
                nombre=trans_name,
                trigger=trigger  # None, '200', '201', '202'
            )
        
        # Cargar arcos
        for arc_elem in net_elem.findall('.//arc'):
            arc_id = arc_elem.get('id')
            source = arc_elem.get('source')
            target = arc_elem.get('target')
            
            # Peso del arco (por defecto 1)
            peso = 1
            inscription = arc_elem.find('.//inscription/text')
            if inscription is not None and inscription.text:
                try:
                    peso = int(inscription.text)
                except:
                    peso = 1
            
            arcs[arc_id] = Arc(
                id=arc_id,
                source=source,
                target=target,
                peso=peso
            )
        
        return PetriNet(
            nombre=net_name,
            places=places,
            transitions=transitions,
            arcs=arcs
        )
        
    except Exception as e:
        logger.error(f"Error parseando PNML {archivo_path}: {e}")
        return None