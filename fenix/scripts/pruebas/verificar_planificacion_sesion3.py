# sgo/fenix/scripts/pruebas/verificar_planificacion_sesion3.py
"""
Script de prueba para verificar el planificador óptimo (Sesión 3):
1. Composición selectiva (exclusión de molienda si la receta no tiene sólidos).
2. Búsqueda de caminos físicos (conexión indirecta D1 -> T1 -> L1).
3. Selección óptima basada en costeo real ABC.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz de fenix al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.Recursos import Recurso, RecursoEquipo, UnidadFuncional, ConexionFisica
from servicios.planificador import PlanificadorProduccion

def test_planificador_completo():
    print("🧪 Iniciando pruebas de planificación y composición dinámica...")

    # 1. Base de datos en memoria
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # 2. Datos taxonómicos básicos
        familia = FamiliaProducto(nombre="Pinturas Lox", descripcion="Pinturas premium")
        
        op_disp = TipoDeOperacion(nombre="Dispersion", codigo="DIS")
        op_mol = TipoDeOperacion(nombre="Molienda", codigo="MOL")
        op_dil = TipoDeOperacion(nombre="Dilucion", codigo="DIL")
        
        patron = PatronDeRuta(nombre="Patron Completo", familiaProducto=familia)
        
        etapa_disp = EtapaRuta(nombre="Dispersion", patronRuta=patron, tipoDeOperacion=op_disp)
        etapa_mol = EtapaRuta(nombre="Molienda", patronRuta=patron, tipoDeOperacion=op_mol)
        etapa_dil = EtapaRuta(nombre="Dilucion", patronRuta=patron, tipoDeOperacion=op_dil)
        
        session.add_all([familia, op_disp, op_mol, op_dil, patron, etapa_disp, etapa_mol, etapa_dil])
        session.flush()
        
        # 3. Equipos físicos
        u_func = UnidadFuncional(codigo="SECC-PROD", nombre="Planta Principal")
        session.add(u_func)
        session.flush()
        
        # Equipos
        r_disp1 = Recurso(codigo="D1", nombre="Dispersor Gigante D1", tipo="equipo")
        r_disp2 = Recurso(codigo="D2", nombre="Dispersor Eficiente D2", tipo="equipo")
        r_mol1 = Recurso(codigo="M1", nombre="Molino Vertical M1", tipo="equipo")
        r_dil1 = Recurso(codigo="L1", nombre="Diluidor Automatizado L1", tipo="equipo")
        r_t1 = Recurso(codigo="T1", nombre="Tanque Pulmón Intermedio T1", tipo="equipo")
        
        session.add_all([r_disp1, r_disp2, r_mol1, r_dil1, r_t1])
        session.flush()
        
        # Detalles de los equipos
        eq_disp1 = RecursoEquipo(id=r_disp1.id, modelo="G-500", unidad_id=u_func.id, disponible=True,
                                 consumo_energia_kw=30.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=20.0)
        eq_disp2 = RecursoEquipo(id=r_disp2.id, modelo="E-200", unidad_id=u_func.id, disponible=True,
                                 consumo_energia_kw=15.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=10.0) # Más barato
        eq_mol1 = RecursoEquipo(id=r_mol1.id, modelo="M-Vertical", unidad_id=u_func.id, disponible=True,
                                consumo_energia_kw=45.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=35.0)
        eq_dil1 = RecursoEquipo(id=r_dil1.id, modelo="L-1000", unidad_id=u_func.id, disponible=True,
                                consumo_energia_kw=10.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=15.0)
        eq_t1 = RecursoEquipo(id=r_t1.id, modelo="T-Buffer", unidad_id=u_func.id, disponible=True,
                              consumo_energia_kw=2.0, costo_energia_por_kwh=0.15, costo_depreciacion_hora=5.0)
        
        session.add_all([eq_disp1, eq_disp2, eq_mol1, eq_dil1, eq_t1])
        session.flush()
        
        # 4. Conexiones Físicas
        # Camino indirecto: D1 -> T1 -> L1 (D1 no se conecta directo a L1)
        conn_d1_t1 = ConexionFisica(recurso_origen_id=r_disp1.id, recurso_destino_id=r_t1.id, tipo="BOMBA",
                                    flujo_maximo_lps=0.5, longitud_metros=10.0, requiere_bombeo=True)
        conn_t1_l1 = ConexionFisica(recurso_origen_id=r_t1.id, recurso_destino_id=r_dil1.id, tipo="BOMBA",
                                    flujo_maximo_lps=0.5, longitud_metros=10.0, requiere_bombeo=True)
        # Camino directo: D2 -> L1 (Sin tanques intermedios)
        conn_d2_l1 = ConexionFisica(recurso_origen_id=r_disp2.id, recurso_destino_id=r_dil1.id, tipo="TUBERIA_GRAVEDAD",
                                    flujo_maximo_lps=1.0, longitud_metros=5.0, requiere_bombeo=False)
        
        # Conexiones para el Molino (cuando se use molienda)
        conn_d1_m1 = ConexionFisica(recurso_origen_id=r_disp1.id, recurso_destino_id=r_mol1.id, tipo="BOMBA",
                                    flujo_maximo_lps=0.3, longitud_metros=15.0, requiere_bombeo=True)
        conn_m1_l1 = ConexionFisica(recurso_origen_id=r_mol1.id, recurso_destino_id=r_dil1.id, tipo="BOMBA",
                                    flujo_maximo_lps=0.3, longitud_metros=15.0, requiere_bombeo=True)
        
        session.add_all([conn_d1_t1, conn_t1_l1, conn_d2_l1, conn_d1_m1, conn_m1_l1])
        session.flush()
        
        # 5. Crear productos (Látex con sólidos, y Esmalte sin sólidos)
        p_latex = Producto(codigo="LATEX-SOL", nombre="Pintura Látex con Sólidos", es_fabricado=True, familia=familia)
        p_esmalte = Producto(codigo="ESMALTE-LIQ", nombre="Pintura Líquida sin Sólidos", es_fabricado=True, familia=familia)
        
        p_agua = Producto(codigo="MAT-AGUA", nombre="Agua Industrial", es_insumo=True, familia=familia)
        p_pigmento = Producto(codigo="MAT-PIGM", nombre="Pigmento de Carbonato", es_insumo=True, familia=familia)
        
        session.add_all([p_latex, p_esmalte, p_agua, p_pigmento])
        session.flush()
        
        # 6. Modelos de Ruta (HolonRuta) y Asignaciones
        ruta_latex = HolonRuta(nombre="Modelo Ruta Látex", producto=p_latex, patron=patron, activa=True)
        ruta_esmalte = HolonRuta(nombre="Modelo Ruta Esmalte", producto=p_esmalte, patron=patron, activa=True)
        
        session.add_all([ruta_latex, ruta_esmalte])
        session.flush()
        
        # Asignaciones para Ruta Látex (requiere todas las etapas)
        asig_lat_disp1 = AsignacionRecurso(holon_ruta=ruta_latex, etapa=etapa_disp, recurso_id=r_disp1.id,
                                           duracion_estimada_min=30.0, costo_por_hora_real=50.0)
        asig_lat_mol = AsignacionRecurso(holon_ruta=ruta_latex, etapa=etapa_mol, recurso_id=r_mol1.id,
                                         duracion_estimada_min=45.0, costo_por_hora_real=60.0)
        asig_lat_dil = AsignacionRecurso(holon_ruta=ruta_latex, etapa=etapa_dil, recurso_id=r_dil1.id,
                                         duracion_estimada_min=20.0, costo_por_hora_real=40.0)
        
        # Asignaciones para Ruta Esmalte (tiene múltiples opciones de dispersor)
        asig_esm_disp1 = AsignacionRecurso(holon_ruta=ruta_esmalte, etapa=etapa_disp, recurso_id=r_disp1.id,
                                           duracion_estimada_min=30.0, costo_por_hora_real=50.0)
        asig_esm_disp2 = AsignacionRecurso(holon_ruta=ruta_esmalte, etapa=etapa_disp, recurso_id=r_disp2.id,
                                           duracion_estimada_min=30.0, costo_por_hora_real=30.0) # Más barato y menor consumo
        asig_esm_dil = AsignacionRecurso(holon_ruta=ruta_esmalte, etapa=etapa_dil, recurso_id=r_dil1.id,
                                         duracion_estimada_min=20.0, costo_por_hora_real=40.0)
        
        session.add_all([asig_lat_disp1, asig_lat_mol, asig_lat_dil, asig_esm_disp1, asig_esm_disp2, asig_esm_dil])
        session.flush()
        
        # 7. Fórmulas (Fórmula Látex tiene pigmento en molienda, Fórmula Esmalte no)
        form_latex = Formula(holon_ruta_id=ruta_latex.id, cantidad_producir_lote=100.0)
        form_esmalte = Formula(holon_ruta_id=ruta_esmalte.id, cantidad_producir_lote=100.0)
        
        session.add_all([form_latex, form_esmalte])
        session.flush()
        
        # Insumos Látex (adiciona pigmento en la etapa de molienda)
        ins_lat_agua = InsumoFormula(formula=form_latex, producto=p_agua, nombre_insumo="Agua", cantidad=60.0, etapa=etapa_disp)
        ins_lat_pigm = InsumoFormula(formula=form_latex, producto=p_pigmento, nombre_insumo="Pigmento", cantidad=40.0, etapa=etapa_mol)
        
        # Insumos Esmalte (sin sólidos, solo agua dosificada en dispersión)
        ins_esm_agua = InsumoFormula(formula=form_esmalte, producto=p_agua, nombre_insumo="Agua", cantidad=100.0, etapa=etapa_disp)
        
        session.add_all([ins_lat_agua, ins_lat_pigm, ins_esm_agua])
        session.commit()
        
        # ============================================================
        # EJECUTAR PRUEBA DE COMPOSICIÓN SELECTIVA Y PLANIFICACIÓN
        # ============================================================
        planificador = PlanificadorProduccion(session)
        
        # Caso A: Planificar Esmalte (Sin sólidos)
        # Debe excluir molienda e instanciar solo Dispersion y Dilucion
        print("\n🔍 Caso A: Planificando Pintura Líquida (Esmalte) sin Sólidos...")
        res_esm = planificador.seleccionar_recursos_para_orden(p_esmalte.id, cantidad=100.0, prioridad=1)
        
        assert res_esm is not None
        print(f"✅ Planificación exitosa para Esmalte.")
        print(f"   Ruta seleccionada: '{res_esm['holon_ruta_nombre']}'")
        print(f"   Duración total: {res_esm['duracion_total_min']} min")
        print(f"   Costo total ABC: {res_esm['costo_total']} $")
        
        # Validar composición selectiva: no debe existir "Molienda" en las etapas programadas
        assert "Molienda" not in res_esm["asignacion"]
        print("   ✅ COMPOSICIÓN SELECTIVA (OK): Etapa de Molienda no instanciada por falta de sólidos.")
        
        # Validar selección óptima: debe preferir D2 sobre D1 por ser más barato y eficiente
        assert res_esm["asignacion"]["Dispersion"]["recurso_id"] == r_disp2.id
        print("   ✅ SELECCIÓN ÓPTIMA (OK): Seleccionado el dispersor D2 (más económico y conectado).")
        
        # Caso B: Planificar Látex (Con sólidos)
        # Debe incluir todas las etapas (Dispersion, Molienda, Dilucion)
        print("\n🔍 Caso B: Planificando Látex con Sólidos...")
        res_lat = planificador.seleccionar_recursos_para_orden(p_latex.id, cantidad=100.0, prioridad=1)
        
        assert res_lat is not None
        print(f"✅ Planificación exitosa para Látex.")
        print(f"   Ruta seleccionada: '{res_lat['holon_ruta_nombre']}'")
        print(f"   Duración total: {res_lat['duracion_total_min']} min")
        print(f"   Costo total ABC: {res_lat['costo_total']} $")
        
        # Validar composición selectiva: debe incluir "Molienda"
        assert "Molienda" in res_lat["asignacion"]
        print("   ✅ COMPOSICIÓN SELECTIVA (OK): Etapa de Molienda incluida por presencia de sólidos en la fórmula.")
        
        # Validar ruta de trasvase: debe pasar por D1 (ya que conecta con el molino)
        assert res_lat["asignacion"]["Dispersion"]["recurso_id"] == r_disp1.id
        print("   ✅ CONECTIVIDAD FÍSICA (OK): Asignado Dispersor D1 que posee conexión física con el Molino M1.")
        
        print("\n🎉 ¡Todos los tests de planificación y composición dinámica pasaron correctamente!")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_planificador_completo()
