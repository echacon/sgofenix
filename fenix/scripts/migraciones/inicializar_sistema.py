# scripts/inicializar_sistema.py
"""
Inicializa el sistema desde cero:
1. Crea las tablas en BD
2. Carga las 3 redes Petri desde PNML a la BD
3. Carga la configuración de encadenamiento desde Excel
4. Verifica que todo esté correcto
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modelos.declarative_base import Base
from modelos.RedPetri import RedPetri
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from utils.parser_pnml import cargar_red_desde_pnml

# Configuración
DB_PATH = Path(__file__).parent.parent / "fenix.db"
PNML_DIR = Path(__file__).parent.parent / "static" / "archivospnml"
EXCEL_PATH = PNML_DIR / "encadenamiento.xlsx"

# Redes a cargar
REDES = [
    "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
    "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
    "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2",
]


def crear_tablas():
    """Crea todas las tablas en BD"""
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    Base.metadata.drop_all(engine)  # Limpia todo
    Base.metadata.create_all(engine)  # Crea tablas
    print("✅ Tablas creadas")
    return engine


def cargar_redes(session):
    """Carga las 3 redes Petri desde PNML a BD"""
    for nombre in REDES:
        ruta = PNML_DIR / f"{nombre}.pnml"
        if not ruta.exists():
            print(f"❌ Red no encontrada: {ruta}")
            continue
        
        red_pnml = cargar_red_desde_pnml(str(ruta))
        if not red_pnml:
            print(f"❌ Error cargando PNML: {nombre}")
            continue
        
        # Serializar a JSON para guardar en BD
        red_bd = RedPetri(
            nombre=nombre,
            descripcion=f"Red {nombre}",
            version="1.0",
            lugares=json.dumps({pid: {"nombre": p.nombre, "marcado_inicial": p.marking_inicial} 
                               for pid, p in red_pnml.places.items()}),
            transiciones=json.dumps({tid: {"nombre": t.nombre, "trigger_type": t.trigger_type}
                                    for tid, t in red_pnml.transitions.items()}),
            arcos=json.dumps({
                "entradas": {tid: [{"source": a.source, "peso": a.peso} for a in arcos]
                            for tid, arcos in red_pnml.arcos_entrada.items()},
                "salidas": {tid: [{"target": a.target, "peso": a.peso} for a in arcos]
                           for tid, arcos in red_pnml.arcos_salida.items()}
            }),
            activo=True
        )
        session.add(red_bd)
        print(f"✅ Red cargada: {nombre}")
    
    session.commit()
    print(f"\n📊 Total redes en BD: {session.query(RedPetri).count()}")


def cargar_encadenamiento(session):
    """Carga reglas de encadenamiento desde Excel"""
    if not EXCEL_PATH.exists():
        print(f"⚠️ Excel no encontrado: {EXCEL_PATH}")
        return
    
    import pandas as pd
    df = pd.read_excel(EXCEL_PATH)
    
    # Construir estructura de reglas
    reglas = {}
    for _, row in df.iterrows():
        red_origen = row['red_origen'].replace('.pnml', '')  # ← Limpiar .pnml
        trans_origen = row['transicion_origen']
        red_destino = row['red_destino'].replace('.pnml', '')  # ← Limpiar .pnml
        evento = row['evento_destino']
        
        if red_origen not in reglas:
            reglas[red_origen] = {}
        reglas[red_origen][trans_origen] = {
            'red_destino': red_destino,
            'evento': evento
        }
    
    # Guardar configuración
    config = ConfiguracionEncadenamiento(
        nombre="Encadenamiento_Complejo_V1",
        red_principal_pnml="Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
        reglas=reglas,
        activo=True
    )
    session.add(config)
    session.commit()
    
    print(f"✅ Encadenamiento cargado: {len(reglas)} redes origen")
    for red, r in reglas.items():
        print(f"   - {red}: {len(r)} reglas")


def verificar(session):
    """Verifica que todo esté cargado correctamente"""
    print("\n" + "="*50)
    print("VERIFICACIÓN")
    print("="*50)
    
    # Redes
    redes = session.query(RedPetri).all()
    print(f"\n📊 Redes ({len(redes)}):")
    for r in redes:
        print(f"   ✅ {r.nombre}")
    
    # Encadenamiento
    config = session.query(ConfiguracionEncadenamiento).filter_by(activo=True).first()
    if config:
        print(f"\n📋 Encadenamiento: {config.nombre}")
        print(f"   Reglas para {len(config.reglas)} redes origen")
    else:
        print("\n⚠️ No hay configuración de encadenamiento activa")


def main():
    print("="*50)
    print("INICIALIZACIÓN DEL SISTEMA")
    print("="*50)
    
    # 1. Crear tablas
    engine = crear_tablas()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 2. Cargar redes
    print("\n📁 Cargando redes Petri...")
    cargar_redes(session)
    
    # 3. Cargar encadenamiento
    print("\n🔗 Cargando encadenamiento...")
    cargar_encadenamiento(session)
    
    # 4. Verificar
    verificar(session)
    
    session.close()
    print("\n✅ Sistema inicializado correctamente")
    print(f"📁 Base de datos: {DB_PATH}")


if __name__ == "__main__":
    main()