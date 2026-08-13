# scripts/diagnosticar_instancias.py
"""Diagnostica las instancias en memoria después de crear la orden"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed

print("=" * 60)
print("🔍 DIAGNÓSTICO DE INSTANCIAS")
print("=" * 60)

engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)
session = Session()

# 1. Ver órdenes existentes
print("\n📋 ÓRDENES EN BD:")
ordenes = session.query(OrdenProduccion).order_by(OrdenProduccion.id.desc()).limit(5).all()
for orden in ordenes:
    print(f"   ID: {orden.id} - Estado: {orden.estado} - Número: {orden.numero_orden}")

# 2. Ver instancias de la última orden
if ordenes:
    ultima_orden = ordenes[0]
    print(f"\n📊 INSTANCIAS de orden {ultima_orden.id}:")
    
    instancias = session.query(InstanciaRed).filter_by(orden_id=ultima_orden.id).all()
    for inst in instancias:
        print(f"   ID: {inst.id} - Tipo: {inst.tipo} - Activa: {inst.activa}")
        print(f"      Patrón Ruta ID: {inst.patron_ruta_id}")
        print(f"      Marcado: {inst.marcado}")

# 3. Verificar conexión con motor
print("\n🔧 INICIALIZANDO MOTOR...")
from utils.motor_abtppn_backup import MotorABTPPN
from servicios.orquestador_backup import Orquestador

motor = MotorABTPPN()
orquestador = Orquestador(motor, session)

print(f"\n📊 INSTANCIAS EN MEMORIA DEL MOTOR:")
print(f"   Total: {len(motor.instancias)}")

for inst_id, inst in motor.instancias.items():
    print(f"\n   Instancia ID: {inst_id}")
    print(f"   Orden ID: {inst.orden_id}")
    print(f"   Red: {inst.red.nombre}")
    print(f"   Activa: {inst.activa}")
    print(f"   BD ID: {inst.instancia_bd_id}")

# 4. Probar búsqueda
if ordenes:
    ultima_orden = ordenes[0]
    print(f"\n🔍 PROBANDO BÚSQUEDA para orden {ultima_orden.id}:")
    
    redes_a_buscar = [
        "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
        "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
        "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2"
    ]
    
    for red_nombre in redes_a_buscar:
        encontrada = False
        for mem_id, inst in motor.instancias.items():
            if inst.orden_id == ultima_orden.id and inst.red.nombre == red_nombre:
                print(f"   ✅ {red_nombre} -> instancia {mem_id}")
                encontrada = True
                break
        if not encontrada:
            print(f"   ❌ {red_nombre} -> NO encontrada")

session.close()
print("\n" + "=" * 60)