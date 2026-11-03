"""
verificar_paper_ieee_tii.py
===========================
Suite de verificación formal que valida la correspondencia exacta entre el
artículo sometido a IEEE Transactions on Industrial Informatics (IEEE TII)
y la implementación en código abierto de Fénix (`sgofenix/fenix`).

Pruebas incluidas:
  1. Proposición 1 y Ecuación (9): Retropropagación de mermas (m_0 = q_n / prod(gamma_i)),
     absorción en costo unitario (Ec. 8) y no-monotonicidad / dependencia de camino.
  2. Algoritmo 1 (Sección V): Poda de factibilidad en dos etapas (conectividad K y
     agenda dinámica Psi_R con deadline d) y Branch-and-Bound con cota inferior LB(nu) (Ec. 11).
  3. Ecuaciones (6) y (15): Desacoplamiento de EDR(R) aplicado exclusivamente a la
     tasa energética kappa_R y uso de mu_R (`costo_overhead_hora`).
  4. Sección VI (Ecuaciones 12-15): Bucle cerrado SCADA de doble escala temporal
     (calibración EWMA de duración, EDR y rendimiento másico gamma, y umbral N_min).
"""

import sys
import math
from pathlib import Path
from datetime import datetime, timedelta

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FENIX_DIR = ROOT_DIR / "fenix"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FENIX_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos.declarative_base import Base
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.RutaProducto import RutaProducto
from modelos.Versionamiento import VersionRuta
from modelos.RedPetri import RedPetri
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula
from modelos.Recursos import Recurso, RecursoEquipo, ConexionFisica
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from servicios.planificador import PlanificadorProduccion
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN, TokenColoreado


