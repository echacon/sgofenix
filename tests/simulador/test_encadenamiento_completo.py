"""
test_encadenamiento_completo.py
Verifica la evolución simultánea de las redes hijas (DIS_DIL_dispersion, DIS_DIL_dilucion)
y la red integradora (DIS_DIL_integradora) mediante el paso y consumo de mensajes inter-redes.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configurar stdout a UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FENIX_DIR = ROOT_DIR / "fenix"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FENIX_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.RedPetri import RedPetri
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.MensajePendiente import MensajePendiente
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.Producto import HolonRuta, Producto
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from servicios.orquestador import Orquestador

def test_encadenamiento_completo():
    print("=" * 70)
    print("TEST DE ENCADENAMIENTO JERARQUICO (HIJAS + INTEGRADORA)")
    print("=" * 70)

    db_path = FENIX_DIR / "fenix.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Limpiar estado previo de orden 1
        session.query(MensajePendiente).filter_by(orden_id=1).delete()
        session.query(EventoRed).filter_by(orden_id=1).delete()
        session.query(InstanciaRed).filter_by(orden_id=1).delete()
        
        orden = session.query(OrdenProduccion).get(1)
        if not orden:
            print("❌ No se encontró la Orden ID 1 en BD.")
            return False
            
        orden.estado = 'pendiente'
        orden.fecha_inicio = None
        orden.fecha_fin = None
        session.commit()

        # 2. Inicializar motor y orquestador
        motor = MotorABTPPN()
        orquestador = Orquestador(motor, session)
        ok_cfg = orquestador.cargar_configuracion_desde_bd()
        assert ok_cfg is True, "No se pudo cargar la configuración de encadenamiento."

        # Cargar redes
        for r in session.query(RedPetri).filter_by(activo=True).all():
            orquestador.cargar_red_desde_bd(r.nombre)

        # 3. Inicializar orden (crea las 3 instancias: dispersion, dilucion, integradora)
        ok_init = orquestador.inicializar_orden(1)
        assert ok_init is True, "Fallo al inicializar la orden 1."

        # Validar marcado inicial de las 3 redes
        inst_disp = next((i for i in motor.instancias.values() if "dispersion" in i.red_nombre.lower()), None)
        inst_dil = next((i for i in motor.instancias.values() if "dilucion" in i.red_nombre.lower()), None)
        inst_int = next((i for i in motor.instancias.values() if "integradora" in i.red_nombre.lower()), None)

        assert inst_disp is not None, "Instancia dispersión no creada."
        assert inst_dil is not None, "Instancia dilución no creada."
        assert inst_int is not None, "Instancia integradora no creada."

        print(f"OK - Redes instanciadas:")
        print(f"   - Dispersion ({inst_disp.red_nombre}): {inst_disp.marcado}")
        print(f"   - Dilucion ({inst_dil.red_nombre}): {inst_dil.marcado}")
        print(f"   - Integradora ({inst_int.red_nombre}): {inst_int.marcado}")

        # 4. Cargar fixture de eventos
        fixture_path = ROOT_DIR / "tests" / "fixtures" / "eventos_exito.json"
        with open(fixture_path, 'r', encoding='utf-8') as f:
            datos_fixture = json.load(f)
        eventos = datos_fixture.get("eventos", [])

        # 5. Ejecutar secuencia completa
        for idx, ev in enumerate(eventos, 1):
            ts = datetime.fromisoformat(ev['timestamp']) if 'timestamp' in ev else datetime.now()
            res = orquestador.procesar_evento_planta(
                orden_id=1,
                red_nombre=ev['red'],
                evento_nombre=ev['transicion'],
                recurso_nombre=ev.get('recurso'),
                timestamp=ts
            )
            assert res is True, f"Fallo al procesar evento {idx}: {ev['red']}.{ev['transicion']}"

        # 6. Verificación final de la orden y redes
        session.refresh(orden)
        print("\n" + "=" * 70)
        print("RESULTADOS FINALES DE LA EVOLUCION")
        print("=" * 70)
        print(f"Estado final de la Orden 1: {orden.estado.upper()}")
        print(f"Marcado final Dispersion:  {inst_disp.marcado}")
        print(f"Marcado final Dilucion:    {inst_dil.marcado}")
        print(f"Marcado final Integradora: {inst_int.marcado}")

        assert orden.estado == 'completada', f"La orden debió finalizar en 'completada', pero está en '{orden.estado}'"
        assert inst_disp.completada is True, "La red de dispersión debió completarse."
        assert inst_dil.completada is True, "La red de dilución debió completarse."
        assert inst_int.completada is True, "La red integradora debió completarse."
        assert "p6" in inst_int.marcado, "La red integradora debió alcanzar el lugar p6 ('Orden completada')."

        # Verificar que no queden mensajes pendientes sin consumir
        pendientes = session.query(MensajePendiente).filter_by(orden_id=1, consumido=False).count()
        assert pendientes == 0, f"Quedaron {pendientes} mensajes pendientes sin procesar."

        print("\n>>> TODAS LAS PRUEBAS DE ENCADENAMIENTO INTER-REDES PASARON CON EXITO! <<<")
        return True

    finally:
        session.close()

if __name__ == "__main__":
    exito = test_encadenamiento_completo()
    sys.exit(0 if exito else 1)
