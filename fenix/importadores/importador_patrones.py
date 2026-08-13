# importadores/importador_patrones.py (versión corregida)

"""
Importador de patrones de ruta.
Escanea importacion/pendientes/, valida, importa a BD y mueve a procesados/
"""

import sys
import shutil
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

RAIZ_PROYECTO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos.declarative_base import Base
from modelos.Taxonomia import FamiliaProducto, PatronDeRuta
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.RedPetri import RedPetri, TransicionRed
from utils.parser_pnml import cargar_red_desde_pnml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImportadorPatrones:
    def __init__(self, session, base_path: Path):
        self.session = session
        self.base_path = Path(base_path)
        
        self.dir_pendientes = self.base_path / "importacion" / "pendientes"
        self.dir_procesados = self.base_path / "importacion" / "procesados"
        self.dir_errores = self.base_path / "importacion" / "errores"
        
        for d in [self.dir_pendientes, self.dir_procesados, self.dir_errores]:
            d.mkdir(parents=True, exist_ok=True)
    
    def escanear_pendientes(self) -> List[Path]:
        """Retorna lista de patrones pendientes"""
        if not self.dir_pendientes.exists():
            return []
        return [d for d in self.dir_pendientes.iterdir() if d.is_dir()]
    
    def validar_patron(self, patron_dir: Path) -> Dict[str, Any]:
        """Valida que el patrón esté bien formado"""
        errores = []
        advertencias = []
        metadatos = {}
        
        # Verificar directorio redes/
        redes_dir = patron_dir / "redes"
        if not redes_dir.exists():
            errores.append("No existe directorio 'redes/'")
        else:
            pnml_files = list(redes_dir.glob("*.pnml"))
            if not pnml_files:
                errores.append("No hay archivos .pnml en redes/")
            else:
                metadatos['pnml_files'] = [f.name for f in pnml_files]
        
        # Verificar metadatos.yaml
        yaml_file = patron_dir / "metadatos.yaml"
        if yaml_file.exists():
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    metadatos.update(yaml.safe_load(f) or {})
            except Exception as e:
                advertencias.append(f"Error leyendo metadatos.yaml: {e}")
        else:
            metadatos['nombre'] = patron_dir.name
            advertencias.append("Usando nombre del directorio como nombre del patrón")
        
        # Verificar encadenamiento (opcional)
        excel_file = patron_dir / "encadenamiento.xlsx"
        if not excel_file.exists():
            advertencias.append("No hay archivo encadenamiento.xlsx")
        
        # Validar metadatos mínimos
        if 'nombre' not in metadatos:
            errores.append("Falta 'nombre' en metadatos")
        
        if 'familia' not in metadatos:
            metadatos['familia'] = "General"
            advertencias.append("Usando familia 'General'")
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'advertencias': advertencias,
            'metadatos': metadatos
        }
    
    def importar_pnml(self, pnml_path: Path, patron_id: int) -> Optional[int]:
        petri_net = cargar_red_desde_pnml(str(pnml_path))
        if not petri_net:
            logger.error(f"   ❌ Error parseando: {pnml_path.name}")
            return None

        lugares = {pid: {'nombre': p.nombre, 'marking_inicial': p.marking_inicial}
                for pid, p in petri_net.places.items()}
        transiciones = {tid: {'nombre': t.nombre, 'trigger': t.trigger}
                        for tid, t in petri_net.transitions.items()}
        arcos = {aid: {'source': a.source, 'target': a.target, 'peso': a.peso}
                for aid, a in petri_net.arcs.items()}

        red = self.session.query(RedPetri).filter_by(nombre=petri_net.nombre).first()
        if red:
            red.lugares = lugares
            red.transiciones = transiciones
            red.arcos = arcos
            red.patron_ruta_id = patron_id
            red.archivo_pnml_origen = str(pnml_path)
            logger.info(f"   ✅ Actualizada red: {petri_net.nombre}")
        else:
            red = RedPetri(
                nombre=petri_net.nombre,
                descripcion=f"Importada de {pnml_path.name}",
                version=1,
                lugares=lugares,
                transiciones=transiciones,
                arcos=arcos,
                patron_ruta_id=patron_id,
                activo=True,
                archivo_pnml_origen=str(pnml_path)
            )
            self.session.add(red)
            logger.info(f"   ✅ Creada red: {petri_net.nombre}")

        self.session.flush()

        # Reconstruir transiciones (siempre desde petri_net, para mantener sincronía)
        self.session.query(TransicionRed).filter_by(red_petri_id=red.id).delete()
        for tid, trans in petri_net.transitions.items():
            trans_bd = TransicionRed(
                red_petri_id=red.id,
                id_pnml=tid,
                nombre=trans.nombre,
                trigger_type=trans.trigger if trans.trigger else 'none'
            )
            self.session.add(trans_bd)
        self.session.flush()

        return red.id
        
    def importar_encadenamiento(self, excel_path: Path, patron_id: int, patron_nombre: str):
        """Importa reglas de encadenamiento desde Excel"""
        import pandas as pd
        
        df = pd.read_excel(excel_path, sheet_name="Feuil1")
        
        reglas = {}
        for _, row in df.iterrows():
            red_origen = str(row['red_origen']).strip()
            transicion_origen = str(row['transicion_origen']).strip()
            red_destino = str(row['red_destino']).strip()
            evento_destino = str(row['evento_destino']).strip()
            
            key = f"{red_origen}.{transicion_origen}"
            if key not in reglas:
                reglas[key] = []
            reglas[key].append({
                "red_destino": red_destino,
                "evento_destino": evento_destino
            })
        
        nombre_config = f"Encadenamiento_{patron_nombre}"
        config = self.session.query(ConfiguracionEncadenamiento).filter_by(
            nombre=nombre_config
        ).first()
        
        if config:
            config.reglas = reglas
            config.patron_ruta_id = patron_id
            logger.info(f"   ✅ Actualizado encadenamiento: {nombre_config}")
        else:
            config = ConfiguracionEncadenamiento(
                nombre=nombre_config,
                red_principal_pnml="",
                descripcion=f"Handshakes para {patron_nombre}",
                reglas=reglas,
                patron_ruta_id=patron_id,
                activo=True
            )
            self.session.add(config)
            logger.info(f"   ✅ Creado encadenamiento: {nombre_config}")
    
    def almacenar_en_bd(self, patron_dir: Path, validacion: Dict[str, Any]) -> Optional[int]:
        """Almacena el patrón en la base de datos"""
        metadatos = validacion['metadatos']
        patron_nombre = metadatos['nombre']
        familia_nombre = metadatos['familia']
        
        # Buscar o crear familia
        familia = self.session.query(FamiliaProducto).filter_by(nombre=familia_nombre).first()
        if not familia:
            familia = FamiliaProducto(nombre=familia_nombre, descripcion=f"Familia {familia_nombre}")
            self.session.add(familia)
            self.session.flush()
            logger.info(f"   📁 Creada familia: {familia_nombre}")
        
        # Buscar o crear patrón
        patron = self.session.query(PatronDeRuta).filter_by(nombre=patron_nombre).first()
        if patron:
            logger.info(f"   📐 Actualizando patrón: {patron_nombre}")
        else:
            patron = PatronDeRuta(
                nombre=patron_nombre,
                descripcion=metadatos.get('descripcion', ''),
                version="1.0",
                familiaProducto_id=familia.id,
                activo=True
            )
            self.session.add(patron)
            self.session.flush()
            logger.info(f"   📐 Creado patrón: {patron_nombre}")
        
        # Importar redes PNML
        redes_dir = patron_dir / "redes"
        for pnml_file in redes_dir.glob("*.pnml"):
            self.importar_pnml(pnml_file, patron.id)
        
        # Importar encadenamiento
        excel_file = patron_dir / "encadenamiento.xlsx"
        if excel_file.exists():
            self.importar_encadenamiento(excel_file, patron.id, patron_nombre)
        
        self.session.commit()
        return patron.id
       
    def marcar_como_procesado(self, patron_dir: Path, patron_id: int = None):
        """Mueve el patrón a procesados/ con timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = self.dir_procesados / f"{patron_dir.name}_{timestamp}"
        shutil.move(str(patron_dir), str(destino))
        logger.info(f"   📦 Patrón movido a: {destino.name}")
        
        if patron_id:
            with open(destino / "importado.txt", "w") as f:
                f.write(f"Patrón importado a BD con ID: {patron_id}\n")
                f.write(f"Fecha: {datetime.now().isoformat()}\n")
    
    def marcar_como_error(self, patron_dir: Path, errores: List[str]):
        """Mueve el patrón a errores/ con archivo de error"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = self.dir_errores / f"{patron_dir.name}_{timestamp}"
        shutil.move(str(patron_dir), str(destino))
        
        with open(destino / "error.log", "w") as f:
            f.write("ERRORES DE VALIDACIÓN\n")
            f.write("=====================\n")
            for error in errores:
                f.write(f"- {error}\n")
            f.write(f"\nFecha: {datetime.now().isoformat()}\n")
        
        logger.warning(f"   ⚠️ Patrón movido a errores: {destino.name}")
    
    def procesar_pendientes(self):
        """Procesa todos los patrones pendientes"""
        pendientes = self.escanear_pendientes()
        if not pendientes:
            logger.info("📭 No hay patrones pendientes en importacion/pendientes/")
            return
        
        logger.info(f"📦 Procesando {len(pendientes)} patrón(es) pendiente(s)...")
        logger.info("=" * 60)
        
        for patron_dir in pendientes:
            logger.info(f"\n🔍 Validando: {patron_dir.name}")
            
            validacion = self.validar_patron(patron_dir)
            
            for adv in validacion['advertencias']:
                logger.warning(f"   ⚠️ {adv}")
            
            if not validacion['valido']:
                logger.error(f"   ❌ Patrón inválido: {len(validacion['errores'])} errores")
                for err in validacion['errores']:
                    logger.error(f"      - {err}")
                self.marcar_como_error(patron_dir, validacion['errores'])
                continue
            
            logger.info(f"   ✅ Patrón válido. Almacenando en BD...")
            patron_id = self.almacenar_en_bd(patron_dir, validacion)
            
            if patron_id:
                self.marcar_como_procesado(patron_dir, patron_id)
            else:
                self.marcar_como_error(patron_dir, ["Error almacenando en base de datos"])
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Procesamiento completado")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="sqlite:///fenix.db")
    parser.add_argument("--base_path", type=str, default=".")
    parser.add_argument("--once", action="store_true", help="Procesar una sola vez")
    parser.add_argument("--intervalo", type=int, default=60, help="Intervalo en segundos")
    
    args = parser.parse_args()
    
    engine = create_engine(args.db)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    importador = ImportadorPatrones(session, Path(args.base_path))
    
    if args.once:
        importador.procesar_pendientes()
    else:
        # Si no existe ejecutar_ciclo, se puede implementar o simplemente llamar a procesar_pendientes
        importador.procesar_pendientes()
    
    session.close()


if __name__ == "__main__":
    main()