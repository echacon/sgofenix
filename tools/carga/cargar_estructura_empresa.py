#!/usr/bin/env python3
# scripts/cargar_estructura_empresa.py

import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.append(str(Path(__file__).parent.parent))

from modelos.Recursos import UnidadFuncional, UnidadNegocio

engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)

ONTOLOGIA = Path(__file__).parent.parent / "ontologia"
EMPRESA_DIR = ONTOLOGIA / "empresa"

def cargar_estructura(session):
    print("🏢 Cargando estructura de la empresa...")
    
    estructura_path = EMPRESA_DIR / "00_empresa.yaml"
    if not estructura_path.exists():
        print("❌ No se encontró 00_empresa.yaml")
        return False
        
    with open(estructura_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Primera pasada: crear todas las UnidadFuncional sin unidadNegocio_id
    unidades_por_codigo = {}
    for item in data.get('unidades_funcionales', []):
        unidad = UnidadFuncional(
            codigo=item['codigo'],
            nombre=item['nombre'],
            descripcion=item.get('descripcion', '')
        )
        session.add(unidad)
        session.flush()  # para obtener el id
        unidades_por_codigo[item['codigo']] = unidad
    
    # Segunda pasada: establecer relaciones padre-hijo
    for item in data.get('unidades_funcionales', []):
        if 'unidad_padre' in item:
            padre = unidades_por_codigo.get(item['unidad_padre'])
            if padre:
                unidad = unidades_por_codigo[item['codigo']]
                unidad.unidadPadre_id = padre.id
    
    # Tercera pasada: crear UnidadNegocio cuando se requiera y asignar a la UnidadFuncional
    for item in data.get('unidades_funcionales', []):
        if item.get('es_unidad_negocio', False):
            # Crear UnidadNegocio con su propio código (puede ser el mismo de la unidad funcional)
            unidad_negocio = UnidadNegocio(
                codigo=f"UN_{item['codigo']}",   # o puedes usar item['codigo'] si es único
                nombre=item['nombre'],
                descripcion=item.get('descripcion', '')
            )
            session.add(unidad_negocio)
            session.flush()
            # Asignar la unidad de negocio a la unidad funcional
            unidad_func = unidades_por_codigo[item['codigo']]
            unidad_func.unidadNegocio_id = unidad_negocio.id
    
    session.commit()
    print("✅ Estructura de empresa cargada correctamente")
    return True

def main():
    session = Session()
    try:
        cargar_estructura(session)
    except Exception as e:
        print(f"❌ Error cargando estructura: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()