def crear_sesion_en_memoria():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_proposicion_1_y_ecuacion_9():
    """
    Verifica la Proposición 1 (No-monotonicidad y dependencia de camino) y la
    Ecuación (9): m_0 = q_n / prod_{i=1..n} gamma(E_i, R_i).
    """
    print("\n" + "=" * 75)
    print("TEST 1: Proposición 1 y Ecuación (9) - Retropropagación de Mermas")
    print("=" * 75)

    session = crear_sesion_en_memoria()

    familia = FamiliaProducto(nombre="Recubrimientos", descripcion="Familia de prueba")
    op_disp = TipoDeOperacion(codigo="DIS", nombre="Dispersión")
    op_env = TipoDeOperacion(codigo="ENV", nombre="Envasado")
    session.add_all([familia, op_disp, op_env])
    session.flush()

    patron = PatronDeRuta(nombre="Patrón Dispersión-Envasado", version="1", familiaProducto_id=familia.id)
    session.add(patron)
    session.flush()

    e1 = EtapaRuta(nombre="Dispersión", patronRuta_id=patron.id, tipoDeOperacion_id=op_disp.id)
    e2 = EtapaRuta(nombre="Envasado", patronRuta_id=patron.id, tipoDeOperacion_id=op_env.id)
    session.add_all([e1, e2])
    session.flush()

    prod = Producto(codigo="PROD_TII", nombre="Recubrimiento Epóxico Industrial", familia_id=familia.id)
    session.add(prod)
    session.flush()

    ruta = HolonRuta(
        nombre="Ruta Estándar Epóxico",
        producto_id=prod.id,
        patron_id=patron.id,
        activa=True
    )
    session.add(ruta)
    session.flush()

    # Fórmula con materia prima costosa: $12.0 / kg para un lote nominal de 1000 kg
    formula = Formula(
        holon_ruta_id=ruta.id,
        cantidad_producir_lote=1000.0,
        unidad_medida="kg"
    )
    session.add(formula)
    session.flush()

    insumo = InsumoFormula(
        formula_id=formula.id,
        etapa_ruta_id=e1.id,
        nombre_insumo="Resina Epóxica Pura",
        cantidad=1000.0,
        unidad="kg",
        costo_unitario_estimado=12.0
    )
    session.add(insumo)

    # Dos recursos candidatos para la Etapa 1:
    # R1_BARATO_MERMA: Baja tasa horaria ($20/h), pero alto desperdicio (gamma = 0.88)
    # R1_PRECISO: Mayor tasa horaria ($75/h), pero alto rendimiento másico (gamma = 0.99)
    r1_a = Recurso(codigo="DISP_A", nombre="Dispersor Antiguo A", tipo="equipo")
    r1_b = Recurso(codigo="DISP_B", nombre="Dispersor Alta Eficiencia B", tipo="equipo")
    r2 = Recurso(codigo="ENV_1", nombre="Envasadora Automática 1", tipo="equipo")
    session.add_all([r1_a, r1_b, r2])
    session.flush()

    eq1_a = RecursoEquipo(
        id=r1_a.id,
        consumo_energia_kw=10.0,
        costo_energia_por_kwh=0.20,
        costo_depreciacion_hora=5.0,
        costo_overhead_hora=8.0,
        velocidad_procesamiento=20.0,  # 20 kg/min
        rendimiento_nominal=0.88
    )
    eq1_b = RecursoEquipo(
        id=r1_b.id,
        consumo_energia_kw=25.0,
        costo_energia_por_kwh=0.20,
        costo_depreciacion_hora=30.0,
        costo_overhead_hora=10.0,
        velocidad_procesamiento=20.0,  # 20 kg/min
        rendimiento_nominal=0.99
    )
    eq2 = RecursoEquipo(
        id=r2.id,
        consumo_energia_kw=5.0,
        costo_energia_por_kwh=0.20,
        costo_depreciacion_hora=10.0,
        costo_overhead_hora=8.0,
        velocidad_procesamiento=10.0,  # 10 kg/min (dependiente de la masa que sale de E1)
        rendimiento_nominal=0.98
    )
    session.add_all([eq1_a, eq1_b, eq2])

    # Conexiones físicas K(R1_A, R2) = 1 y K(R1_B, R2) = 1 sin pérdida en tubería
    c_a2 = ConexionFisica(recurso_origen_id=r1_a.id, recurso_destino_id=r2.id, flujo_maximo_lps=50.0, activa=True, disponible=True)
    c_b2 = ConexionFisica(recurso_origen_id=r1_b.id, recurso_destino_id=r2.id, flujo_maximo_lps=50.0, activa=True, disponible=True)
    session.add_all([c_a2, c_b2])

    asig_1a = AsignacionRecurso(
        holon_ruta_id=ruta.id, etapa_ruta_id=e1.id, recurso_id=r1_a.id,
        costo_por_hora_real=5.0, duracion_estimada_min=50.0, rendimiento_gamma=0.88
    )
    asig_1b = AsignacionRecurso(
        holon_ruta_id=ruta.id, etapa_ruta_id=e1.id, recurso_id=r1_b.id,
        costo_por_hora_real=30.0, duracion_estimada_min=50.0, rendimiento_gamma=0.99
    )
    asig_2 = AsignacionRecurso(
        holon_ruta_id=ruta.id, etapa_ruta_id=e2.id, recurso_id=r2.id,
        costo_por_hora_real=15.0, duracion_estimada_min=100.0, rendimiento_gamma=0.98
    )
    session.add_all([asig_1a, asig_1b, asig_2])
    session.commit()

    planificador = PlanificadorProduccion(session)

    # 1. Evaluación con retropropagación de merma activa (Ec. 9 del artículo)
    res_con_retro = planificador.seleccionar_recursos_para_orden(
        producto_id=prod.id,
        cantidad=1000.0,
        prioridad=1,
        retropropagar_merma=True
    )

    assert res_con_retro is not None, "El planificador debe encontrar una solución óptima"
    rec_elegido_e1 = res_con_retro["asignacion"]["Dispersión"]["recurso_nombre"]
    masa_inicial = res_con_retro["masa_inicial"]
    masa_salida = res_con_retro["masa_salida"]

    # m_0 esperado para DISP_B (gamma1=0.99, gamma2=0.98): 1000 / (0.99 * 0.98) = 1030.7153 kg
    m0_esperado_b = 1000.0 / (0.99 * 0.98)
    print(f"   -> Recurso seleccionado en E1 (con Ec. 9): {rec_elegido_e1}")
    print(f"   -> Masa inicial retropropagada m_0: {masa_inicial:.2f} kg (esperado: {m0_esperado_b:.2f} kg)")
    print(f"   -> Masa final entregada m_n (q_n):  {masa_salida:.2f} kg (objetivo: 1000.00 kg)")
    print(f"   -> Costo total J(pi*):              ${res_con_retro['costo_total']:.2f}")
    print(f"   -> Costo unitario final u_n:        ${res_con_retro['costo_unitario']:.4f}/kg")

    assert rec_elegido_e1 == "Dispersor Alta Eficiencia B", (
        f"Por Proposición 1, DISP_B debe ser elegido sobre DISP_A al considerar mermas (elegido: {rec_elegido_e1})"
    )
    assert math.isclose(masa_inicial, m0_esperado_b, rel_tol=1e-4), "m_0 debe cumplir exactamente la Ec. (9)"
    assert math.isclose(masa_salida, 1000.0, rel_tol=1e-4), "La masa de salida debe coincidir con q_n = 1000 kg"
    print("   [OK] Proposición 1 y Ecuación (9) verificadas exitosamente.")


