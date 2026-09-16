# validar_yaml.py
import yaml
from pathlib import Path

def cargar_yaml(archivo):
    with open(archivo, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

base = Path(__file__).parent / 'config'

familias = cargar_yaml(base / '01_familias.yaml')
tipos_op = cargar_yaml(base / '02_tipos_operacion.yaml')
patrones = cargar_yaml(base / '03_patrones.yaml')
recursos = cargar_yaml(base / '04_recursos.yaml')
capacidades = cargar_yaml(base / '05_capacidades.yaml')
productos = cargar_yaml(base / '06_productos.yaml')
conectividad = cargar_yaml(base / '07_conectividad.yaml')

# Extraer códigos
codigos_operacion = {t['codigo'] for t in tipos_op.get('tipos_operacion', [])}
codigos_recurso = {r['codigo'] for r in recursos.get('recursos', [])}
nombres_familia = {f['nombre'] for f in familias.get('familias', [])}
nombres_patron = {p['nombre'] for p in patrones.get('patrones', [])}
# Capacidades: mapeo categoria -> operaciones
capacidad_por_categoria = {}
for cap in capacidades.get('capacidades', []):
    capacidad_por_categoria.setdefault(cap['tipo_recurso'], []).append(cap['tipo_operacion'])

# Validar recursos: su categoría debe estar en capacidades
for r in recursos.get('recursos', []):
    cat = r.get('categoria')
    if cat and cat not in capacidad_por_categoria:
        print(f"⚠️ Recurso {r['codigo']} tiene categoría '{cat}' sin capacidades definidas")

# Validar patrones
for p in patrones.get('patrones', []):
    for op in p.get('operaciones', []):
        if op not in codigos_operacion:
            print(f"⚠️ Patrón {p['nombre']} usa operación '{op}' no definida")
    if p['familia'] not in nombres_familia:
        print(f"⚠️ Patrón {p['nombre']} referencia familia '{p['familia']}' no definida")

# Validar productos
for prod in productos.get('productos', []):
    if prod['familia'] not in nombres_familia:
        print(f"⚠️ Producto {prod['codigo']} familia '{prod['familia']}' no existe")
    if prod['patron'] not in nombres_patron:
        print(f"⚠️ Producto {prod['codigo']} patrón '{prod['patron']}' no existe")
    for ruta in prod.get('rutas', []):
        for op, asign in ruta.get('asignaciones', {}).items():
            if op not in codigos_operacion:
                print(f"⚠️ Producto {prod['codigo']} ruta {ruta.get('nombre')} operación '{op}' no definida")
            recurso_cod = asign.get('recurso')
            if recurso_cod and recurso_cod not in codigos_recurso:
                print(f"⚠️ Producto {prod['codigo']} asigna recurso '{recurso_cod}' no definido")

# Validar conectividad
for conn in conectividad.get('conexiones_fisicas', []):
    if conn['origen'] not in codigos_recurso:
        print(f"⚠️ Conexión origen '{conn['origen']}' no existe")
    if conn['destino'] not in codigos_recurso:
        print(f"⚠️ Conexión destino '{conn['destino']}' no existe")

print("Validación completada.")