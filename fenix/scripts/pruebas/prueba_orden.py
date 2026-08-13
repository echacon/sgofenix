# prueba_orden.py - Versión corregida
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from modelos.RedPetri import RedPetri
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from datetime import datetime

print("=" * 60)
print("🚀 INICIANDO PRUEBA DE ORDEN")
print("=" * 60)

# Conectar a BD
engine = create_engine("sqlite:///fenix.db")
Session = sessionmaker(bind=engine)
session = Session()

# Crear motor y orquestador
motor = MotorABTPPN()
orquestador = Orquestador(motor, session)

# Cargar configuración de encadenamiento
orquestador.cargar_configuracion_desde_bd()

# Cargar todas las redes PNML desde BD al motor
print("\n📄 Cargando redes desde BD...")
redes = session.query(RedPetri).filter_by(activo=True).all()
nombre_redes = {}
for red in redes:
    red_mem = orquestador.cargar_red_desde_bd(red.nombre)
    if red_mem:
        motor.redes_cargadas[red.nombre] = red_mem
        print(f"   ✅ {red.nombre}")
        # Crear un alias corto para referencia
        if 'dispersion' in red.nombre.lower():
            nombre_redes['dispersion'] = red.nombre
        elif 'dilucion' in red.nombre.lower():
            nombre_redes['dilucion'] = red.nombre
        elif 'integradora' in red.nombre.lower() or 'integracion' in red.nombre.lower():
            nombre_redes['integradora'] = red.nombre

print(f"\n📌 Alias: {nombre_redes}")

# Verificar estado de la orden
orden = session.query(OrdenProduccion).get(1)
print(f"\n📋 Orden ID 1: estado={orden.estado}")

# Recuperar instancias existentes en el motor
print("\n🔄 Recuperando instancias existentes...")
instancias_bd = session.query(InstanciaRed).filter_by(orden_id=1, activa=True).all()

for inst_bd in instancias_bd:
    # Cargar red
    red_mem = motor.redes_cargadas.get(inst_bd.tipo)
    if not red_mem:
        red_mem = orquestador.cargar_red_desde_bd(inst_bd.tipo)
        if red_mem:
            motor.redes_cargadas[inst_bd.tipo] = red_mem
    
    # Reconstruir token
    token = TokenColoreado(
        orden_id=inst_bd.token_o,
        material=inst_bd.token_m,
        coste=inst_bd.token_c,
        timestamp=inst_bd.token_t or datetime.now()
    )
    
    # Crear instancia en motor
    inst_mem_id = motor.crear_instancia(
        red_nombre=inst_bd.tipo,
        orden_id=orden.id,
        token_inicial=token,
        marcado_inicial=inst_bd.marcado,
        pnml_path=None
    )
    motor.actualizar_instancia_bd_id(inst_mem_id, inst_bd.id)
    print(f"   ✅ Recuperada: {inst_bd.tipo}")

# Procesar eventos usando los nombres completos
print("\n" + "=" * 60)
print("📱 PROCESANDO EVENTOS")
print("=" * 60)

eventos = [
    ("Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", "Asignar equipo", "DISP_SEC_01"),
    ("Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", "Cargar auto", "DISP_SEC_01"),
    ("Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1", "Fin solidos", "DISP_SEC_01"),
]

for red_nombre, transicion, recurso in eventos:
    print(f"\n📱 Evento: {red_nombre}.{transicion}")
    
    resultado = orquestador.procesar_evento_planta(
        orden_id=1,
        red_nombre=red_nombre,
        evento_nombre=transicion,
        recurso_id=recurso,
        timestamp=datetime.now()
    )
    
    if resultado:
        print(f"   ✅ Procesado")
        # Procesar handshakes
        orquestador.procesar_mensajes_pendientes(1)
    else:
        print(f"   ❌ Falló")

# Verificar estado final
print("\n" + "=" * 60)
print("📊 ESTADO FINAL")
print("=" * 60)

instancias = session.query(InstanciaRed).filter_by(orden_id=1).all()
for inst in instancias:
    print(f"\n📊 {inst.tipo}:")
    print(f"   Marcado: {inst.marcado}")
    print(f"   Token: {inst.token_m:.2f} kg, ${inst.token_c:.2f}")

session.close()
print("\n✅ Prueba completada")