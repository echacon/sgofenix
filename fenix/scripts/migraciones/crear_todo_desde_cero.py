#!/usr/bin/env python3
"""Crea todas las tablas desde cero sin usar modelos existentes"""

import sqlite3
import os
from pathlib import Path

def crear_todo_desde_cero():
    # Cerrar cualquier conexión existente y renombrar la BD
    db_path = Path(__file__).parent.parent / 'fenix.db'
    
    if db_path.exists():
        backup_path = db_path.parent / 'fenix.db.backup'
        print(f"📦 Respaldando {db_path} a {backup_path}")
        os.rename(db_path, backup_path)
    
    # Crear nueva base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Crear tabla red_petri
    cursor.execute('''
        CREATE TABLE red_petri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(100) UNIQUE NOT NULL,
            descripcion VARCHAR(256),
            version INTEGER DEFAULT 1,
            tipo_red VARCHAR(20) DEFAULT 'ruta',
            lugares JSON NOT NULL,
            transiciones JSON NOT NULL,
            arcos JSON NOT NULL,
            patron_ruta_id INTEGER,
            activo BOOLEAN DEFAULT 1,
            archivo_pnml_origen VARCHAR(200),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Tabla 'red_petri' creada")
    
    # 2. Crear tabla suscripcion_evento
    cursor.execute('''
        CREATE TABLE suscripcion_evento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            red_origen_id INTEGER NOT NULL,
            evento VARCHAR(50) NOT NULL,
            red_destino_id INTEGER NOT NULL,
            accion VARCHAR(50) NOT NULL,
            destino_param VARCHAR(50) NOT NULL,
            parametros JSON,
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (red_origen_id) REFERENCES red_petri(id),
            FOREIGN KEY (red_destino_id) REFERENCES red_petri(id)
        )
    ''')
    print("✅ Tabla 'suscripcion_evento' creada")
    
    # 3. Insertar red de ejemplo (proceso negocio)
    cursor.execute('''
        INSERT INTO red_petri (nombre, tipo_red, lugares, transiciones, arcos)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'ProcesoNegocio_Pedido',
        'negocio',
        '{}',
        '{}',
        '{}'
    ))
    print("✅ Red de ejemplo insertada")
    
    # 4. Insertar red de producción (si existe el PNML)
    cursor.execute('''
        INSERT OR IGNORE INTO red_petri (nombre, tipo_red, lugares, transiciones, arcos)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4',
        'ruta',
        '{}',
        '{}',
        '{}'
    ))
    
    conn.commit()
    
    # Verificar
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = cursor.fetchall()
    print("\n📋 Tablas creadas:")
    for tabla in tablas:
        print(f"   - {tabla[0]}")
    
    cursor.execute("SELECT id, nombre, tipo_red FROM red_petri")
    redes = cursor.fetchall()
    print("\n🔧 Redes registradas:")
    for red in redes:
        print(f"   - ID {red[0]}: {red[1]} (tipo: {red[2]})")
    
    conn.close()
    print("\n✅ Base de datos inicializada completamente")

if __name__ == "__main__":
    crear_todo_desde_cero()