#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN

engine = create_engine('sqlite:///fenix.db')
Session = sessionmaker(bind=engine)
session = Session()
motor = MotorABTPPN()
orquestador = Orquestador(motor, session)

# Cargar redes en el motor primero
from servicios.orquestador import Orquestador
# (Reutilizamos la función de main.py)
def cargar_redes():
    from modelos.RedPetri import RedPetri
    redes_bd = session.query(RedPetri).filter_by(activo=True).all()
    for red in redes_bd:
        red_mem = orquestador.cargar_red_desde_bd(red.nombre)
        if red_mem and red.nombre not in motor.redes_cargadas:
            motor.redes_cargadas[red.nombre] = red_mem
            print(f"   ✅ Red cargada: {red.nombre}")

cargar_redes()

orden_id = 1  # Cambia si es otro
exito = orquestador.inicializar_orden(orden_id)
if exito:
    print(f"✅ Orden {orden_id} inicializada correctamente")
else:
    print(f"❌ Falló la inicialización de la orden {orden_id}")

session.close()