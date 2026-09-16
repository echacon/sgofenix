"""
test_resiliencia_tracking.py
Verifica la resiliencia ante pérdida de eventos intermedios (Tracking Error).
Asegura que el cierre forzado marque 'error_seguimiento' y excluya la orden
del bucle de aprendizaje EWMA para preservar la integridad estadística.
"""

import sys
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
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.Producto import HolonRuta, AsignacionRecurso
from utils.motor_abtppn import MotorABTPPN
from servicios.orquestador import Orquestador

def test_resiliencia_tracking_error():
    print("=" * 70)
    print("🧪 TEST DE RESILIENCIA ANTE PÉRDIDA DE EVENTOS (TRACKING ERROR)")
    print("=" * 70)

    db_path = FENIX_DIR / "fenix.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Resetear orden 1
        session.query(EventoRed).filter_by(orden_id=1).delete()
        session.query(InstanciaRed).filter_by(orden_id=1).delete()
        
        orden = session.query(OrdenProduccion).get(1)
        orden.estado = 'pendiente'
        session.commit()

        motor = MotorABTPPN()
        orquestador = Orquestador(motor, session)
        orquestador.cargar_configuracion_desde_bd()
        
        for r in session.query(RedPetri).filter_by(activo=True).all():
            orquestador.cargar_red_desde_bd(r.nombre)
            
        # 2. Inicializar orden
        orquestador.inicializar_orden(1)

        # 3. Guardar eficiencia inicial de los recursos de la ruta
        asigs_iniciales = {
            a.recurso_id: a.eficiencia_real 
            for a in session.query(AsignacionRecurso).filter_by(holon_ruta_id=orden.holon_ruta_id).all()
        }

        # 4. Simular solo el primer evento y luego pérdida de todos los intermedios
        orquestador.procesar_evento_planta(
            orden_id=1,
            red_nombre="DIS_DIL_dispersion",
            evento_nombre="Asignar equipo",
            recurso_nombre="DISP_SEC_01",
            timestamp=datetime.now()
        )

        print("📡 Simulando pérdida de eventos intermedios (salto directo a evento Fin)...")

        # 5. Aplicar cierre forzado por error de seguimiento al llegar el evento final
        orquestador.forzar_cierre_por_error_seguimiento(1, motivo="Salto de telemetría: eventos 2 al 23 no recibidos")

        # 6. Intentar ejecutar el aprendizaje
        orquestador.ejecutar_aprendizaje_orden(1)

        # 7. Validaciones
        session.refresh(orden)
        instancias = session.query(InstanciaRed).filter_by(orden_id=1).all()

        assert orden.estado == 'completada', f"Estado de orden incorrecto: {orden.estado}"
        assert all(i.completada is True for i in instancias), "Todas las instancias debieron marcarse completadas."
        assert all(i.tipo_terminacion == 'error_seguimiento' for i in instancias), "El tipo de terminación debe ser 'error_seguimiento'."

        # Comprobar que las eficiencias no se modificaron
        for a in session.query(AsignacionRecurso).filter_by(holon_ruta_id=orden.holon_ruta_id).all():
            ef_ini = asigs_iniciales.get(a.recurso_id)
            assert a.eficiencia_real == ef_ini, f"La eficiencia del recurso {a.recurso_id} cambió indebidamente ({ef_ini} -> {a.eficiencia_real})"

        print("✅ Instancias cerradas correctamente con 'error_seguimiento'.")
        print("✅ Bucle EWMA excluyó la orden: Parámetros y eficiencias de recursos preservados intactos.")
        print("\n🎉 ¡TEST DE RESILIENCIA ANTE TRACKING ERROR COMPLETADO CON ÉXITO!")
        return True

    finally:
        session.close()

if __name__ == "__main__":
    exito = test_resiliencia_tracking_error()
    sys.exit(0 if exito else 1)
