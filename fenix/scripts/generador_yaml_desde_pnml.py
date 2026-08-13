#!/usr/bin/env python3
# scripts/generador_yaml_desde_pnml.py
"""
Genera automáticamente el archivo de configuración YAML de un proceso
a partir de su archivo PNML de WoPeD.
"""

import sys
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path

def parse_pnml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # WoPeD usually saves inside <net> -> <page> or directly under <net>
    # We will search recursively to be compatible with different WoPeD versions
    places = {}
    transitions = {}
    arcs = []
    
    for net in root.findall('.//net'):
        for place in net.findall('.//place'):
            p_id = place.get('id')
            name_elem = place.find('.//name/text')
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else p_id
            places[p_id] = name
            
        for transition in net.findall('.//transition'):
            t_id = transition.get('id')
            name_elem = transition.find('.//name/text')
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else t_id
            
            # Extract trigger type (e.g. 200, 201)
            trigger_elem = transition.find('.//trigger')
            if trigger_elem is None:
                trigger_elem = transition.find('.//toolspecific/trigger')
            trigger_type = int(trigger_elem.get('type')) if trigger_elem is not None and trigger_elem.get('type') else 200
            
            transitions[t_id] = {
                'id': t_id,
                'trigger': name,
                'tipo': trigger_type,
                'origen': [],
                'destino': []
            }
            
        for arc in net.findall('.//arc'):
            source = arc.get('source')
            target = arc.get('target')
            arcs.append((source, target))
            
    for source, target in arcs:
        if target in transitions:
            transitions[target]['origen'].append(source)
        elif source in transitions:
            transitions[source]['destino'].append(target)
            
    return places, transitions

def generate_yaml(pnml_path, output_yaml_path):
    places, transitions = parse_pnml(pnml_path)
    
    # Formatear pasos
    pasos_yaml = []
    def get_p_id_num(p_id):
        num_part = p_id[1:]
        return int(num_part) if num_part.isdigit() else 999
        
    for p_id in sorted(places.keys(), key=get_p_id_num):
        pasos_yaml.append({
            'id': p_id,
            'nombre': places[p_id],
            'duracion': "10 m",      # Valor por defecto
            'velocidad': "media"     # Valor por defecto
        })
        
    # Formatear transiciones
    def get_t_id_num(t_id):
        num_part = t_id[1:]
        return int(num_part) if num_part.isdigit() else 999
        
    transiciones_yaml = []
    for t_id in sorted(transitions.keys(), key=get_t_id_num):
        t = transitions[t_id]
        transiciones_yaml.append({
            'id': t['id'],
            'trigger': t['trigger'],
            'tipo': t['tipo'],
            'origen': sorted(t['origen'], key=get_p_id_num),
            'destino': sorted(t['destino'], key=get_p_id_num)
        })
        
    yaml_data = {
        'nombre': f"Proceso generado desde {Path(pnml_path).name}",
        'categoria_recurso': "DISPERSOR_ALTA", # Valor por defecto
        'pasos': pasos_yaml,
        'transiciones': transiciones_yaml
    }
    
    with open(output_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
    print(f"✅ Archivo YAML generado exitosamente en: {output_yaml_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python generador_yaml_desde_pnml.py <ruta_archivo.pnml> <ruta_salida.yaml>")
        sys.exit(1)
        
    generate_yaml(sys.argv[1], sys.argv[2])
