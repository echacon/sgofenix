import yaml
from pathlib import Path

EMPRESA_DIR = Path("ontologia/empresa")
for yaml_file in EMPRESA_DIR.glob("*.yaml"):
    print(f"\n📄 {yaml_file.name}")
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if yaml_file.name == "01_familias.yaml":
        for item in data.get('familias', []):
            print(f"   familia: {item.get('nombre')}")
    elif yaml_file.name == "02_tipos_operacion.yaml":
        for item in data.get('tipos_operacion', []):
            print(f"   tipo: {item.get('nombre')}")
    elif yaml_file.name == "03_patrones.yaml":
        for item in data.get('patrones', []):
            print(f"   patrón: {item.get('nombre')}")
    elif yaml_file.name == "04_recursos.yaml":
        for item in data.get('recursos', []):
            print(f"   recurso: {item.get('codigo')} - {item.get('nombre')}")
    elif yaml_file.name == "05_capacidades.yaml":
        for item in data.get('capacidades', []):
            print(f"   capacidad: {item.get('tipo_recurso')} -> {item.get('tipo_operacion')}")
    elif yaml_file.name == "06_productos.yaml":
        for item in data.get('productos', []):
            print(f"   producto: {item.get('codigo')} - {item.get('nombre')} (familia: {item.get('familia')})")