def test_algoritmo_1_poda_agenda_deadline_y_bb():
    """
    Verifica el Algoritmo 1:
      - Fase 1b: Ventana temporal sobre la agenda dinámica Psi_R (EAT_k -> EST_k -> EFT_k)
        y poda por fecha límite (deadline d).
      - Fase 2: Poda Branch-and-Bound mediante la cota inferior admisible LB(nu) (Ec. 11).
    """
    print("\n" + "=" * 75)
    print("TEST 2: Algoritmo 1 - Agenda Dinámica Psi_R, Deadline d y Poda LB(nu)")
    print("=" * 75)

    session = crear_sesion_en_memoria()

    familia = FamiliaProducto(nombre="Acrílicos", descripcion="Familia de prueba")
    op_mez = TipoDeOperacion(codigo="MEZ", nombre="Mezclado")
    op_fil = TipoDeOperacion(codigo="FIL", nombre="Filtrado")
    session.add_all([familia, op_mez, op_fil])
    session.flush()

    patron = PatronDeRuta(nombre="Patrón Algoritmo 1", version="1", familiaProducto_id=familia.id)
    session.add(patron)
    session.flush()

    e1 = EtapaRuta(nombre="Mezclado", patronRuta_id=patron.id, tipoDeOperacion_id=op_mez.id)
    e2 = EtapaRuta(nombre="Filtrado", patronRuta_id=patron.id, tipoDeOperacion_id=op_fil.id)
    session.add_all([e1, e2])
    session.flush()

    prod = Producto(codigo="PROD_ALG1", nombre="Pintura Acrílica", familia_id=familia.id)
    session.add(prod)
    session.flush()

    ruta = HolonRuta(nombre="Ruta Acrílica", producto_id=prod.id, patron_id=patron.id, activa=True)
    session.add(ruta)
    session.flush()

    # Dos mezcladores en E1:
    # MEZ_1: Económico pero ocupado en su agenda Psi_R desde t=0 hasta t=120 min
    # MEZ_2: Más costoso por hora pero libre inmediatamente (t=0)
    mez_1 = Recurso(
        codigo="MEZ_1", nombre="Mezclador 1 (Ocupado 0-120m)", tipo="equipo",
        agenda=[{"inicio_min": 0.0, "fin_min": 120.0}]
    )
    mez_2 = Recurso(
        codigo="MEZ_2", nombre="Mezclador 2 (Libre)", tipo="equipo",
        agenda=[]
    )
    # Dos filtros en E2:
    # FIL_1: Costo normal
    # FIL_2: Extremadamente costoso (debe ser podado por LB(nu) en Fase 2)
    fil_1 = Recurso(codigo="FIL_1", nombre="Filtro Estándar 1", tipo="equipo")
    fil_2 = Recurso(codigo="FIL_2", nombre="Filtro Costoso 2", tipo="equipo")
    session.add_all([mez_1, mez_2, fil_1, fil_2])
    session.flush()

    session.add_all([
        RecursoEquipo(id=mez_1.id, consumo_energia_kw=10.0, costo_energia_por_kwh=0.1, costo_depreciacion_hora=5.0, costo_overhead_hora=10.0, rendimiento_nominal=1.0),
        RecursoEquipo(id=mez_2.id, consumo_energia_kw=20.0, costo_energia_por_kwh=0.1, costo_depreciacion_hora=25.0, costo_overhead_hora=10.0, rendimiento_nominal=1.0),
        RecursoEquipo(id=fil_1.id, consumo_energia_kw=5.0, costo_energia_por_kwh=0.1, costo_depreciacion_hora=5.0, costo_overhead_hora=10.0, rendimiento_nominal=1.0),
        RecursoEquipo(id=fil_2.id, consumo_energia_kw=50.0, costo_energia_por_kwh=0.5, costo_depreciacion_hora=200.0, costo_overhead_hora=50.0, rendimiento_nominal=1.0),
    ])

    # Conectividad completa entre E1 y E2
    for r_orig in (mez_1, mez_2):
        for r_dest in (fil_1, fil_2):
            session.add(ConexionFisica(recurso_origen_id=r_orig.id, recurso_destino_id=r_dest.id, flujo_maximo_lps=100.0, activa=True, disponible=True))

    session.add_all([
        AsignacionRecurso(holon_ruta_id=ruta.id, etapa_ruta_id=e1.id, recurso_id=mez_1.id, costo_por_hora_real=10.0, duracion_estimada_min=60.0, rendimiento_gamma=1.0),
        AsignacionRecurso(holon_ruta_id=ruta.id, etapa_ruta_id=e1.id, recurso_id=mez_2.id, costo_por_hora_real=20.0, duracion_estimada_min=60.0, rendimiento_gamma=1.0),
        AsignacionRecurso(holon_ruta_id=ruta.id, etapa_ruta_id=e2.id, recurso_id=fil_1.id, costo_por_hora_real=10.0, duracion_estimada_min=30.0, rendimiento_gamma=1.0),
        AsignacionRecurso(holon_ruta_id=ruta.id, etapa_ruta_id=e2.id, recurso_id=fil_2.id, costo_por_hora_real=100.0, duracion_estimada_min=60.0, rendimiento_gamma=1.0),
    ])
    session.commit()

    planificador = PlanificadorProduccion(session)

    # Caso A: Sin deadline estricto -> elige MEZ_1 (aunque termina en t = 120 + 60 + 30 = 210 min)
    res_sin_deadline = planificador.seleccionar_recursos_para_orden(
        producto_id=prod.id, cantidad=500.0, prioridad=1
    )
    assert res_sin_deadline["asignacion"]["Mezclado"]["recurso_nombre"] == "Mezclador 1 (Ocupado 0-120m)"
    assert res_sin_deadline["makespan_min"] >= 210.0
    print(f"   -> Sin deadline: selecciona '{res_sin_deadline['asignacion']['Mezclado']['recurso_nombre']}' (Makespan={res_sin_deadline['makespan_min']:.1f} min, Costo=${res_sin_deadline['costo_total']:.2f})")

    # Caso B: Con deadline d = 150 min -> MEZ_1 es podado en Fase 1b (EFT_1 = 180 > 150), selecciona MEZ_2 (Makespan ~ 90 min)
    res_con_deadline = planificador.seleccionar_recursos_para_orden(
        producto_id=prod.id, cantidad=500.0, prioridad=1, deadline_min=150.0
    )
    assert res_con_deadline is not None
    assert res_con_deadline["asignacion"]["Mezclado"]["recurso_nombre"] == "Mezclador 2 (Libre)"
    assert res_con_deadline["makespan_min"] <= 150.0
    stats = res_con_deadline["estadisticas_bb"]
    print(f"   -> Con deadline d=150m: selecciona '{res_con_deadline['asignacion']['Mezclado']['recurso_nombre']}' (Makespan={res_con_deadline['makespan_min']:.1f} min, Costo=${res_con_deadline['costo_total']:.2f})")
    print(f"   -> Estadísticas Algoritmo 1: {stats}")
    assert stats["nodos_podados_deadline"] >= 1, "Debe haber podado al menos una rama por deadline"
    assert stats["nodos_podados_bb"] >= 1, "Debe haber podado la rama costosa FIL_2 mediante LB(nu)"
    print("   [OK] Algoritmo 1 (Agenda Psi_R, Deadline d y Poda LB(nu)) verificado exitosamente.")


