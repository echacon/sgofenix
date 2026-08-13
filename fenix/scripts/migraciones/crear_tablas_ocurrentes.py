#!/usr/bin/env python3
"""
Script para crear las tablas de procesos ocurrentes
(OrdenProduccion, InstanciaRed, EventoRed)
"""

import sys
import os
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect
from modelos.declarative_base import Base, engine
from modelos.ProcesoOcurrente import OrdenProduccion, InstanciaRed, EventoRed

def crear_tablas_ocurrentes():
    """Crea las tablas de procesos ocurrentes en la base de datos"""
    
    print("=" * 60)
    print("CREANDO TABLAS DE PROCESOS OCURRENTES")
    print("=" * 60)
    
    # Verificar qué tablas ya existen
    inspector = inspect(engine)
    tablas_existentes = inspector.get_table_names()
    
    tablas_a_crear = ['orden_produccion', 'instancia_red', 'evento_red']
    tablas_faltantes = [t for t in tablas_a_crear if t not in tablas_existentes]
    
    if tablas_faltantes:
        print(f"\n📋 Creando tablas: {', '.join(tablas_faltantes)}")
        # Crear solo las tablas que no existen
        Base.metadata.create_all(engine, tables=[Base.metadata.tables[t] for t in tablas_faltantes if t in Base.metadata.tables])
        print("✅ Tablas creadas exitosamente")
    else:
        print("\n✅ Todas las tablas ya existen")
    
    # Mostrar resumen
    print("\n📊 TABLAS EN LA BASE DE DATOS:")
    print("-" * 40)
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        print(f"  • {table_name}: {len(columns)} columnas")
    
    print("\n" + "=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

def eliminar_tablas_ocurrentes():
    """Elimina las tablas de procesos ocurrentes"""
    
    print("=" * 60)
    print("ELIMINANDO TABLAS DE PROCESOS OCURRENTES")
    print("=" * 60)
    
    tablas_a_eliminar = ['evento_red', 'instancia_red', 'orden_produccion']
    
    for table in tablas_a_eliminar:
        if table in Base.metadata.tables:
            Base.metadata.tables[table].drop(engine, checkfirst=True)
            print(f"✅ Tabla '{table}' eliminada")
    
    print("\n" + "=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Gestionar tablas de procesos ocurrentes')
    parser.add_argument('--drop', action='store_true', help='Eliminar tablas existentes')
    parser.add_argument('--reset', action='store_true', help='Eliminar y recrear tablas')
    
    args = parser.parse_args()
    
    if args.drop:
        eliminar_tablas_ocurrentes()
    elif args.reset:
        eliminar_tablas_ocurrentes()
        print("\n")
        crear_tablas_ocurrentes()
    else:
        crear_tablas_ocurrentes()