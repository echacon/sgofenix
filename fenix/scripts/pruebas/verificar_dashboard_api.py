# sgo/fenix/scripts/pruebas/verificar_dashboard_api.py
"""
Script de prueba para validar los endpoints del Dashboard de Operaciones en Flask.
Utiliza el test client de Flask para simular las llamadas HTTP y verificar:
1. Planificación óptima y creación de ordenes (estado pendiente).
2. Procesamiento asíncrono e inicialización de la orden.
3. Validación de invariantes físicos del SCADA (error 500/bloqueo de seguridad).
4. Compuertas de calidad automáticas (QA Gate) aprobadas y rechazadas.
5. Autocalibración EWMA al completar la orden.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Agregar raíz del proyecto al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app import app, SessionLocal
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.Producto import AsignacionRecurso, InvariantePaso, EspecificacionCalidad, CriterioAceptacionEtapa, Producto
from modelos.Recursos import Recurso
from modelos.RedPetri import RedPetri
from main import procesar_nuevas_ordenes, orquestador, motor

def test_api_dashboard():
    print("🧪 Iniciando pruebas de integración del Dashboard API de Fénix...")
    
    # Compartir motor y orquestador para el test en memoria
    app.config['MOTOR'] = motor
    app.config['ORQUESTADOR'] = orquestador
    
    # 1. Usar el test client de Flask
    client = app.test_client()
    
    # Simular inicio de sesión (el decorator @login_required busca 'usuario_id' en session)
    with client.session_transaction() as sess:
        sess['usuario_id'] = 1
        sess['usuario_rol'] = 'operador'
        
    session = SessionLocal()
    print("Database URL in app.config:", app.config['ENGINE'].url)
    print("Products count in SessionLocal:", session.query(Producto).count())
    
    # 0. Sembrar invariantes y especificaciones de calidad para la prueba en fenix.db
    asig_disp = session.query(AsignacionRecurso).filter_by(holon_ruta_id=1, etapa_ruta_id=1).first()
    if asig_disp:
        # Limpiar previos si los hay
        session.query(InvariantePaso).filter_by(asignacion_recurso_id=asig_disp.id).delete()
        # Crear invariante de temperatura max 55°C
        inv_temp = InvariantePaso(
            asignacion_recurso_id=asig_disp.id,
            parametro="Temperatura",
            valor_minimo=0.0,
            valor_maximo=55.0,
            unidad="C"
        )
        session.add(inv_temp)
        print("   🌱 Sembrado Invariante de Temperatura (max 55.0°C) para Dispersor Principal.")
        
    # Crear la especificación de calidad "Viscosidad KU" (90-100 KU)
    espec_visc = session.query(EspecificacionCalidad).filter_by(nombre="Viscosidad KU").first()
    if not espec_visc:
        espec_visc = EspecificacionCalidad(
            nombre="Viscosidad KU",
            limite_minimo=90.0,
            limite_maximo=100.0,
            valor_objetivo=95.0,
            unidad_medida="KU"
        )
        session.add(espec_visc)
        session.flush()
        print("   🌱 Sembrada Especificación de Calidad: Viscosidad KU (90-100 KU).")
        
    # Crear el criterio de aceptación para la etapa DIL (id=2) de la ruta 1 (donde ocurre el QA de laboratorio)
    crit_dil = session.query(CriterioAceptacionEtapa).filter_by(holon_ruta_id=1, etapa_ruta_id=2).first()
    if not crit_dil:
        crit_dil = CriterioAceptacionEtapa(
            holon_ruta_id=1,
            etapa_ruta_id=2,
            especificacion_id=espec_visc.id
        )
        session.add(crit_dil)
        print("   🌱 Sembrado Criterio de Aceptación para etapa DIL (Viscosidad KU).")
        
    session.commit()
    
    try:
        # ============================================================
        # 1. PRUEBA DE CREACIÓN DE ORDEN (VÍA PLANIFICADOR)
        # ============================================================
        print("\n🔍 Test 1: Creación de orden mediante Planificador...")
        
        # Producto 1: Plantilla Ruta Látex (TPL_LATEX) que sí tiene asignaciones de recursos
        plazo = (datetime.now() + timedelta(days=1)).isoformat()
        res_crear = client.post('/operador/api/crear_orden', json={
            'producto_id': 1,
            'cantidad': 1000.0,
            'plazo_entrega': plazo
        })
        
        data_crear = json.loads(res_crear.data)
        print("Status Code:", res_crear.status_code)
        print("Response Data:", data_crear)
        assert res_crear.status_code == 200
        assert data_crear['success'] is True
        orden_id = data_crear['orden_id']
        print(f"   ✅ ORDEN CREADA (OK): {data_crear['mensaje']}")
        
        # Verificar estado inicial en BD (debe ser 'pendiente')
        orden_db = session.query(OrdenProduccion).get(orden_id)
        assert orden_db.estado == 'pendiente'
        print("   ✅ ESTADO INICIAL (OK): La orden se insertó en estado 'pendiente'.")
        
        # ============================================================
        # 2. PRUEBA DE PROCESAMIENTO ASÍNCRONO (INICIALIZACIÓN DAEMON)
        # ============================================================
        print("\n🔍 Test 2: Inicialización asíncrona del orquestador...")
        
        # Simular ciclo del daemon main.py
        procesar_nuevas_ordenes()
        
        # Recargar orden y verificar estado (debe ser 'en_produccion')
        session.refresh(orden_db)
        assert orden_db.estado == 'en_produccion'
        print("   ✅ ORDEN INICIALIZADA (OK): Daemon cambió estado a 'en_produccion'.")
        
        # Verificar que la Red Petri fue cargada en el motor y en la BD
        instancia_bd = session.query(InstanciaRed).filter_by(orden_id=orden_id, activa=True).first()
        assert instancia_bd is not None
        print(f"   ✅ INSTANCIA RED (OK): Creada red de tipo '{instancia_bd.tipo}' (ID BD: {instancia_bd.id}).")
        
        # Comprobar la Composición Selectiva (Poda de Molienda)
        marcado = instancia_bd.marcado if isinstance(instancia_bd.marcado, dict) else json.loads(instancia_bd.marcado)
        lugares_activos = [k for k, v in marcado.items() if v > 0]
        print(f"   ✅ MARCADO INICIAL (OK): Token en lugar '{lugares_activos[0]}'.")
        
        # ============================================================
        # 3. PRUEBA DE INVARIANTES FÍSICOS (BLOQUEO DE SEGURIDAD SCADA)
        # ============================================================
        print("\n🔍 Test 3: Simulación de telemetría y chequeo de invariantes...")
        
        # Forzar marcado de token al lugar de dispersión 'p7' para probar el invariante
        instancia_mem = None
        for inst in motor.instancias.values():
            if inst.instancia_bd_id == instancia_bd.id:
                instancia_mem = inst
                break
                
        print("   Forzando marcado al lugar 'p5' para habilitar dispersión...")
        for pid in list(instancia_mem.marcado.keys()):
            instancia_mem.marcado[pid] = 0
        instancia_mem.marcado['p5'] = 1
        instancia_bd.marcado = json.dumps(instancia_mem.marcado)
        session.commit()

        # Obtener las transiciones habilitadas para la instancia
        res_trans = client.get(f'/operador/api/instancia/{instancia_bd.id}/transiciones')
        data_trans = json.loads(res_trans.data)
        assert res_trans.status_code == 200
        transiciones = data_trans['transiciones']
        assert len(transiciones) > 0
        
        # Usamos la transición t7 (Chequeo)
        trans_id = 't7'
        trans_nombre = 'Chequeo'
        print(f"   Transición a probar: '{trans_nombre}' (ID: {trans_id})")
        
        # 3.1. Caso Fallido: Enviar temperatura de 60.0°C (El dispersor DISP_PRIN_01 tiene límite de 55°C)
        res_disp_err = client.post('/operador/api/disparar', json={
            'instancia_id': instancia_bd.id,
            'transicion_id': trans_id,
            'invariantes': {
                'Temperatura': 60.0,
                'Velocidad': 800
            }
        })
        data_disp_err = json.loads(res_disp_err.data)
        print("Response Disparo Fallido:", data_disp_err)
        assert data_disp_err['success'] is False
        assert "⚠️ ALERTA DE SEGURIDAD FÍSICA" in data_disp_err['mensaje']
        print(f"   ✅ BLOQUEO DE INVARIANTE (OK): Avance bloqueado. Mensaje: {data_disp_err['mensaje']}")
        
        # 3.2. Caso Exitoso: Enviar temperatura correcta de 51.5°C
        res_disp_ok = client.post('/operador/api/disparar', json={
            'instancia_id': instancia_bd.id,
            'transicion_id': trans_id,
            'invariantes': {
                'Temperatura': 51.5,
                'Velocidad': 850
            }
        })
        data_disp_ok = json.loads(res_disp_ok.data)
        assert data_disp_ok['success'] is True
        print(f"   ✅ DISPARO EXITOSO (OK): {data_disp_ok['mensaje']}")
        
        # ============================================================
        # 4. PRUEBA DE COMPUERTA DE CALIDAD AUTOMÁTICA
        # ============================================================
        print("\n🔍 Test 4: Compuertas de calidad automáticas (laboratorio)...")
        
        # Buscamos la instancia activa de dilución
        instancia_qc_bd = session.query(InstanciaRed).filter_by(
            orden_id=orden_id, 
            tipo='DIS_DIL_dilucion', 
            activa=True
        ).first()
        assert instancia_qc_bd is not None
        
        instancia_qc_mem = None
        for inst in motor.instancias.values():
            if inst.instancia_bd_id == instancia_qc_bd.id:
                instancia_qc_mem = inst
                break
        
        assert instancia_qc_mem is not None
        
        # Forzar marcado de token al lugar de calidad 'p10' ('Chequeando lab') en la red de dilución
        lugar_qc = 'p10'
        print(f"   Forzando marcado al lugar de control de calidad: '{lugar_qc}' en red {instancia_qc_bd.tipo}")
        for pid in list(instancia_qc_mem.marcado.keys()):
            instancia_qc_mem.marcado[pid] = 0
        instancia_qc_mem.marcado[lugar_qc] = 1
        instancia_qc_bd.marcado = json.dumps(instancia_qc_mem.marcado)
        session.commit()
        
        # 4.1. Laboratorio reporta viscosidad rechazada: 75 KU (límite 90 - 100 KU)
        res_qc_err = client.post('/operador/api/control_calidad', json={
            'instancia_id': instancia_qc_bd.id,
            'mediciones_qc': {
                'Viscosidad KU': 75.0
            }
        })
        data_qc_err = json.loads(res_qc_err.data)
        assert data_qc_err['success'] is True
        assert data_qc_err['aprobado'] is False
        print(f"   ✅ CALIDAD RECHAZADA (OK): Lote enviado a reproceso. Mensaje: {data_qc_err['mensaje']}")
        
        # Volver a mover al lugar de calidad para probar aprobación
        for pid in list(instancia_qc_mem.marcado.keys()):
            instancia_qc_mem.marcado[pid] = 0
        instancia_qc_mem.marcado[lugar_qc] = 1
        instancia_qc_bd.marcado = json.dumps(instancia_qc_mem.marcado)
        session.commit()
        
        # 4.2. Laboratorio reporta viscosidad aprobada: 96 KU
        res_qc_ok = client.post('/operador/api/control_calidad', json={
            'instancia_id': instancia_qc_bd.id,
            'mediciones_qc': {
                'Viscosidad KU': 96.0
            }
        })
        data_qc_ok = json.loads(res_qc_ok.data)
        assert data_qc_ok['success'] is True
        assert data_qc_ok['aprobado'] is True
        print(f"   ✅ CALIDAD APROBADA (OK): Lote aprobado para descarga. Mensaje: {data_qc_ok['mensaje']}")
            
        # ============================================================
        # 5. PRUEBA DE BUCLE DE APRENDIZAJE EWMA
        # ============================================================
        print("\n🔍 Test 5: Verificación del bucle de aprendizaje EWMA...")
        
        # Forzar la finalización de la orden
        orden_db.estado = 'completada'
        session.commit()
        
        # Ejecutar aprendizaje de forma síncrona para verificar que recalibra
        r_disp = session.query(Recurso).filter_by(codigo="DISP_PRIN_01").first()
        asig_disp_rec = session.query(AsignacionRecurso).filter_by(recurso_id=r_disp.id, holon_ruta_id=1).first()
        # Resetear eficiencia a 1.0 para que el test sea determinista
        asig_disp_rec.eficiencia_real = 1.0
        session.commit()
        
        # Simular algunos logs en evento_red para el cálculo de aprendizaje
        from modelos.ProcesoOcurrente import EventoRed
        log_evento = EventoRed(
            orden_id=orden_id,
            instancia_id=instancia_bd.id,
            transicion_nombre="Carga completada",
            timestamp=datetime.now(),
            invariantes={
                'tipo': 'externo',
                'recurso': r_disp.nombre,
                'duracion_min': 45.0  # Duró 45 min, nominal era 30 min (eficiencia obs = 0.66)
            },
            costo_real_paso=10.0
        )
        session.add(log_evento)
        session.commit()
        
        # Ejecutar
        orquestador.session = session
        orquestador.ejecutar_aprendizaje_orden(orden_id)
        
        # Recargar asignación y verificar eficiencia recalibrada
        session.refresh(asig_disp_rec)
        # Eficiencia nominal = 1.0. Obs1 = 45 / 0 = clamped to 1.5. EWMA = 1.10.
        # Obs2 = 45 / 45 = 1.0. EWMA = 0.2 * 1.0 + 0.8 * 1.10 = 1.08.
        assert asig_disp_rec.eficiencia_real is not None
        assert abs(asig_disp_rec.eficiencia_real - 1.08) < 0.02
        print(f"   ✅ APRENDIZAJE EWMA (OK): La eficiencia real del Dispersor Principal se autocalibró a {asig_disp_rec.eficiencia_real:.3f}")
        
        print("\n🎉 ¡Todos los tests del Dashboard API y control en lazo cerrado pasaron con éxito!")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_api_dashboard()
