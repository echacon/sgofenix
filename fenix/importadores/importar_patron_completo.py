# scripts/importadores/importar_patron_completo.py

"""
Importa un patrón de ruta completo:
- Datos del patrón (desde YAML o manual)
- Redes PNML (desde directorio)
- Reglas de encadenamiento (desde Excel)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos.Taxonomia import PatronDeRuta, FamiliaProducto
from modelos.RedPetri import RedPetri
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from scripts.importadores.importar_pnml import importar_pnml
from scripts.importadores.importar_encadenamiento import importar_encadenamiento

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def importar_patron_completo(
    session: Session,
    patron_nombre: str,
    familia_nombre: str,
    directorio_redes: Path,
    excel_encadenamiento: Path = None,
    descripcion: str = ""
) -> Optional[int]:
    """
    Importa un patrón completo con sus redes y encadenamiento.
    
    Args:
        session: Sesión SQLAlchemy
        patron_nombre: Nombre del patrón (ej: "DIS-DIL")
        familia_nombre: Nombre de la familia (ej: "Látex")
        directorio_redes: Directorio con archivos .pnml de este patrón
        excel_encadenamiento: Ruta al Excel con reglas (opcional)
        descripcion: Descripción del patrón
    
    Returns:
        ID del patrón creado
    """
    
    # 1. Buscar o crear la familia
    familia = session.query(FamiliaProducto).filter_by(nombre=familia_nombre).first()
    if not familia:
        logger.warning(f"⚠️ Familia no encontrada: {familia_nombre}. Creándola...")
        familia = FamiliaProducto(nombre=familia_nombre, descripcion=f"Familia {familia_nombre}")
        session.add(familia)
        session.flush()
    
    # 2. Buscar o crear el patrón
    patron = session.query(PatronDeRuta).filter_by(nombre=patron_nombre).first()
    if patron:
        logger.info(f"📐 Actualizando patrón existente: {patron_nombre}")
        patron.descripcion = descripcion or patron.descripcion
        patron.familiaProducto_id = familia.id
    else:
        logger.info(f"📐 Creando nuevo patrón: {patron_nombre}")
        patron = PatronDeRuta(
            nombre=patron_nombre,
            descripcion=descripcion,
            version="1.0",
            familiaProducto_id=familia.id,
            activo=True
        )
        session.add(patron)
        session.flush()
    
    # 3. Importar todas las redes PNML del directorio
    logger.info(f"📄 Importando redes desde: {directorio_redes}")
    
    redes_ids = []
    for pnml_file in directorio_redes.glob("*.pnml"):
        # Usar importar_pnml con el patrón asociado
        from scripts.importadores.importar_pnml import importar_pnml
        
        red_id = importar_pnml(
            session=session,
            pnml_path=pnml_file,
            patron_nombre=patron_nombre,  # Asocia al patrón
            red_nombre_override=None  # Usa el nombre del archivo
        )
        if red_id:
            redes_ids.append(red_id)
            logger.info(f"   ✅ Red importada: {pnml_file.name} (ID: {red_id})")
    
    # 4. Importar encadenamiento (si existe)
    if excel_encadenamiento and excel_encadenamiento.exists():
        logger.info(f"🔗 Importando encadenamiento desde: {excel_encadenamiento}")
        
        nombre_config = f"Encadenamiento_{patron_nombre}"
        
        # Buscar o crear configuración de encadenamiento para este patrón
        encadenamiento = session.query(ConfiguracionEncadenamiento).filter_by(
            patron_ruta_id=patron.id
        ).first()
        
        if not encadenamiento:
            encadenamiento = session.query(ConfiguracionEncadenamiento).filter_by(
                nombre=nombre_config
            ).first()
        
        # Importar reglas desde Excel
        importar_encadenamiento(
            session=session,
            excel_path=excel_encadenamiento,
            nombre_config=nombre_config
        )
        
        # Asegurar que está vinculado al patrón
        encadenamiento = session.query(ConfiguracionEncadenamiento).filter_by(
            nombre=nombre_config
        ).first()
        
        if encadenamiento:
            encadenamiento.patron_ruta_id = patron.id
            encadenamiento.descripcion = f"Handshakes para patrón {patron_nombre}"
            session.commit()
            logger.info(f"   ✅ Encadenamiento vinculado al patrón")
    else:
        logger.warning(f"⚠️ No se encontró archivo de encadenamiento: {excel_encadenamiento}")
    
    session.commit()
    
    logger.info(f"🎉 Patrón '{patron_nombre}' importado completo:")
    logger.info(f"   - ID Patrón: {patron.id}")
    logger.info(f"   - Redes: {len(redes_ids)}")
    logger.info(f"   - Familia: {familia.nombre}")
    
    return patron.id


def importar_todos_los_patrones(session: Session, base_path: Path):
    """
    Importa todos los patrones desde la estructura de directorios estándar.
    
    Estructura esperada:
    base_path/
    ├── patrones/
    │   ├── DIS-DIL/
    │   │   ├── redes/
    │   │   │   ├── dispersion.pnml
    │   │   │   ├── dilucion.pnml
    │   │   │   └── integradora.pnml
    │   │   └── encadenamiento.xlsx
    │   ├── DIS-MOL-DIL/
    │   │   ├── redes/
    │   │   └── encadenamiento.xlsx
    │   └── ...
    └── config/
        └── 03_patrones.yaml (metadatos)
    """
    
    # Cargar metadatos desde YAML
    import yaml
    yaml_path = base_path / "config" / "03_patrones.yaml"
    
    if not yaml_path.exists():
        logger.error(f"❌ No se encuentra {yaml_path}")
        return
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    for patron_data in data.get('patrones', []):
        patron_nombre = patron_data['nombre']
        familia_nombre = patron_data.get('familia', 'General')
        descripcion = patron_data.get('descripcion', '')
        
        # Buscar directorio del patrón
        patron_dir = base_path / "patrones" / patron_nombre
        redes_dir = patron_dir / "redes"
        excel_path = patron_dir / "encadenamiento.xlsx"
        
        if not redes_dir.exists():
            logger.warning(f"⚠️ Directorio de redes no encontrado: {redes_dir}")
            continue
        
        importar_patron_completo(
            session=session,
            patron_nombre=patron_nombre,
            familia_nombre=familia_nombre,
            directorio_redes=redes_dir,
            excel_encadenamiento=excel_path if excel_path.exists() else None,
            descripcion=descripcion
        )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--patron", type=str, help="Nombre del patrón a importar")
    parser.add_argument("--familia", type=str, default="General")
    parser.add_argument("--redes_dir", type=str, help="Directorio con archivos .pnml")
    parser.add_argument("--excel", type=str, help="Archivo Excel de encadenamiento")
    parser.add_argument("--db", type=str, default="sqlite:///fenix.db")
    parser.add_argument("--todos", action="store_true", help="Importar todos los patrones")
    parser.add_argument("--base_path", type=str, default=".", help="Ruta base del proyecto")
    
    args = parser.parse_args()
    
    engine = create_engine(args.db)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    if args.todos:
        importar_todos_los_patrones(session, Path(args.base_path))
    elif args.patron and args.redes_dir:
        importar_patron_completo(
            session=session,
            patron_nombre=args.patron,
            familia_nombre=args.familia,
            directorio_redes=Path(args.redes_dir),
            excel_encadenamiento=Path(args.excel) if args.excel else None
        )
    else:
        print("Uso:")
        print("  --todos --base_path .")
        print("  --patron DIS-DIL --redes_dir ./patrones/DIS-DIL/redes --excel ./patrones/DIS-DIL/encadenamiento.xlsx")
    
    session.close()