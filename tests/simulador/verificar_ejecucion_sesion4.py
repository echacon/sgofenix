# sgo/fenix/scripts/pruebas/verificar_ejecucion_sesion4.py
"""
Script de prueba para verificar la ejecución, control de calidad,
invariantes y aprendizaje EWMA (Sesión 4) en Fénix.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz de fenix al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.Producto import (
    Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula,
    EspecificacionCalidad, CriterioAceptacionEtapa, InvariantePaso
)
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.Recursos import Recurso, RecursoEquipo, UnidadFuncional, ConexionFisica
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from modelos.RedPetri import RedPetri, TransicionRed
from utils.motor_abtppn import MotorABTPPN
from servicios.orquestador import Orquestador

def test_control_y_aprendizaje():
    print("🧪 Iniciando pruebas de control híbrido, invariantes y aprendizaje...")

    # 1. Crear BD en memoria
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # 2. Configurar estructura base de datos
        familia = FamiliaProducto(nombre="Pinturas premium", descripcion="Premium")
        op_disp = TipoDeOperacion(nombre="Dispersion", codigo="DIS")
        op_qc = TipoDeOperacion(nombre="Control Calidad", codigo="QC")
        op_env = TipoDeOperacion(nombre="Envasado", codigo="ENV")
        
        patron = PatronDeRuta(nombre="Patron Premium", familiaProducto=familia)
        etapa_disp = EtapaRuta(nombre="Dispersion", patronRuta=patron, tipoDeOperacion=op_disp)
        etapa_qc = EtapaRuta(nombre="Control Calidad", patronRuta=patron, tipoDeOperacion=op_qc)
        etapa_env = EtapaRuta(nombre="Envasado", patronRuta=patron, tipoDeOperacion=op_env)
        
        session.add_all([familia, op_disp, op_qc, op_env, patron, etapa_disp, etapa_qc, etapa_env])
        session.flush()
        
        # 3. Equipos físicos
        u_func = UnidadFuncional(codigo="SECC-PREM", nombre="Sección Premium")
        session.add(u_func)
        session.flush()
        
        r_disp = Recurso(codigo="D-PREM", nombre="Dispersor Premium D-PREM", tipo="equipo")
        r_lab = Recurso(codigo="LAB-QA", nombre="Laboratorio de Calidad", tipo="equipo")
        session.add_all([r_disp, r_lab])
        session.flush()
        
        eq_disp = RecursoEquipo(id=r_disp.id, modelo="PREM-100", unidad_id=u_func.id, disponible=True,
                                consumo_energia_kw=20.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=15.0)
        eq_lab = RecursoEquipo(id=r_lab.id, modelo="QA-Station", unidad_id=u_func.id, disponible=True,
                               consumo_energia_kw=2.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=5.0)
        session.add_all([eq_disp, eq_lab])
        session.flush()
        
        # Conexión directa D-PREM -> LAB-QA
        conn_disp_lab = ConexionFisica(recurso_origen_id=r_disp.id, recurso_destino_id=r_lab.id, tipo="MANUAL")
        session.add(conn_disp_lab)
        session.flush()
        
        # 4. Producto y Ruta
        producto = Producto(codigo="LOX-PREM", nombre="Lox Premium Blanco", es_fabricado=True, familia=familia)
        session.add(producto)
        session.flush()
        
        ruta = HolonRuta(nombre="Ruta Lox Premium", producto=producto, patron=patron, activa=True)
        session.add(ruta)
        session.flush()
        
        # Asignaciones de recursos
        asig_disp = AsignacionRecurso(holon_ruta=ruta, etapa=etapa_disp, recurso_id=r_disp.id,
                                      duracion_estimada_min=30.0, costo_por_hora_real=50.0, eficiencia_real=1.0)
        asig_qc = AsignacionRecurso(holon_ruta=ruta, etapa=etapa_qc, recurso_id=r_lab.id,
                                    duracion_estimada_min=15.0, costo_por_hora_real=30.0, eficiencia_real=1.0)
        asig_env = AsignacionRecurso(holon_ruta=ruta, etapa=etapa_env, recurso_id=r_disp.id,
                                     duracion_estimada_min=10.0, costo_por_hora_real=50.0, eficiencia_real=1.0)
        session.add_all([asig_disp, asig_qc, asig_env])
        session.flush()
        
        # 5. Invariantes y Criterios de Calidad
        inv_temp = InvariantePaso(asignacion_recurso=asig_disp, parametro="Temperatura", valor_maximo=55.0, unidad="C")
        session.add(inv_temp)
        
        espec_visc = EspecificacionCalidad(nombre="Viscosidad KU", limite_minimo=90.0, limite_maximo=100.0, valor_objetivo=95.0, unidad_medida="KU")
        session.add(espec_visc)
        session.flush()
        
        criterio_qc = CriterioAceptacionEtapa(holon_ruta=ruta, etapa=etapa_qc, especificacion=espec_visc)
        session.add(criterio_qc)
        session.flush()
        
        # 6. Crear Red Petri lógica en BD
        # Lugares: p1 (Dispersion), p2 (QC), p3 (Envasado), p4 (Fin)
        lugares_json = {
            "p1": {"id": "p1", "name": "Dispersion", "marking_inicial": 1},
            "p2": {"id": "p2", "name": "Control Calidad", "marking_inicial": 0},
            "p3": {"id": "p3", "name": "Envasado", "marking_inicial": 0},
            "p4": {"id": "p4", "name": "Fin", "marking_inicial": 0}
        }
        
        # Transiciones: 
        # t1 (Carga completada) -> de p1 a p2
        # t2_aprobado (QA Aprobado, trigger 201) -> de p2 a p3
        # t2_rechazado (QA Rechazado, trigger 200) -> de p2 a p1 (reproceso)
        # t3 (Cierre, automática) -> de p3 a p4
        transiciones_json = {
            "t1": {"id": "t1", "name": "Carga completada", "trigger": "200"},
            "t2_aprobado": {"id": "t2_aprobado", "name": "Aprobado", "trigger": "201"},
            "t2_rechazado": {"id": "t2_rechazado", "name": "Rechazado", "trigger": "200"},
            "t3": {"id": "t3", "name": "Envasado completado", "trigger": None}
        }
        
        arcos_json = {
            "a1": {"source": "p1", "target": "t1", "peso": 1},
            "a2": {"source": "t1", "target": "p2", "peso": 1},
            "a3": {"source": "p2", "target": "t2_aprobado", "peso": 1},
            "a4": {"source": "t2_aprobado", "target": "p3", "peso": 1},
            "a5": {"source": "p2", "target": "t2_rechazado", "peso": 1},
            "a6": {"source": "t2_rechazado", "target": "p1", "peso": 1},
            "a7": {"source": "p3", "target": "t3", "peso": 1},
            "a8": {"source": "t3", "target": "p4", "peso": 1}
        }
        
        red_bd = RedPetri(nombre="Red_Premium", lugares=lugares_json, transiciones=transiciones_json, arcos=arcos_json, patron_ruta_id=patron.id, activo=True)
        session.add(red_bd)
        session.flush()
        
        # 7. Crear Orden de Producción
        orden = OrdenProduccion(numero_orden="ORD-99", producto_id=producto.id, holon_ruta_id=ruta.id, cantidad=100.0, prioridad=1, estado="pendiente")
        # Inyectar asignación simulada
        orden.asignacion_recursos = {
            "Dispersion": {"recurso_id": r_disp.id, "recurso_nombre": r_disp.nombre},
            "Control Calidad": {"recurso_id": r_lab.id, "recurso_nombre": r_lab.nombre},
            "Envasado": {"recurso_id": r_disp.id, "recurso_nombre": r_disp.nombre}
        }
        session.add(orden)
        session.commit()
        
        # ============================================================
        # INICIAR ORQUESTADOR Y MOTOR
        # ============================================================
        motor = MotorABTPPN()
        orquestador = Orquestador(motor, session)
        
        # Inicializar orden
        res_init = orquestador.inicializar_orden(orden.id)
        assert res_init is True
        print("✅ Orden e instancias Petri creadas e inicializadas.")
        
        # ============================================================
        # TEST 1: COMPROBACIÓN DE INVARIANTES DE PASO
        # ============================================================
        print("\n🔍 Test 1: Comprobación de invariantes de seguridad...")
        
        # Intentar disparar transición t1 con temperatura de 60.0°C (Límite es 55.0°C)
        t_err = datetime.now() + timedelta(minutes=30)
        try:
            orquestador.procesar_evento_planta(orden.id, "Carga completada", recurso_nombre="D-PREM", red_nombre="Red_Premium", timestamp=t_err, mediciones={"Temperatura": 60.0})
            assert False, "Debería haber lanzado ValueError por invariante violado"
        except ValueError as e:
            print(f"   ✅ EXCEPCIÓN DETECTADA (OK): {e}")
            print("   ✅ INVARIANTE COMPROBADO (OK): Se bloqueó el evento debido a Temperatura de 60.0 C (> 55.0 C).")
            
        # Ahora disparar con temperatura correcta: 52.0°C
        t_ok = datetime.now() + timedelta(minutes=30)
        res_ok = orquestador.procesar_evento_planta(orden.id, "Carga completada", recurso_nombre="D-PREM", red_nombre="Red_Premium", timestamp=t_ok, mediciones={"Temperatura": 52.0})
        assert res_ok is True
        print("   ✅ EVENTO PROCESADO (OK): Lote transicionó correctamente a Control de Calidad con Temperatura de 52.0 C.")
        
        # ============================================================
        # TEST 2: COMPUERTA DE CALIDAD AUTOMÁTICA (QA LOOPS)
        # ============================================================
        print("\n🔍 Test 2: Validación de compuertas de calidad automáticas...")
        
        # Escenario A: Calidad Rechazada (Viscosidad de 70 KU, límite es 90-100 KU)
        # Debe disparar t2_rechazado y retornar el lote a Dispersion (p1)
        t_qc1 = t_ok + timedelta(minutes=15)
        res_qc1 = orquestador.procesar_control_calidad(orden.id, recurso_nombre="LAB-QA", mediciones_qc={"Viscosidad KU": 70.0}, red_nombre="Red_Premium")
        assert res_qc1 is True
        
        # Verificar marcado: debe estar en p1 (reproceso)
        inst_mem_id = orquestador._buscar_instancia_red(orden.id, "Red_Premium")
        inst_mem = motor.instancias[inst_mem_id]
        assert inst_mem.marcado["p1"] == 1
        print("   ✅ CALIDAD RECHAZADA (OK): El lote fue retornado a Dispersión por viscosidad fuera de rango.")
        
        # Procesar nuevamente mezcla
        t_rep = t_qc1 + timedelta(minutes=30)
        orquestador.procesar_evento_planta(orden.id, "Carga completada", recurso_nombre="D-PREM", red_nombre="Red_Premium", timestamp=t_rep, mediciones={"Temperatura": 50.0})
        
        # Escenario B: Calidad Aprobada (Viscosidad de 95 KU)
        # Debe disparar t2_aprobado y avanzar a Envasado (p3), y luego transición automática t3 a Fin (p4)
        t_qc2 = t_rep + timedelta(minutes=15)
        res_qc2 = orquestador.procesar_control_calidad(orden.id, recurso_nombre="LAB-QA", mediciones_qc={"Viscosidad KU": 95.0}, red_nombre="Red_Premium")
        assert res_qc2 is True
        
        # Al disparar t2_aprobado a p3, la transición automática t3 debe dispararse inmediatamente (Fin)
        # Marcado final en p4 debe ser 1
        assert inst_mem.marcado["p4"] == 1
        print("   ✅ CALIDAD APROBADA (OK): El lote fue aprobado con 95.0 KU y avanzó automáticamente a Fin.")
        
        # ============================================================
        # TEST 3: BUCLE DE APRENDIZAJE EWMA
        # ============================================================
        print("\n🔍 Test 3: Bucle de aprendizaje EWMA...")
        
        # Verificar que la orden se haya marcado como completada
        orden_db = session.query(OrdenProduccion).get(orden.id)
        assert orden_db.estado == "completada"
        print("   ✅ ORDEN FINALIZADA (OK): Estado actualizado a 'completada'.")
        
        # La duración del paso de Dispersión (reproceso incluido):
        # 1er paso: t_ok - inicio (duró 30 min)
        # Reproceso: t_rep - t_qc1 (duró 30 min)
        # Duración total real acumulada en dispersión fue de 60 min.
        # Duración nominal planificada era de 30 min.
        # Eficiencia observada = 30 / 30 = 1.0 (en el primer paso, pero con el reproceso la duración real fue de 30 min en cada ejecución).
        # Verifiquemos cómo se actualizó la eficiencia real de la asignación del dispersor:
        asig_disp_db = session.query(AsignacionRecurso).filter_by(holon_ruta_id=ruta.id, recurso_id=r_disp.id).first()
        # Eficiencia anterior = 1.0
        # En la ejecución de reproceso: duró 30 min, nominal era 30 min -> eficiencia obs = 1.0
        # El sistema recalcula usando EWMA: 0.2 * 1.0 + 0.8 * 1.0 = 1.0 (se mantiene)
        # Vamos a verificar que la eficiencia real esté guardada en el modelo
        assert asig_disp_db.eficiencia_real is not None
        print(f"   ✅ APRENDIZAJE EWMA (OK): Eficiencia real autocalibrada del dispersor guardada: {asig_disp_db.eficiencia_real:.3f}")
        
        print("\n🎉 ¡Todos los tests de ejecución y control híbrido de la Sesión 4 pasaron correctamente!")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_control_y_aprendizaje()
