"""
tests/simulador/ejemplo_integral_modos_abc.py
================================================================================
Ejemplo Integral End-to-End de FÉNIX (MOM/MES Holónico para PyMEs):
1. Ruta de Carga Canónica en 6 Pasos y Semáforo Pre-Producción.
2. Planificación y Cotización Dinámica ABC (Algoritmo 1: Poda + Branch & Bound +
   Retropropagación de Mermas m_0 = q_n / prod(gamma_k) + Agenda Psi_R).
3. Ejecución Híbrida de Piso de Planta Coexistiendo las 3 Modalidades Tecnológicas:
   - Versión C (C_EDGE): Nodo de borde de bajo coste (Arduino SCT-013 + DS18B20 +
     Gateway Raspberry Pi) en la etapa de Mezclado Térmico.
   - Versión A (A_OPERADOR): Sin tecnología avanzada de piso (Operador en Tablet)
     en la etapa de Homogeneización e Inspección.
   - Versión B (B_SCADA): Tecnología media (Conector hacia SCADA / PLC existente)
     en la etapa de Envasado Automatizado.
4. Supervisión en el Centro de Control Ejecutivo MES (`/mes/api/resumen`) y
   Auto-Calibración de Doble Escala Temporal EWMA / EDR (Ecuaciones 12-15).
================================================================================
"""

import sys
import math
from pathlib import Path
from datetime import datetime

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
from modelos.Taxonomia import FamiliaProducto, TipoDeOperacion, PatronDeRuta, EtapaRuta
from modelos.RedPetri import RedPetri, DuracionEstimadaLugar
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.Recursos import (
    UnidadNegocio, UnidadFuncional, Recurso, RecursoEquipo, RecursoPersonal,
    ServicioTecnico, ServicioTecnicoOfrecido, ConexionFisica
)
from modelos.Producto import (
    Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula, InvariantePaso
)
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente
from utils.motor_abtppn import MotorABTPPN
from servicios.orquestador import Orquestador
from tools.edge_y_scada.nodo_edge_raspberry_arduino import NodoEdgeRaspberryArduino
from tools.edge_y_scada.conector_scada_cliente import ConectorSCADAFenix, MapeoTagSCADA
import web.app as flask_app_module


