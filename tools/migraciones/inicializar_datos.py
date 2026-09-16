#!/usr/bin/env python3
"""
Script para inicializar datos de prueba en la base de datos
Ejecutar: python scripts/inicializar_datos.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from modelos.declarative_base import Base
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta, TipoDeOperacion, TipoRecurso, CapacidadTipoOperacion
from modelos.Producto import Producto, HolonRuta
from modelos.Usuario import Usuario

# Conectar a la BD
DATABASE_URL = 'sqlite:///fenix.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)
session = Session()

# Crear tablas si no existen
Base.metadata.create_all(engine)

print("=" * 60)
print("INICIALIZANDO DATOS DE PRUEBA")
print("=" * 60)

# Variables para guardar IDs
familia_id = None
patron_id = None
producto_id = None
holon_id = None

# 1. Crear Familia de Producto
familia = session.query(FamiliaProducto).first()
if not familia:
    familia = FamiliaProducto(
        nombre="Pinturas Base Agua",
        descripcion="Familia de pinturas base agua"
    )
    session.add(familia)
    session.commit()
    print(f"✅ Familia creada: {familia.nombre} (ID: {familia.id})")
else:
    print(f"📌 Familia existente: {familia.nombre} (ID: {familia.id})")
familia_id = familia.id

# 2. Crear Patrón de Ruta
patron = session.query(PatronDeRuta).filter_by(nombre="Estándar").first()
if not patron:
    patron = PatronDeRuta(
        nombre="Estándar",
        descripcion="Ruta estándar de producción",
        familiaProducto_id=familia_id
    )
    session.add(patron)
    session.commit()
    print(f"✅ Patrón creado: {patron.nombre} (ID: {patron.id})")
else:
    print(f"📌 Patrón existente: {patron.nombre} (ID: {patron.id})")
patron_id = patron.id

# 3. Crear Producto
producto = session.query(Producto).first()
if not producto:
    producto = Producto(
        nombre="Base Agua Blanca",
        codigo_interno="BB-001",
        es_fabricado=True,
        es_adquirido=False,
        es_final=True,
        es_insumo=False,
        es_intermedio=False,
        id_tipoDeProducto=familia_id
    )
    session.add(producto)
    session.commit()
    print(f"✅ Producto creado: {producto.nombre} (ID: {producto.id})")
else:
    print(f"📌 Producto existente: {producto.nombre} (ID: {producto.id})")
producto_id = producto.id

# 4. Crear HolonRuta
holon = session.query(HolonRuta).first()
if not holon:
    holon = HolonRuta(
        producto_id=producto_id,
        fechaModelo="2024-01-01",
        nombreRuta="Ruta Principal",
        id_tipoRuta=patron_id
    )
    session.add(holon)
    session.commit()
    print(f"✅ HolonRuta creado (ID: {holon.id})")
else:
    print(f"📌 HolonRuta existente (ID: {holon.id})")
holon_id = holon.id

# 5. Crear Tipos de Operación (para parámetros del motor)
operaciones = ["OrdenEn WIP", "Iniciar disp", "Dispersando", "Diluyendo", "Envasar"]
for op_nombre in operaciones:
    op = session.query(TipoDeOperacion).filter_by(nombre=op_nombre).first()
    if not op:
        op = TipoDeOperacion(nombre=op_nombre, descripcion=f"Operación: {op_nombre}")
        session.add(op)
        print(f"✅ TipoOperación creado: {op_nombre}")
session.commit()

# 6. Crear Tipo de Recurso
tipo_recurso = session.query(TipoRecurso).first()
if not tipo_recurso:
    tipo_recurso = TipoRecurso(
        nombre="Dispersador Grande",
        descripcion="Equipo de dispersión grande"
    )
    session.add(tipo_recurso)
    session.commit()
    print(f"✅ TipoRecurso creado: {tipo_recurso.nombre} (ID: {tipo_recurso.id})")
else:
    print(f"📌 TipoRecurso existente: {tipo_recurso.nombre} (ID: {tipo_recurso.id})")
tipo_recurso_id = tipo_recurso.id

# 7. Crear CapacidadTipoOperacion (parámetros de coste)
operacion_disp = session.query(TipoDeOperacion).filter_by(nombre="Dispersando").first()
if operacion_disp:
    capacidad = session.query(CapacidadTipoOperacion).filter_by(
        tipoRecurso_id=tipo_recurso_id,
        tipoOperacion_id=operacion_disp.id
    ).first()
    if not capacidad:
        capacidad = CapacidadTipoOperacion(
            tipoRecurso_id=tipo_recurso_id,
            tipoOperacion_id=operacion_disp.id,
            eficiencia_estimada=0.97,
            costo_por_hora=100.0
        )
        session.add(capacidad)
        session.commit()
        print(f"✅ Capacidad creada: {operacion_disp.nombre} - costo/hora: 100.0")
    else:
        print(f"📌 Capacidad existente para {operacion_disp.nombre}")

# 8. Crear usuario operador
usuario_operador = session.query(Usuario).filter_by(email="operador@fenix.com").first()
if not usuario_operador:
    usuario_operador = Usuario(
        nombre="Operador",
        email="operador@fenix.com",
        password_hash=generate_password_hash("123456"),
        rol="operador"
    )
    session.add(usuario_operador)
    session.commit()
    print(f"✅ Usuario operador creado: operador@fenix.com / 123456")
else:
    print(f"📌 Usuario operador ya existe")

# 9. Crear usuario admin (si no existe)
usuario_admin = session.query(Usuario).filter_by(email="admin@fenix.com").first()
if not usuario_admin:
    usuario_admin = Usuario(
        nombre="Administrador",
        email="admin@fenix.com",
        password_hash=generate_password_hash("admin123"),
        rol="admin"
    )
    session.add(usuario_admin)
    session.commit()
    print(f"✅ Usuario admin creado: admin@fenix.com / admin123")
else:
    print(f"📌 Usuario admin ya existe")

session.close()

print("\n" + "=" * 60)
print("✅ INICIALIZACIÓN COMPLETADA")
print("=" * 60)
print("\n📋 Resumen:")
print(f"   Familia ID: {familia_id}")
print(f"   Patrón ID: {patron_id}")
print(f"   Producto ID: {producto_id}")
print(f"   HolonRuta ID: {holon_id}")
print(f"   TipoRecurso ID: {tipo_recurso_id}")
print("\n🔑 Credenciales:")
print("   Operador: operador@fenix.com / 123456")
print("   Admin: admin@fenix.com / admin123")
print("\n🚀 Ahora puedes:")
print("   1. Iniciar sesión como operador")
print("   2. Crear una orden desde el dashboard")
print("=" * 60)