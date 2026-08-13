# resetear_orden.py
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente
from modelos.DocumentosNegocio import OrdenProduccion
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN

engine = create_engine("sqlite:///fenix.db")
Session = sessionmaker(bind=engine)
session = Session()

# 1. Limpiar eventos, mensajes e instancias de la orden
orden_id = 1

print(f"🔄 Reseteando orden {orden_id}...")

# Eliminar eventos
eventos = session.query(EventoRed).filter_by(orden_id=orden_id).delete()
print(f"   ✅ Eliminados {eventos} eventos")

# Eliminar mensajes pendientes
mensajes = session.query(MensajePendiente).filter_by(orden_id=orden_id).delete()
print(f"   ✅ Eliminados {mensajes} mensajes")

# Eliminar instancias
instancias = session.query(InstanciaRed).filter_by(orden_id=orden_id).delete()
print(f"   ✅ Eliminadas {instancias} instancias")

# Cambiar estado de la orden a pendiente
orden = session.query(OrdenProduccion).get(orden_id)
orden.estado = 'pendiente'
orden.fecha_inicio = None
orden.fecha_fin = None
print(f"   ✅ Orden cambiada a estado 'pendiente'")

session.commit()

# 2. Recrear las instancias desde cero
motor = MotorABTPPN()
orquestador = Orquestador(motor, session)
orquestador.cargar_configuracion_desde_bd()

# Cargar redes
from modelos.RedPetri import RedPetri
redes = session.query(RedPetri).filter_by(activo=True).all()
for red in redes:
    red_mem = orquestador.cargar_red_desde_bd(red.nombre)
    if red_mem:
        motor.redes_cargadas[red.nombre] = red_mem

# Inicializar orden
if orquestador.inicializar_orden(orden_id):
    print(f"\n✅ Orden {orden_id} reinicializada correctamente")
else:
    print(f"\n❌ Error al reinicializar orden")

session.close()