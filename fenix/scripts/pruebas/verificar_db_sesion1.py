# sgo/fenix/scripts/pruebas/verificar_db_sesion1.py
"""
Script de prueba para verificar que la ontología extendida (Base de Datos)
se crea y relaciona correctamente con los nuevos modelos de la Sesión 1.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz de fenix al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from modelos.declarative_base import Base
from modelos.Producto import (
    Producto, HolonRuta, AsignacionRecurso, Formula, InsumoFormula,
    EspecificacionCalidad, CriterioAceptacionEtapa, InvariantePaso
)
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.Recursos import Recurso, RecursoEquipo, UnidadFuncional


def test_ontologia_extendida():
    print("🧪 Iniciando prueba de la ontología extendida...")
    
    # 1. Crear motor en memoria
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    print("✅ Tablas creadas en base de datos en memoria.")
    
    # 2. Iniciar sesión
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # 3. Crear datos base (Taxonomía)
        familia = FamiliaProducto(nombre="Pinturas Base Agua", descripcion="Pinturas solubles en agua")
        tipo_op = TipoDeOperacion(nombre="Dispersion", codigo="DIS", descripcion="Dispersar pigmentos")
        patron = PatronDeRuta(nombre="Patron Dispersion Dilucion", descripcion="Flujo base", familiaProducto=familia)
        etapa = EtapaRuta(nombre="Etapa Dispersion", patronRuta=patron, tipoDeOperacion=tipo_op)
        
        session.add_all([familia, tipo_op, patron, etapa])
        session.flush()  # Para obtener IDs
        
        # 4. Crear productos (final e insumo)
        producto_final = Producto(
            codigo="LATEX-BLANCO",
            nombre="Látex Blanco Estándar",
            es_fabricado=True,
            familia=familia
        )
        materia_prima = Producto(
            codigo="PIGM-TITANIO",
            nombre="Dióxido de Titanio",
            es_insumo=True,
            familia=familia
        )
        
        session.add_all([producto_final, materia_prima])
        session.flush()
        
        # 5. Crear HolonRuta y Asignación de Recurso
        recurso_base = Recurso(
            codigo="DISP-D22",
            nombre="Dispersor Industrial D22",
            tipo="equipo",
            descripcion="Dispersor 500L"
        )
        session.add(recurso_base)
        session.flush()
        
        unidad_func = UnidadFuncional(codigo="SECC-DISP", nombre="Sección Dispersión")
        session.add(unidad_func)
        session.flush()

        recurso = RecursoEquipo(
            id=recurso_base.id,
            modelo="D22",
            unidad_id=unidad_func.id,
            disponible=True
        )
        session.add(recurso)
        session.flush()

        ruta = HolonRuta(
            nombre="Ruta Standard Látex",
            producto=producto_final,
            patron=patron,
            activa=True
        )
        asignacion = AsignacionRecurso(
            holon_ruta=ruta,
            etapa=etapa,
            recurso_id=recurso_base.id,  # Referenciar por ID del recurso base
            duracion_estimada_min=45.0,
            costo_por_hora_real=120.0
        )
        
        session.add_all([ruta, asignacion])
        session.flush()
        
        # 6. Crear Fórmula con Insumo asociado a etapa
        formula = Formula(holon_ruta=ruta, cantidad_producir_lote=1000.0, unidad_medida="kg")
        insumo = InsumoFormula(
            formula=formula,
            producto=materia_prima,
            nombre_insumo="Dióxido de Titanio",
            cantidad=150.0,
            unidad="kg",
            costo_unitario_estimado=2.5,
            etapa=etapa  # Asociado a la Etapa de Dispersión
        )
        
        session.add_all([formula, insumo])
        session.flush()
        
        # 7. Crear Especificación de Calidad y Criterio de Aceptación
        especificacion = EspecificacionCalidad(
            nombre="Viscosidad KU",
            descripcion="Viscosidad medida en unidades Krebs",
            limite_minimo=90.0,
            limite_maximo=110.0,
            valor_objetivo=100.0,
            unidad_medida="KU"
        )
        criterio = CriterioAceptacionEtapa(
            holon_ruta=ruta,
            etapa=etapa,
            especificacion=especificacion
        )
        
        session.add_all([especificacion, criterio])
        session.flush()
        
        # 8. Crear Invariante de Paso
        invariante = InvariantePaso(
            asignacion_recurso=asignacion,
            parametro="Temperatura",
            valor_maximo=55.0,
            unidad="C"
        )
        
        session.add(invariante)
        session.commit()
        print("✅ Datos de prueba insertados y persistidos con éxito.")
        
        # 9. Validaciones de Relaciones
        print("\n🔍 Validando relaciones en BD:")
        
        # Consulta de Insumo y su Etapa asociada
        insumo_db = session.query(InsumoFormula).filter_by(nombre_insumo="Dióxido de Titanio").first()
        assert insumo_db is not None
        assert insumo_db.etapa_ruta_id == etapa.id
        assert insumo_db.etapa.nombre == "Etapa Dispersion"
        print(f"   - Insumo '{insumo_db.nombre_insumo}' dosificado en: '{insumo_db.etapa.nombre}' (OK)")
        
        # Consulta de Criterios de Calidad en la Ruta
        ruta_db = session.query(HolonRuta).first()
        assert len(ruta_db.criterios_calidad) == 1
        criterio_db = ruta_db.criterios_calidad[0]
        assert criterio_db.especificacion.nombre == "Viscosidad KU"
        assert criterio_db.etapa.nombre == "Etapa Dispersion"
        print(f"   - Ruta '{ruta_db.nombre}' tiene control de calidad '{criterio_db.especificacion.nombre}' en etapa '{criterio_db.etapa.nombre}' (OK)")
        
        # Consulta de Invariantes en el Recurso Asignado
        asignacion_db = session.query(AsignacionRecurso).first()
        assert len(asignacion_db.invariantes) == 1
        invariante_db = asignacion_db.invariantes[0]
        assert invariante_db.parametro == "Temperatura"
        assert invariante_db.valor_maximo == 55.0
        print(f"   - Asignación en '{asignacion_db.recurso.nombre}' tiene invariante: {invariante_db.parametro} <= {invariante_db.valor_maximo} {invariante_db.unidad} (OK)")
        
        print("\n🎉 ¡Todos los tests de ontología extendida pasaron correctamente!")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error en la prueba: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    test_ontologia_extendida()
