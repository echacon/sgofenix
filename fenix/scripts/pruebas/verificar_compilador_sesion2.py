# sgo/fenix/scripts/pruebas/verificar_compilador_sesion2.py
"""
Script de prueba para verificar que el Compilador de Recetas (Sesión 2)
es capaz de parsear el formato YAML de modelo de proceso y cargarlo en la BD.
"""

import sys
import tempfile
from pathlib import Path

# Agregar el directorio raíz de fenix al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.RedPetri import RedPetri, TransicionRed
from importadores.compilador_recetas import CompiladorRecetas

TEST_YAML = """
nombre: "Proceso dispersion test"
categoria_recurso: DISPERSOR_ALTA
pasos:
  - id: p1
    nombre: "Carga vehiculo"
    duracion: 10 m
    velocidad: baja
  - id: p2
    nombre: "Carga polvos"
    duracion: 15 m
    velocidad: alta
  - id: p3
    nombre: "Dispersion"
    duracion: 20 m
    velocidad: media
  - id: p4
    nombre: "Control Calidad"
    duracion: 10 m
    velocidad: baja
  - id: p5
    nombre: "Descargado"
    duracion: 10 m

transiciones:
  - id: t1
    trigger: "Equipo listo"
    destino: [p1]
  - id: t2
    trigger: "Vehiculo cargado"
    origen: [p1]
    destino: [p2]
  - id: t3
    trigger: "Polvos listos"
    origen: [p2]
    destino: [p3]
  - id: t4
    trigger: "Mezcla completada"
    origen: [p3]
    destino: [p4]
  - id: t5_aprobado
    trigger: "201"
    origen: [p4]
    destino: [p5]
  - id: t5_rechazado
    trigger: "Rechazado"
    origen: [p4]
    destino: [p3] # Retorna a dispersion para reprocesar
"""

def test_compilador():
    print("🧪 Iniciando prueba del compilador de recetas...")

    # 1. Compilar el string YAML conceptualmente
    datos_red = CompiladorRecetas.compilar_yaml_a_dict(TEST_YAML)
    print("✅ Compilación conceptual a diccionario realizada.")

    # Validar lugares
    assert "p1" in datos_red["lugares"]
    assert datos_red["lugares"]["p1"]["name"] == "Carga vehiculo"
    assert datos_red["lugares"]["p1"]["marking_inicial"] == 1
    assert datos_red["lugares"]["p2"]["marking_inicial"] == 0
    print("   - Lugares e inicializaciones (OK)")

    # Validar transiciones y triggers
    assert "t1" in datos_red["transiciones"]
    assert datos_red["transiciones"]["t1"]["trigger"] == "200" # "Equipo listo" -> manual (200)
    assert datos_red["transiciones"]["t5_aprobado"]["trigger"] == "201" # "201" -> mensaje (201)
    assert datos_red["transiciones"]["t5_rechazado"]["trigger"] == "200" # "Rechazado" -> manual (200)
    print("   - Mapeo de triggers (OK)")

    # Validar arcos
    arcos = datos_red["arcos"]
    # t2 conecta p1 -> t2 -> p2
    t2_arcs_in = [a for a in arcos.values() if a["source"] == "p1" and a["target"] == "t2"]
    t2_arcs_out = [a for a in arcos.values() if a["source"] == "t2" and a["target"] == "p2"]
    assert len(t2_arcs_in) == 1
    assert len(t2_arcs_out) == 1

    # t5_rechazado conecta p4 -> t5_rechazado -> p3 (bucle de retorno)
    trech_in = [a for a in arcos.values() if a["source"] == "p4" and a["target"] == "t5_rechazado"]
    trech_out = [a for a in arcos.values() if a["source"] == "t5_rechazado" and a["target"] == "p3"]
    assert len(trech_in) == 1
    assert len(trech_out) == 1
    print("   - Generación de arcos e inyección de bucles de calidad (OK)")

    # 2. Guardar a BD
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Crear un archivo temporal para simular lectura de YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as temp_f:
            temp_f.write(TEST_YAML)
            temp_path = Path(temp_f.name)

        try:
            compiler = CompiladorRecetas()
            red_db = compiler.importar_receta_a_bd(session, temp_path)
            
            # Consultar y validar BD
            red_consultada = session.query(RedPetri).filter_by(nombre="Proceso dispersion test").first()
            assert red_consultada is not None
            assert len(red_consultada.lugares) == 5
            assert len(red_consultada.transiciones) == 6
            assert len(red_consultada.arcos) == 11 # 1 por entrada/salida de transiciones con origen y destino

            # Validar transiciones en tabla detalle
            trans_detalle = session.query(TransicionRed).filter_by(red_petri_id=red_consultada.id).all()
            assert len(trans_detalle) == 6
            
            t5_aprob_db = session.query(TransicionRed).filter_by(red_petri_id=red_consultada.id, id_pnml="t5_aprobado").first()
            assert t5_aprob_db.trigger_type == "201"
            
            t5_rech_db = session.query(TransicionRed).filter_by(red_petri_id=red_consultada.id, id_pnml="t5_rechazado").first()
            assert t5_rech_db.trigger_type == "200"

            print("✅ Datos persistidos correctamente en la base de datos.")
            print("\n🎉 ¡Todos los tests del compilador de recetas de la Sesión 2 pasaron correctamente!")

        finally:
            # Borrar archivo temporal
            if temp_path.exists():
                temp_path.unlink()

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error en la prueba: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    test_compilador()