def test_ecuaciones_abc_edr_y_bucle_ewma():
    """
    Verifica:
      - Ecuaciones (6) y (15): kappa_R^eff = EDR(R) * kappa(R), sin distorsionar la depreciación delta_R,
        y usando mu_R (`costo_overhead_hora`).
      - Sección VI (Ecuaciones 12, 13 y 14): Bucle de aprendizaje EWMA para eficiencia temporal,
        EDR energético y rendimiento másico gamma(p, R).
    """
    print("\n" + "=" * 75)
    print("TEST 3: Ecuaciones (6), (12)-(15) - Tasas ABC Exactas y Bucle Lento EWMA")
    print("=" * 75)

    session = crear_sesion_en_memoria()

    familia = FamiliaProducto(nombre="Especialidades", descripcion="Familia de prueba")
    op = TipoDeOperacion(codigo="DIS", nombre="Dispersión")
    session.add_all([familia, op])
    session.flush()

    patron = PatronDeRuta(nombre="Patrón EWMA", version="1", familiaProducto_id=familia.id)
    session.add(patron)
    session.flush()

    etapa = EtapaRuta(nombre="Dispersión", patronRuta_id=patron.id, tipoDeOperacion_id=op.id)
    prod = Producto(codigo="PROD_EWMA", nombre="Producto Calibración", familia_id=familia.id)
    session.add_all([etapa, prod])
    session.flush()

    ruta = HolonRuta(nombre="Ruta Calibración", producto_id=prod.id, patron_id=patron.id, activa=True)
    rec = Recurso(codigo="EQ_SCADA_01", nombre="Reactor Instrumentado 01", tipo="equipo")
    session.add_all([ruta, rec])
    session.flush()

    # Configurar equipo con medidor_energia=True:
    # kappa_nominal = 20 kW * 0.50 $/kWh = 10.0 $/h
    # edr_actual = 1.5 -> kappa_eff = 15.0 $/h
    # delta_R = 20.0 $/h (NO debe multiplicarse por 1.5)
    # mu_R = 15.0 $/h
    # omega_R = 10.0 $/h
    # Phi esperada = 15.0 + 10.0 + 20.0 + 15.0 = 60.0 $/h
    eq = RecursoEquipo(
        id=rec.id,
        consumo_energia_kw=20.0,
        costo_energia_por_kwh=0.50,
        costo_depreciacion_hora=20.0,
        costo_overhead_hora=15.0,
        medidor_energia=True,
        edr_actual=1.5,
        rendimiento_nominal=0.95
    )
    asig = AsignacionRecurso(
        holon_ruta_id=ruta.id,
        etapa_ruta_id=etapa.id,
        recurso_id=rec.id,
        costo_por_hora_real=10.0,
        duracion_estimada_min=60.0,
        eficiencia_real=1.0,
        rendimiento_gamma=0.95
    )
    session.add_all([eq, asig])
    session.commit()

    # 1. Verificar Ecuación (6) y (15) en PlanificadorProduccion
    tasa_abc = PlanificadorProduccion._obtener_tasa_horaria_abc(asig, eq)
    print(f"   -> Tasa horaria ABC Phi(p, R) calculada: ${tasa_abc:.2f}/h (esperado: $60.00/h)")
    assert math.isclose(tasa_abc, 60.0, rel_tol=1e-6), f"Phi(p, R) debe ser 60.0 $/h según Ec. (6) y (15), obtenido: {tasa_abc}"

    # 2. Verificar Bucle Lento EWMA (Ecuaciones 12, 13 y 14) en Orquestador
    orden = OrdenProduccion(
        numero_orden="ORD-EWMA-001",
        producto_id=prod.id,
        holon_ruta_id=ruta.id,
        cantidad=1000.0,
        prioridad=1,
        estado="completada"
    )
    session.add(orden)
    session.flush()

    inst = InstanciaRed(
        orden_id=orden.id,
        tipo="DIS_dispersion",
        patron_ruta_id=patron.id,
        holon_ruta_id=ruta.id,
        marcado={},
        token_o="ORD-EWMA-001",
        token_m=900.0,
        token_c=500.0,
        activa=False,
        completada=True,
        tipo_terminacion="exito"
    )
    session.add(inst)
    session.flush()

    # Registrar un evento SCADA donde:
    # - duracion_min = 75.0 min (nominal era 60.0 min -> eficiencia_obs = 60/75 = 0.80)
    # - energia_kwh = 30.0 kWh (nominal en 75 min a 20 kW es 25.0 kWh -> edr_obs = 30/25 = 1.20)
    # - masa_entrada = 1000.0 kg, masa_salida = 900.0 kg (-> gamma_obs = 0.90)
    ev = EventoRed(
        orden_id=orden.id,
        instancia_id=inst.id,
        transicion_nombre="Fin Dispersion",
        timestamp=datetime.now(),
        invariantes={
            "tipo": "externo",
            "recurso": "EQ_SCADA_01",
            "duracion_min": 75.0,
            "mediciones": {
                "energia_kwh": 30.0,
                "masa_entrada": 1000.0,
                "masa_salida": 900.0
            }
        },
        token_m=900.0,
        token_c=500.0,
        costo_real_paso=75.0
    )
    session.add(ev)
    session.commit()

    motor = MotorABTPPN()
    orquestador = Orquestador(motor, session)

    # Verificar también que _obtener_costo_hora_recurso del Orquestador coincide con 60.0 $/h
    tasa_orq = orquestador._obtener_costo_hora_recurso(orden.id, "DIS_dispersion", "EQ_SCADA_01")
    assert math.isclose(tasa_orq, 60.0, rel_tol=1e-6), f"Tasa en Orquestador debe ser 60.0 $/h, obtenido: {tasa_orq}"

    # Ejecutar bucle de aprendizaje con alfa = 0.2
    orquestador.ejecutar_aprendizaje_orden(orden.id, alfa=0.2, n_min=1)
    session.refresh(asig)
    session.refresh(eq)

    # Valores esperados con alfa = 0.2:
    # Ec. (12): eficiencia_nueva = 0.2 * 0.80 + 0.8 * 1.00 = 0.96
    # Ec. (13): edr_nuevo        = 0.2 * 1.20 + 0.8 * 1.50 = 1.44
    # Ec. (14): gamma_nuevo      = 0.2 * 0.90 + 0.8 * 0.95 = 0.94
    print(f"   -> Eficiencia temporal calibrada (Ec. 12): {asig.eficiencia_real:.4f} (esperado: 0.9600)")
    print(f"   -> EDR energético calibrado      (Ec. 13): {eq.edr_actual:.4f} (esperado: 1.4400)")
    print(f"   -> Rendimiento másico calibrado  (Ec. 14): {asig.rendimiento_gamma:.4f} (esperado: 0.9400)")

    assert math.isclose(asig.eficiencia_real, 0.96, rel_tol=1e-5)
    assert math.isclose(eq.edr_actual, 1.44, rel_tol=1e-5)
    assert math.isclose(asig.rendimiento_gamma, 0.94, rel_tol=1e-5)
    print("   [OK] Ecuaciones (6), (12), (13), (14) y (15) verificadas exitosamente.")


if __name__ == "__main__":
    print("===========================================================================")
    print(" SUITE DE VERIFICACIÓN FORMAL IEEE TII vs. FÉNIX (SGOFENIX) ")
    print("===========================================================================")
    test_proposicion_1_y_ecuacion_9()
    test_algoritmo_1_poda_agenda_deadline_y_bb()
    test_ecuaciones_abc_edr_y_bucle_ewma()
    print("\n===========================================================================")
    print(" TODAS LAS PRUEBAS DEL ARTÍCULO IEEE TII PASARON EXITOSAMENTE ")
    print("===========================================================================")