def construir_planta_ejemplo_6_pasos(session):
    """
    Ejecuta la Ruta de Carga Canónica en 6 Pasos para configurar una planta PyME
    híbrida con estaciones en Modo C (Edge Arduino/RPi), Modo A (Operador) y Modo B (SCADA).
    """
    print("\n" + "=" * 78)
    print("FASE 1: RUTA DE CARGA CANÓNICA EN 6 PASOS (SABER HACER -> TECNOLOGÍA)")
    print("=" * 78)

    # PASO 1: Jerarquía Física (Unidades de Negocio y Unidades Funcionales)
    un = UnidadNegocio(codigo="UN_QUIM", nombre="División Recubrimientos y Resinas PyME")
    session.add(un)
    session.flush()

    uf_proc = UnidadFuncional(
        codigo="UF_PROC",
        nombre="Nave de Reacción y Mezclado",
        unidadNegocio_id=un.id,
        descripcion="PROCESO"
    )
    uf_env = UnidadFuncional(
        codigo="UF_ENV",
        nombre="Línea de Acabado y Envasado",
        unidadNegocio_id=un.id,
        descripcion="ENVASADO"
    )
    session.add_all([uf_proc, uf_env])
    session.flush()
    print("  [Paso 1 OK] Unidades Funcionales registradas: UF_PROC, UF_ENV")

    # PASO 2: Taxonomía Industrial (Familias y Tipos de Operación)
    familia = FamiliaProducto(
        nombre="Resinas Acrílicas",
        descripcion="Emulsiones y recubrimientos base agua"
    )
    op_mez = TipoDeOperacion(codigo="MEZ", nombre="Mezclado Térmico")
    op_hom = TipoDeOperacion(codigo="HOM", nombre="Homogeneización Manual")
    op_env = TipoDeOperacion(codigo="ENV", nombre="Envasado")
    session.add_all([familia, op_mez, op_hom, op_env])
    session.flush()
    print("  [Paso 2 OK] Taxonomía cargada: 1 Familia, 3 Tipos de Operación (MEZ, HOM, ENV)")

    # PASO 3: Patrón de Ruta, Redes de Petri AB-TPPN (N_E y N_S) y Encadenamiento
    patron = PatronDeRuta(
        nombre="Patrón Híbrido ABC (Mezcla-Homog-Envasado)",
        version="1.0",
        familiaProducto_id=familia.id,
        activo=True
    )
    session.add(patron)
    session.flush()

    e1 = EtapaRuta(nombre="Mezclado", patronRuta_id=patron.id, tipoDeOperacion_id=op_mez.id)
    e2 = EtapaRuta(nombre="Homogeneizado", patronRuta_id=patron.id, tipoDeOperacion_id=op_hom.id)
    e3 = EtapaRuta(nombre="Envasado", patronRuta_id=patron.id, tipoDeOperacion_id=op_env.id)
    session.add_all([e1, e2, e3])
    session.flush()

    # Red de Ejecución Física N_E (con 3 lugares operativos p1, p2, p3 y lugar final p_fin)
    red_ejecucion = RedPetri(
        nombre="red_ejecucion_mez_hom_env",
        descripcion="Red AB-TPPN de Ejecución Física de Planta (N_E)",
        patron_ruta_id=patron.id,
        activo=True,
        lugares={
            "p1": {"name": "Mezclado en Curso", "marking_inicial": 1},
            "p2": {"name": "Homogeneizado en Curso", "marking_inicial": 0},
            "p3": {"name": "Envasado en Curso", "marking_inicial": 0},
            "p_exito": {"name": "Fin Exitoso Ejecución", "marking_inicial": 0}
        },
        transiciones={
            "t_fin_mezcla": {"name": "Fin Mezclado", "trigger": "200"},
            "t_fin_homog": {"name": "Fin Homogeneizado", "trigger": "200"},
            "t_fin_envasado": {"name": "Fin Envasado", "trigger": "200"}
        },
        arcos={
            "a1": {"source": "p1", "target": "t_fin_mezcla", "peso": 1},
            "a2": {"source": "t_fin_mezcla", "target": "p2", "peso": 1},
            "a3": {"source": "p2", "target": "t_fin_homog", "peso": 1},
            "a4": {"source": "t_fin_homog", "target": "p3", "peso": 1},
            "a5": {"source": "p3", "target": "t_fin_envasado", "peso": 1},
            "a6": {"source": "t_fin_envasado", "target": "p_exito", "peso": 1}
        }
    )

    # Red de Seguimiento / Negocio N_S sincronizada mediante mensajes inter-red
    red_seguimiento = RedPetri(
        nombre="red_seguimiento_erp",
        descripcion="Red AB-TPPN de Seguimiento de Negocio y Costeo (N_S)",
        patron_ruta_id=patron.id,
        activo=True,
        lugares={
            "s1": {"name": "Orden en Mezclado", "marking_inicial": 1},
            "s2": {"name": "Orden en Homogeneizado", "marking_inicial": 0},
            "s3": {"name": "Orden en Envasado", "marking_inicial": 0},
            "s_exito": {"name": "Orden Cerrada Exitosamente", "marking_inicial": 0}
        },
        transiciones={
            "ts_mezcla_ok": {"name": "Sync Mezclado Completado", "trigger": "201"},
            "ts_homog_ok": {"name": "Sync Homogeneizado Completado", "trigger": "201"},
            "ts_envasado_ok": {"name": "Sync Envasado Completado", "trigger": "201"}
        },
        arcos={
            "as1": {"source": "s1", "target": "ts_mezcla_ok", "peso": 1},
            "as2": {"source": "ts_mezcla_ok", "target": "s2", "peso": 1},
            "as3": {"source": "s2", "target": "ts_homog_ok", "peso": 1},
            "as4": {"source": "ts_homog_ok", "target": "s3", "peso": 1},
            "as5": {"source": "s3", "target": "ts_envasado_ok", "peso": 1},
            "as6": {"source": "ts_envasado_ok", "target": "s_exito", "peso": 1}
        }
    )
    session.add_all([red_ejecucion, red_seguimiento])
    session.flush()

    encadenamiento = ConfiguracionEncadenamiento(
        nombre="Encadenamiento_Hibrido_NE_NS",
        red_principal_pnml="red_seguimiento_erp.pnml",
        descripcion="Sincronización formal N_E -> N_S (Sección IV.C IEEE TII)",
        patron_ruta_id=patron.id,
        activo=True,
        reglas={
            "red_ejecucion_mez_hom_env.t_fin_mezcla": [
                {"red_destino": "red_seguimiento_erp", "evento_destino": "ts_mezcla_ok"}
            ],
            "red_ejecucion_mez_hom_env.t_fin_homog": [
                {"red_destino": "red_seguimiento_erp", "evento_destino": "ts_homog_ok"}
            ],
            "red_ejecucion_mez_hom_env.t_fin_envasado": [
                {"red_destino": "red_seguimiento_erp", "evento_destino": "ts_envasado_ok"}
            ]
        }
    )
    session.add(encadenamiento)
    session.flush()
    print("  [Paso 3 OK] Patrón, Redes AB-TPPN (N_E || N_S) y Reglas de Encadenamiento cargadas")

    # PASO 4: Holones de Recurso (Coexistencia Modos C, A y B) y Conectividad Física K
    # - Estación 1 (Modo C - Edge Arduino/RPi): Mezclador Térmico con SCT-013 + DS18B20
    rec_mez_c = Recurso(
        codigo="MEZ_EDGE_01",
        nombre="Mezclador Térmico 01 (Arduino Edge)",
        tipo="equipo",
        descripcion="Instrumentado con Nodo Edge Arduino SCT-013 + DS18B20 + Raspberry Pi"
    )
    # - Estación 2 (Modo A - Operador Tablet): Cuba de Homogeneización Manual
    rec_hom_a = Recurso(
        codigo="HOM_MAN_01",
        nombre="Cuba Homogeneizadora Manual 01",
        tipo="equipo",
        descripcion="Operación asistida por operador en Tablet Web (Human-in-the-Loop)"
    )
    # - Estación 3 (Modo B - SCADA/PLC): Línea de Envasado con PLC/SCADA existente
    rec_env_b = Recurso(
        codigo="ENV_SCADA_01",
        nombre="Envasadora Automática SCADA 01",
        tipo="equipo",
        descripcion="Integrada mediante Conector SCADA / PLC existente"
    )
    rec_operador = Recurso(
        codigo="OP_PLANTA_01",
        nombre="Operador Especialista Turno 1",
        tipo="personal",
        descripcion="Operador de planta"
    )
    session.add_all([rec_mez_c, rec_hom_a, rec_env_b, rec_operador])
    session.flush()

    eq_mez = RecursoEquipo(
        id=rec_mez_c.id,
        modelo="Reactor Edge IIoT (Arduino+RPi)",
        unidad_id=uf_proc.id,
        capacidad_maxima=1500.0,
        velocidad_procesamiento=15.0,
        rendimiento_nominal=0.98,
        consumo_energia_kw=20.0,
        costo_energia_por_kwh=0.25,     # kappa_base = 5.0 $/h
        costo_depreciacion_hora=10.0,   # delta = 10.0 $/h
        costo_overhead_hora=12.0,       # mu = 12.0 $/h
        disponible=True,
        medidor_energia=True,           # Modo C: Medidor no invasivo SCT-013 en Arduino
        edr_actual=1.0
    )
    eq_hom = RecursoEquipo(
        id=rec_hom_a.id,
        modelo="Cuba Estándar (Modo A Operador)",
        unidad_id=uf_proc.id,
        capacidad_maxima=1500.0,
        velocidad_procesamiento=20.0,
        rendimiento_nominal=0.99,
        consumo_energia_kw=4.0,
        costo_energia_por_kwh=0.25,     # kappa_base = 1.0 $/h
        costo_depreciacion_hora=4.0,    # delta = 4.0 $/h
        costo_overhead_hora=8.0,        # mu = 8.0 $/h
        disponible=True,
        medidor_energia=False,          # Modo A: Sin sensores de energía en piso
        edr_actual=1.0
    )
    eq_env = RecursoEquipo(
        id=rec_env_b.id,
        modelo="Línea PLC Siemens/SCADA (Modo B)",
        unidad_id=uf_env.id,
        capacidad_maxima=2000.0,
        velocidad_procesamiento=25.0,
        rendimiento_nominal=0.99,
        consumo_energia_kw=15.0,
        costo_energia_por_kwh=0.25,     # kappa_base = 3.75 $/h
        costo_depreciacion_hora=12.0,   # delta = 12.0 $/h
        costo_overhead_hora=10.0,       # mu = 10.0 $/h
        disponible=True,
        medidor_energia=True,           # Modo B: Tag de kWh desde PLC/SCADA
        edr_actual=1.0
    )
    per_op = RecursoPersonal(
        id=rec_operador.id,
        unidad_id=un.id,
        especialidad="Operador de Planta",
        costo_por_hora=15.0,
        disponible=True
    )
    session.add_all([eq_mez, eq_hom, eq_env, per_op])
    session.flush()

    # Servicios Técnicos Ofrecidos S_R y Grafo de Conectividad Física K
    st_mez = ServicioTecnico(nombre="Servicio Mezclado Térmico", descripcion="Mezcla con control térmico")
    st_hom = ServicioTecnico(nombre="Servicio Homogeneizado", descripcion="Homogeneización e inspección")
    st_env = ServicioTecnico(nombre="Servicio Envasado", descripcion="Envasado y sellado")
    session.add_all([st_mez, st_hom, st_env])
    session.flush()

    s1 = ServicioTecnicoOfrecido(
        unidadFuncional_id=uf_proc.id, servicio_id=st_mez.id, capacidad=1500.0
    )
    s2 = ServicioTecnicoOfrecido(
        unidadFuncional_id=uf_proc.id, servicio_id=st_hom.id, capacidad=1500.0
    )
    s3 = ServicioTecnicoOfrecido(
        unidadFuncional_id=uf_env.id, servicio_id=st_env.id, capacidad=2000.0
    )
    c12 = ConexionFisica(
        recurso_origen_id=rec_mez_c.id, recurso_destino_id=rec_hom_a.id,
        tipo="TUBERIA", flujo_maximo_lps=1.0, perdida_material_pct=0.0, activa=True, disponible=True
    )
    c23 = ConexionFisica(
        recurso_origen_id=rec_hom_a.id, recurso_destino_id=rec_env_b.id,
        tipo="BOMBA", flujo_maximo_lps=1.0, perdida_material_pct=0.0, activa=True, disponible=True
    )
    session.add_all([s1, s2, s3, c12, c23])
    session.flush()
    print("  [Paso 4 OK] Holones de Recurso (Modo C Edge, Modo A Operador, Modo B SCADA) y Grafo K cargados")

    # PASO 5: Holón Producto, Ruta, Fórmula (BOM), Duraciones e Invariantes Físicos
    prod_insumo = Producto(
        codigo="MP_MONOMERO", nombre="Monómero Acrílico Puro",
        familia_id=familia.id, es_insumo=True, es_fabricado=False, es_adquirido=True
    )
    prod_final = Producto(
        codigo="RES_ACR_500", nombre="Resina Acrílica Industrial Premium",
        familia_id=familia.id, es_insumo=False, es_fabricado=True
    )
    session.add_all([prod_insumo, prod_final])
    session.flush()

    holon_ruta = HolonRuta(
        nombre="Ruta Híbrida Estándar (Edge + Operador + SCADA)",
        producto_id=prod_final.id,
        patron_id=patron.id,
        activa=True
    )
    session.add(holon_ruta)
    session.flush()

    formula = Formula(
        holon_ruta_id=holon_ruta.id,
        cantidad_producir_lote=500.0,
        unidad_medida="kg"
    )
    session.add(formula)
    session.flush()

    insumo_f = InsumoFormula(
        formula_id=formula.id,
        etapa_ruta_id=e1.id,
        producto_id=prod_insumo.id,
        nombre_insumo="Monómero Acrílico Puro",
        cantidad=500.0,
        unidad="kg",
        costo_unitario_estimado=4.50
    )
    session.add(insumo_f)

    asig_mez = AsignacionRecurso(
        holon_ruta_id=holon_ruta.id, etapa_ruta_id=e1.id, recurso_id=rec_mez_c.id,
        costo_por_hora_real=15.0, duracion_estimada_min=35.0, eficiencia_real=1.0, rendimiento_gamma=0.98
    )
    asig_hom = AsignacionRecurso(
        holon_ruta_id=holon_ruta.id, etapa_ruta_id=e2.id, recurso_id=rec_hom_a.id,
        costo_por_hora_real=15.0, duracion_estimada_min=25.0, eficiencia_real=1.0, rendimiento_gamma=0.99
    )
    asig_env = AsignacionRecurso(
        holon_ruta_id=holon_ruta.id, etapa_ruta_id=e3.id, recurso_id=rec_env_b.id,
        costo_por_hora_real=15.0, duracion_estimada_min=20.0, eficiencia_real=1.0, rendimiento_gamma=0.99
    )
    session.add_all([asig_mez, asig_hom, asig_env])
    session.flush()

    # Invariante termodinámico en Etapa 1 (Mezclado): Temperatura en [60.0, 75.0] °C
    inv_temp = InvariantePaso(
        asignacion_recurso_id=asig_mez.id,
        parametro="temperatura_c",
        valor_minimo=60.0,
        valor_maximo=75.0,
        unidad="°C"
    )
    d1 = DuracionEstimadaLugar(
        producto_id=prod_final.id, red_id=red_ejecucion.id,
        lugar_id="p1", lugar_nombre="Mezclado en Curso", recurso_id=rec_mez_c.id,
        duracion_segundos=2100.0
    )
    d2 = DuracionEstimadaLugar(
        producto_id=prod_final.id, red_id=red_ejecucion.id,
        lugar_id="p2", lugar_nombre="Homogeneizado en Curso", recurso_id=rec_hom_a.id,
        duracion_segundos=1500.0
    )
    d3 = DuracionEstimadaLugar(
        producto_id=prod_final.id, red_id=red_ejecucion.id,
        lugar_id="p3", lugar_nombre="Envasado en Curso", recurso_id=rec_env_b.id,
        duracion_segundos=1200.0
    )
    session.add_all([inv_temp, d1, d2, d3])
    session.commit()
    print("  [Paso 5 OK] Producto, HolonRuta, BOM, Duraciones e Invariante Térmico [60, 75] °C cargados")

    return {
        "producto_id": prod_final.id,
        "recurso_mez": rec_mez_c.nombre,
        "recurso_hom": rec_hom_a.nombre,
        "recurso_env": rec_env_b.nombre,
        "red_ejecucion": red_ejecucion.nombre,
        "red_seguimiento": red_seguimiento.nombre
    }


