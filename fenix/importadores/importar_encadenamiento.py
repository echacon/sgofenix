# # scripts/importadores/importar_encadenamiento.py

"""Importa reglas de encadenamiento desde Excel a la BD"""

import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from modelos.Encadenamiento import ConfiguracionEncadenamiento


def normalizar_nombre_red(nombre: str) -> str:
    """Elimina extensión .pnml y espacios, manteniendo el nombre limpio"""
    # Quitar .pnml si existe
    if nombre.lower().endswith('.pnml'):
        nombre = nombre[:-5]
    return nombre.strip()

def importar_encadenamiento(session: Session, excel_path: Path, 
                           nombre_config: str = "Encadenamiento_Principal") -> int:
    """
    Importa reglas de encadenamiento desde Excel (hoja Feuil1)
    Los nombres de redes se normalizan (sin .pnml
    
    Args:
        session: Sesión de SQLAlchemy
        excel_path: Ruta al archivo Excel
        nombre_config: Nombre de la configuración
    
    Returns:
        Número de reglas importadas
    """
    if not excel_path.exists():
        raise FileNotFoundError(f"No se encontró: {excel_path}")
    
    # Leer hoja Feuil1
    df = pd.read_excel(excel_path, sheet_name="Feuil1")
    
    # Construir reglas en formato JSON
    reglas = {}
    for _, row in df.iterrows():
        red_origen = normalizar_nombre_red(str(row['red_origen']).strip())
        transicion_origen = str(row['transicion_origen']).strip()
        red_destino = normalizar_nombre_red(str(row['red_destino']).strip())
        evento_destino = str(row['evento_destino']).strip()
        
        key = f"{red_origen}.{transicion_origen}"
        
        if key not in reglas:
            reglas[key] = []
        
        reglas[key].append({
            "red_destino": red_destino,
            "evento_destino": evento_destino
        })
    
    # Buscar o crear configuración
    config = session.query(ConfiguracionEncadenamiento).filter_by(
        nombre=nombre_config
    ).first()
    
    total_reglas = sum(len(v) for v in reglas.values())
    
    if config:
        config.reglas = reglas
        print(f"   ✅ Actualizada configuración: {nombre_config}")
    else:
        config = ConfiguracionEncadenamiento(
            nombre=nombre_config,
            red_principal_pnml="",
            descripcion="Reglas de encadenamiento importadas desde Excel",
            reglas=reglas,
            activo=True
        )
        session.add(config)
        print(f"   ✅ Creada configuración: {nombre_config}")
    
    session.commit()
    print(f"   📬 {len(reglas)} claves origen, {total_reglas} reglas totales")
    
    return total_reglas


if __name__ == "__main__":
    import argparse
    from sqlalchemy import create_engine
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", type=str, default="encadenamiento.xlsx")
    parser.add_argument("--db", type=str, default="sqlite:///fenix.db")
    parser.add_argument("--nombre", type=str, default="Encadenamiento_Principal")
    args = parser.parse_args()
    
    engine = create_engine(args.db)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    importar_encadenamiento(session, Path(args.excel), args.nombre)
    
    session.close()