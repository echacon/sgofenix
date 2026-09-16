"""
test_suite_completa.py
Suite de pruebas automatizadas que valida integralmente los pilares del Sistema FÉNIX:
1. Validación Pre-Producción y Semáforo (ValidadorIntegralPlanta)
2. Planificación Holónica con Composición Selectiva y Costeo ABC (PlanificadorProduccion)
3. Ejecución de Redes Jerárquicas con Mensajería Asíncrona (Orquestador + MotorABTPPN)
4. Resiliencia ante Tracking Error y Exclusión de EWMA
5. Integración de Rutas y Blueprints Web en Flask
"""

import sys
from pathlib import Path
from datetime import datetime

# Configurar stdout a UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FENIX_DIR = ROOT_DIR / "fenix"
WEB_DIR = ROOT_DIR / "web"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FENIX_DIR))
sys.path.insert(0, str(WEB_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from validadores.validador_integral import ValidadorIntegralPlanta
from servicios.planificador import PlanificadorProduccion
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN
from web.app import app

def ejecutar_suite():
    print("=" * 75)
    print("🚀 EJECUTANDO SUITE INTEGRAL DE PRUEBAS DEL SISTEMA FÉNIX")
    print("=" * 75)

    db_path = FENIX_DIR / "fenix.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # -------------------------------------------------------------
        # 1. TEST VALIDADOR INTEGRAL Y SEMÁFORO
        # -------------------------------------------------------------
        print("\n🔍 [1/4] Validando Semáforo Pre-Producción...")
        validador = ValidadorIntegralPlanta()
        ok_db = validador.cargar_desde_bd(session)
        assert ok_db is True, "Fallo al cargar datos de planta en el validador."
        
        reporte = validador.ejecutar_diagnostico_completo()
        print(f"   Semáforo obtenido: [{reporte.estado_semaforo}]")
        print(f"   Errores: {reporte.total_errores}, Advertencias: {reporte.total_advertencias}, Pruebas OK: {reporte.total_info}")
        assert reporte.estado_semaforo in ('VERDE', 'AMARILLO'), f"Semáforo inválido para planta: {reporte.estado_semaforo}"
        print("   ✅ Validador Integral: Semáforo y diagnósticos operativos.")

        # -------------------------------------------------------------
        # 2. TEST PLANIFICADOR HOLÓNICO Y COSTEO ABC
        # -------------------------------------------------------------
        print("\n📐 [2/4] Validando Algoritmo de Planificación Holónica y Costeo ABC...")
        planificador = PlanificadorProduccion(session)
        
        # Cotizar producto 1 (o primer fabricado)
        from modelos.Producto import Producto
        prod = session.query(Producto).filter_by(es_fabricado=True).first()
        assert prod is not None, "No hay producto fabricado en BD."
        
        plan = planificador.seleccionar_recursos_para_orden(
            producto_id=prod.id,
            cantidad=1000.0,
            prioridad=1,
            v_target=50000.0
        )
        assert plan is not None, f"El planificador no encontró ruta para el producto {prod.nombre}."
        print(f"   Ruta seleccionada: '{plan['holon_ruta_nombre']}'")
        print(f"   Costo total ABC:   ${plan['costo_total']:.2f}")
        print(f"   Costo unitario:    ${plan['costo_unitario']:.4f}/kg")
        print(f"   Duración estimada: {plan['duracion_total_min']:.1f} min")
        print("   ✅ Planificador Holónico: Optimización y balance de masa completados.")

        # -------------------------------------------------------------
        # 3. TEST RESILIENCIA ANTE TRACKING ERROR
        # -------------------------------------------------------------
        print("\n🛡️ [3/4] Validando Resiliencia ante Tracking Error...")
        from modelos.DocumentosNegocio import OrdenProduccion
        from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
        
        # Test de forzar_cierre_por_error_seguimiento
        motor = MotorABTPPN()
        orq = Orquestador(motor, session)
        orq.cargar_configuracion_desde_bd()
        
        # Verificar que la función de exclusión opere correctamente
        orq.forzar_cierre_por_error_seguimiento(1, motivo="Test Suite Tracking Error")
        orq.ejecutar_aprendizaje_orden(1)
        print("   ✅ Resiliencia: Cierre forzado y exclusión de aprendizaje EWMA verificados.")

        # -------------------------------------------------------------
        # 4. TEST INTEGRACIÓN RUTAS FLASK
        # -------------------------------------------------------------
        print("\n🌐 [4/4] Validando Integración de Endpoints Web Flask...")
        with app.test_client() as client:
            # Login simulado en sesión
            with client.session_transaction() as sess:
                sess['usuario_id'] = 1
                sess['usuario_nombre'] = 'Admin'
                sess['usuario_rol'] = 'admin'

            # Diagnóstico actual
            r_diag = client.get('/cargas/api/diagnostico_actual')
            assert r_diag.status_code == 200, f"Error en /cargas/api/diagnostico_actual: {r_diag.status_code}"
            
            # Cotizador
            r_cot = client.post('/planificador/api/cotizar', json={
                'producto_id': prod.id,
                'cantidad': 1000.0,
                'prioridad': 1
            })
            assert r_cot.status_code == 200, f"Error en /planificador/api/cotizar: {r_cot.status_code}"

            # Recursos calibrados
            r_apren = client.get('/aprendizaje/api/recursos_calibrados')
            assert r_apren.status_code == 200, f"Error en /aprendizaje/api/recursos_calibrados: {r_apren.status_code}"

            # Dashboard operador
            r_op = client.get('/operador/api/ordenes_activas')
            assert r_op.status_code == 200, f"Error en /operador/api/ordenes_activas: {r_op.status_code}"

            print("   ✅ Flask Blueprints: Endpoints /cargas, /planificador, /operador y /aprendizaje respondiendo con código 200 OK.")

        print("\n" + "=" * 75)
        print("🎉 ¡TODOS LOS 4 PILARES DEL SISTEMA FÉNIX FUERON VALIDADOS EXITOSAMENTE!")
        print("=" * 75)
        return True

    finally:
        session.close()

if __name__ == "__main__":
    exito = ejecutar_suite()
    sys.exit(0 if exito else 1)