def ejecutar_ejemplo_integral():
    # Configurar base de datos en memoria dedicada y enlazarla con la app Flask de Fénix
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session_init = SessionLocal()
    info_planta = construir_planta_ejemplo_6_pasos(session_init)

    # Inicializar motor y orquestador sobre esta base de datos
    motor = MotorABTPPN()
    orquestador = Orquestador(motor, SessionLocal())
    orquestador.cargar_configuracion_desde_bd()

    flask_app = flask_app_module.app
    flask_app.config["TESTING"] = True
    flask_app.config["ENGINE"] = engine
    flask_app.config["SESSION_MAKER"] = SessionLocal
    flask_app.config["MOTOR"] = motor
    flask_app.config["ORQUESTADOR"] = orquestador

    client = flask_app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["usuario_nombre"] = "Ing. Planta PyME"
        sess["usuario_rol"] = "admin"

    # Helper para que los conectores Modo B (SCADA) y Modo C (Edge RPi+Arduino) publiquen al cliente Flask
    def post_local(ruta: str, payload: dict) -> dict:
        resp = client.post(ruta, json=payload)
        return resp.get_json()

    # PASO 6 de Ruta de Carga: Verificar Semáforo Pre-Producción en el Centro de Control MES
    resp_mes_ini = client.get("/mes/api/resumen").get_json()
    assert resp_mes_ini["success"] is True
    assert resp_mes_ini["semaforo_global"] in ("VERDE", "AMARILLO")
    pasos_completos = sum(1 for p in resp_mes_ini["ruta_carga"] if p["completado"])
    print(f"  [Paso 6 OK] Diagnóstico Pre-Producción: Semáforo {resp_mes_ini['semaforo_global']} ({pasos_completos}/6 pasos completos)")

    # =========================================================================
    # FASE 2: PLANIFICACIÓN Y COTIZACIÓN DINÁMICA ABC (ALGORITMO 1)
    # =========================================================================
    print("\n" + "=" * 78)
    print("FASE 2: PLANIFICACIÓN HOLÓNICA Y COTIZACIÓN ABC (ALGORITMO 1 IEEE TII)")
    print("=" * 78)

    resp_cot = client.post("/planificador/api/cotizar", json={
        "producto_id": info_planta["producto_id"],
        "cantidad": 500.0,
        "prioridad": 2,
        "v_target": 5000.0,
        "deadline_min": 240.0,
        "retropropagar_merma": True
    }).get_json()
    assert resp_cot["success"] is True, f"Fallo en cotización: {resp_cot}"
    plan = resp_cot["plan"]

    # Rendimiento global acumulado: gamma_total = 0.98 * 0.99 * 0.99 = 0.960498
    # Masa inicial retropropagada (Ec. 9): m_0 = 500 / 0.960498 = 520.5633 kg
    gamma_global = 0.98 * 0.99 * 0.99
    m0_esperada = 500.0 / gamma_global
    assert math.isclose(plan["masa_inicial_kg"], m0_esperada, rel_tol=1e-4)
    assert math.isclose(plan["masa_final_kg"], 500.0, rel_tol=1e-4)

    print(f"  -> Ruta Óptima Seleccionada : {plan['holon_ruta_nombre']}")
    print(f"  -> Retropropagación (Ec. 9) : Masa inicial m_0 = {plan['masa_inicial_kg']:.2f} kg -> Salida neta q_n = {plan['masa_final_kg']:.2f} kg")
    print(f"  -> Costo Total Estimado ABC : ${plan['costo_total']:.2f} | Costo Unitario u_K = ${plan['costo_unitario']:.4f}/kg")
    print(f"  -> Makespan Estimado EFT_K  : {plan['duracion_total_min']:.1f} min (Deadline d = 240.0 min)")

    # Crear y reservar la orden optimizada
    resp_orden = client.post("/planificador/api/crear_orden_optimizada", json={
        "producto_id": info_planta["producto_id"],
        "cantidad": 500.0,
        "prioridad": 2,
        "v_target": 5000.0,
        "deadline_min": 240.0,
        "retropropagar_merma": True
    }).get_json()
    assert resp_orden["success"] is True
    orden_id = resp_orden["orden_id"]
    print(f"  -> Orden Creada y Reservada : #{orden_id} ({resp_orden['numero_orden']}) en agendas Psi_R")

    # Iniciar las redes AB-TPPN (N_E y N_S) desde el endpoint MES
    resp_ini = client.post(f"/mes/api/orden/{orden_id}/iniciar").get_json()
    assert resp_ini["success"] is True
    print(f"  -> Orquestador AB-TPPN      : {resp_ini['mensaje']}")

    # Para que la resolución automática por recurso encuentre las 3 estaciones en N_E,
    # registramos los 3 recursos asignados en recursos_ocupados de la instancia física N_E
    s_fix = SessionLocal()
    inst_ne = s_fix.query(InstanciaRed).filter_by(
        orden_id=orden_id, tipo=info_planta["red_ejecucion"]
    ).first()
    inst_ne.recursos_ocupados = {
        "recursos": [
            info_planta["recurso_mez"],
            info_planta["recurso_hom"],
            info_planta["recurso_env"]
        ]
    }
    s_fix.commit()
    s_fix.close()

    # =========================================================================
    # FASE 3: EJECUCIÓN EN PLANTA COEXISTIENDO MODOS C, A Y B
    # =========================================================================
    print("\n" + "=" * 78)
    print("FASE 3: EJECUCIÓN HÍBRIDA DE PLANTA (MODO C EDGE + MODO A OPERADOR + MODO B SCADA)")
    print("=" * 78)

    # -------------------------------------------------------------------------
    # ETAPA 1 (Mezclado): MODO C — Nodo Edge de Bajo Coste (Arduino + Raspberry Pi)
    # -------------------------------------------------------------------------
    print("\n  [Etapa 1 · MODO C (Edge Arduino SCT-013 + DS18B20 + Raspberry Pi)]")
    gateway_rpi = NodoEdgeRaspberryArduino(cliente_local_post=post_local)
    gateway_rpi.registrar_estacion_arduino(
        nodo_id="ARD-MEZ-01",
        recurso_fenix=info_planta["recurso_mez"],
        evento_fin_fenix="Fin Mezclado",
        red_fenix=info_planta["red_ejecucion"]
    )

    # 1a) Prueba de bloqueo por Invariante Físico: el Arduino intenta finalizar a 51.0 °C (< 60.0 °C)
    resp_bloqueo = gateway_rpi.procesar_trama_arduino(orden_id, {
        "nodo_id": "ARD-MEZ-01",
        "corriente_a": 22.0,
        "voltaje_v": 220.0,
        "cos_phi": 0.88,
        "temp_c": 51.0,
        "boton_fin": 1,
        "dt_seg": 60.0
    })
    assert resp_bloqueo is not None and resp_bloqueo["success"] is False
    assert resp_bloqueo.get("bloqueo_invariante") is True
    print(f"    -> Verificación Invariante (T=51.0°C < 60°C): Bloqueado correctamente ({resp_bloqueo['mensaje']})")

    # 1b) Operación nominal del lote en el Mezclador:
    #     Simulamos 4 muestras de 600 s (40 min en total = 2400 s) con potencia activa de 24.3 kW
    #     (consumo real = 16.20 kWh frente al nominal de 20 kW * 40/60 h = 13.333 kWh -> EDR_obs = 1.215)
    for paso_i in range(4):
        es_ultimo = (paso_i == 3)
        resp_edge = gateway_rpi.procesar_trama_arduino(orden_id, {
            "nodo_id": "ARD-MEZ-01",
            "potencia_kw": 24.3,
            "corriente_a": 25.1,
            "voltaje_v": 220.0,
            "temp_c": 65.5,
            "boton_fin": 1 if es_ultimo else 0,
            "dt_seg": 600.0,
            "mediciones_extra": {
                "merma_kg": 10.4,
                "costo_materia_prima": plan["masa_inicial_kg"] * 4.50
            } if es_ultimo else None
        })

    assert resp_edge is not None and resp_edge["success"] is True, f"Error en Modo C: {resp_edge}"
    print(f"    -> Evento Modo C Procesado : {resp_edge['mensaje']}")
    print(f"    -> Estado Token tras Mezcla: m = {resp_edge['token']['m']:.2f} kg | c_acc = ${resp_edge['token']['c_acc']:.2f} | u = ${resp_edge['token']['u']:.4f}/kg")

    # -------------------------------------------------------------------------
    # ETAPA 2 (Homogeneización): MODO A — Operador en Tablet Web (Human-in-the-Loop)
    # -------------------------------------------------------------------------
    print("\n  [Etapa 2 · MODO A (Sin tecnología avanzada de piso — Operador en Tablet)]")
    resp_op = post_local("/api/ingesta/evento_planta", {
        "orden_id": orden_id,
        "recurso": info_planta["recurso_hom"],
        "red": info_planta["red_ejecucion"],
        "evento": "Fin Homogeneizado",
        "modo_captura": "A_OPERADOR",
        "mediciones": {
            "duracion_min": 25.0,
            "merma_kg": 5.1,
            "observacion_operador": "Homogeneización e inspección visual conforme"
        }
    })
    assert resp_op["success"] is True, f"Error en Modo A: {resp_op}"
    print(f"    -> Evento Modo A Procesado : {resp_op['mensaje']}")
    print(f"    -> Estado Token tras Homog.: m = {resp_op['token']['m']:.2f} kg | c_acc = ${resp_op['token']['c_acc']:.2f} | u = ${resp_op['token']['u']:.4f}/kg")

    # -------------------------------------------------------------------------
    # ETAPA 3 (Envasado): MODO B — Conector SCADA / PLC Existente
    # -------------------------------------------------------------------------
    print("\n  [Etapa 3 · MODO B (Tecnología Media — Conector SCADA / PLC Existente)]")
    conector_scada = ConectorSCADAFenix(cliente_local_post=post_local)
    conector_scada.registrar_mapeo(MapeoTagSCADA(
        tag_disparo="PLC_ENV01.FIN_LOTE",
        recurso_fenix=info_planta["recurso_env"],
        evento_fenix="Fin Envasado",
        red_fenix=info_planta["red_ejecucion"],
        tag_energia_kwh="PLC_ENV01.KWH_LOTE",
        tag_temperatura_c="PLC_ENV01.TEMP_SELLADO",
        tag_merma_kg="PLC_ENV01.MERMA_KG",
        tags_extra={"duracion_min": "PLC_ENV01.TIEMPO_CICLO_MIN"}
    ))

    resp_scada = conector_scada.procesar_flanco_tag(
        orden_id=orden_id,
        tag_disparo="PLC_ENV01.FIN_LOTE",
        lecturas_tags={
            "PLC_ENV01.KWH_LOTE": 6.50,          # En 22 min a 15 kW nominal (5.5 kWh) -> EDR_obs = 1.1818
            "PLC_ENV01.TEMP_SELLADO": 42.0,
            "PLC_ENV01.MERMA_KG": 5.06,
            "PLC_ENV01.TIEMPO_CICLO_MIN": 22.0
        }
    )
    assert resp_scada["success"] is True, f"Error en Modo B: {resp_scada}"
    print(f"    -> Evento Modo B Procesado : {resp_scada['mensaje']}")
    print(f"    -> Estado Token Final      : m = {resp_scada['token']['m']:.2f} kg | c_acc = ${resp_scada['token']['c_acc']:.2f} | u = ${resp_scada['token']['u']:.4f}/kg")
    print(f"    -> Estado de la Orden      : {resp_scada['estado_orden'].upper()}")
    assert resp_scada["estado_orden"] == "completada", "La orden debe haber finalizado en estado 'completada'"

    # =========================================================================
    # FASE 4: VERIFICACIÓN DEL CENTRO DE CONTROL MES Y BUCLE LENTO EWMA / EDR
    # =========================================================================
    print("\n" + "=" * 78)
    print("FASE 4: RESUMEN EJECUTIVO MES Y AUTO-CALIBRACIÓN EWMA / EDR (ECS. 12-15)")
    print("=" * 78)

    resumen_final = client.get("/mes/api/resumen").get_json()
    assert resumen_final["success"] is True

    modos_vistos = {ev["modo_captura"] for ev in resumen_final["eventos_recientes"] if "modo_captura" in ev}
    print(f"  -> Modalidades registradas en bitácora MES: {sorted(modos_vistos)}")
    assert {"A_OPERADOR", "B_SCADA", "C_EDGE"}.issubset(modos_vistos)

    for rec in resumen_final["recursos"]:
        if rec["tipo"] == "equipo":
            print(
                f"  -> Holón '{rec['nombre']}' [{rec['modo_captura']['codigo']}]: "
                f"EDR={rec['edr_actual']:.3f} ({rec['salud_energetica']}), "
                f"gamma={rec['gamma']:.4f}, Tasa ABC=${rec['tasa_total_abc_h']:.2f}/h"
            )

    # Verificar que el Mezclador Edge (Modo C) y la Envasadora SCADA (Modo B) recalibraron su EDR > 1.0
    rec_mez_post = next(r for r in resumen_final["recursos"] if r["codigo"] == "MEZ_EDGE_01")
    rec_env_post = next(r for r in resumen_final["recursos"] if r["codigo"] == "ENV_SCADA_01")
    assert rec_mez_post["edr_actual"] > 1.02, f"EDR del Mezclador Edge debió subir tras consumo real mayor, actual={rec_mez_post['edr_actual']}"
    assert rec_env_post["edr_actual"] > 1.02, f"EDR de la Envasadora SCADA debió subir tras consumo real mayor, actual={rec_env_post['edr_actual']}"

    print("\n" + "=" * 78)
    print(" EJEMPLO INTEGRAL HÍBRIDO (MODOS A, B Y C + INTERFACES MES) COMPLETADO CON ÉXITO ")
    print("=" * 78)


if __name__ == "__main__":
    ejecutar_ejemplo_integral()
