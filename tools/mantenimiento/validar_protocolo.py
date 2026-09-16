#!/usr/bin/env python3
# validar_protocolo.py - Verifica la composición global de redes comunicantes

import sys
import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.parser_pnml import cargar_red_desde_pnml
from servicios.validador_modelos import ValidadorRedes

def cargar_redes_desde_archivos(directorio_redes):
    redes_data = {}
    for pnml_file in Path(directorio_redes).glob("*.pnml"):
        yaml_file = pnml_file.with_suffix('.yaml')
        if not yaml_file.exists():
            print(f"⚠️ Falta archivo yaml para {pnml_file.name}, se omite")
            continue
        with open(yaml_file, 'r') as f:
            meta = yaml.safe_load(f)
        red = cargar_red_desde_pnml(str(pnml_file))
        if not red:
            print(f"❌ Error al cargar red {pnml_file.name}")
            continue
        nombre = meta.get('nombre', pnml_file.stem)
        if 'marcado_inicial' not in meta or 'estados_finales' not in meta:
            print(f"⚠️ Red {nombre}: faltan marcado_inicial o estados_finales en YAML")
            continue
        redes_data[nombre] = {
            'red': red,
            'marcado_inicial': meta['marcado_inicial'],
            'estados_finales': meta['estados_finales']
        }
    return redes_data

def cargar_encadenamiento(archivo_enc):
    with open(archivo_enc, 'r') as f:
        data = yaml.safe_load(f)
    reglas = {}
    for key, dests in data.get('reglas', {}).items():
        if '.' not in key:
            print(f"Clave inválida: {key}")
            continue
        red_orig, trans_orig = key.split('.', 1)
        for d in dests:
            reglas.setdefault((red_orig, trans_orig), []).append((d['red_destino'], d['evento_destino']))
    return reglas

def main():
    if len(sys.argv) < 2:
        print("Uso: validar_protocolo.py <directorio_redes> [archivo_encadenamiento.yaml]")
        sys.exit(1)
    dir_redes = sys.argv[1]
    archivo_enc = sys.argv[2] if len(sys.argv) > 2 else None

    redes_data = cargar_redes_desde_archivos(dir_redes)
    if not redes_data:
        print("No se cargaron redes.")
        sys.exit(1)

    reglas = {}
    if archivo_enc:
        reglas = cargar_encadenamiento(archivo_enc)
    else:
        print("No se proporcionó encadenamiento, solo se verificarán redes individualmente.")
        for nombre, data in redes_data.items():
            es_valida, errores = ValidadorRedes.validar_red_petri(data['red'], {
                'marcado_inicial': data['marcado_inicial'],
                'estados_finales': data['estados_finales']
            })
            if es_valida:
                print(f"✅ Red {nombre}: válida")
            else:
                print(f"❌ Red {nombre}: inválida - {errores}")
        return

    # Validación global
    alcanzable, msg = ValidadorRedes.validar_composicion_global(redes_data, reglas, max_states=5000)
    if alcanzable:
        print("✅ Composición global: el sistema puede alcanzar un estado final.")
    else:
        print(f"❌ Composición global: {msg}")

if __name__ == "__main__":
    main()