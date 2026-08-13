# sgo/fenix/importadores/compilador_recetas.py
"""
Compilador de Recetas (Parser YAML a Red de Petri) para el sistema FÉNIX.
Permite traducir las descripciones de procesos en YAML a la ontología
relacional de Redes de Petri (RedPetri, TransicionRed, etc.) en la base de datos.
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from modelos.RedPetri import RedPetri, TransicionRed

logger = logging.getLogger(__name__)


class CompiladorRecetas:
    """
    Clase para parsear archivos YAML de modelos de proceso y
    compilarlos en estructuras de Red de Petri en la base de datos.
    """

    @staticmethod
    def compilar_yaml_a_dict(yaml_content: str) -> Dict[str, Any]:
        """
        Compila el contenido YAML de un modelo de proceso a la estructura
        interna de Lugares, Transiciones y Arcos requerida por RedPetri.
        """
        try:
            data = yaml.safe_load(yaml_content)
        except Exception as e:
            logger.error(f"Error parsing YAML content: {e}")
            raise ValueError(f"YAML no válido: {e}")

        nombre_red = data.get("nombre", "Red_Compilada")
        pasos = data.get("pasos", [])
        transiciones_yaml = data.get("transiciones", [])

        lugares_json = {}
        transiciones_json = {}
        arcos_dict = {}
        arc_counter = 1

        # 1. Procesar Pasos (Lugares)
        for i, paso in enumerate(pasos):
            pid = paso.get("id")
            if not pid:
                raise ValueError(f"Falta 'id' en el paso en la posición {i}")
            
            # El primer paso de la lista tiene por defecto marca inicial 1
            marcado_inicial = 1 if i == 0 else 0
            
            lugares_json[pid] = {
                "id": pid,
                "name": paso.get("nombre", pid),
                "marking_inicial": marcado_inicial
            }

        # 2. Procesar Transiciones y Arcos
        for i, trans in enumerate(transiciones_yaml):
            tid = trans.get("id")
            if not tid:
                raise ValueError(f"Falta 'id' en la transición en la posición {i}")

            trigger_str = trans.get("trigger", "")
            
            # Mapear trigger legible a los códigos de FÉNIX
            # Si es vacío o no se especifica, es automático (None)
            # Si coincide con 200, 201, 202 se deja. Si es un texto, mapea a '200' (manual/externo)
            trigger_code = None
            if trigger_str:
                trigger_clean = str(trigger_str).strip()
                if trigger_clean in ["200", "201", "202"]:
                    trigger_code = trigger_clean
                else:
                    trigger_code = "200"  # Evento manual del operador

            transiciones_json[tid] = {
                "id": tid,
                "name": trans.get("trigger", tid) or tid,
                "trigger": trigger_code
            }

            # Generar Arcos de Entrada (origen -> transicion)
            orígenes = trans.get("origen", [])
            if isinstance(orígenes, str):
                orígenes = [orígenes]
            for orig_id in orígenes:
                if orig_id not in lugares_json:
                    logger.warning(f"Lugar de origen '{orig_id}' no definido en pasos para la transición '{tid}'")
                
                arc_id = f"arc_{arc_counter}"
                arcos_dict[arc_id] = {
                    "source": orig_id,
                    "target": tid,
                    "peso": 1
                }
                arc_counter += 1

            # Generar Arcos de Salida (transicion -> destino)
            destinos = trans.get("destino", [])
            if isinstance(destinos, str):
                destinos = [destinos]
            for dest_id in destinos:
                if dest_id not in lugares_json:
                    logger.warning(f"Lugar de destino '{dest_id}' no definido en pasos para la transición '{tid}'")
                
                arc_id = f"arc_{arc_counter}"
                arcos_dict[arc_id] = {
                    "source": tid,
                    "target": dest_id,
                    "peso": 1
                }
                arc_counter += 1

        return {
            "nombre": nombre_red,
            "categoria_recurso": data.get("categoria_recurso"),
            "lugares": lugares_json,
            "transiciones": transiciones_json,
            "arcos": arcos_dict
        }

    def importar_receta_a_bd(self, session: Session, yaml_path: Path, patron_id: Optional[int] = None) -> RedPetri:
        """
        Compila un archivo YAML y lo guarda o actualiza en la base de datos.
        """
        logger.info(f"Compilando y cargando modelo de proceso desde {yaml_path}")
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()

        red_datos = self.compilar_yaml_a_dict(yaml_content)
        nombre_red = red_datos["nombre"]

        # Buscar si ya existe la red
        red = session.query(RedPetri).filter_by(nombre=nombre_red).first()
        if red:
            logger.info(f"Red '{nombre_red}' ya existe. Actualizando...")
            red.fecha_actualizacion = datetime.now()
        else:
            logger.info(f"Creando nueva red '{nombre_red}'")
            red = RedPetri(nombre=nombre_red)
            session.add(red)

        red.descripcion = f"Compilado de receta para {red_datos['categoria_recurso']}"
        red.lugares = red_datos["lugares"]
        red.transiciones = red_datos["transiciones"]
        red.arcos = red_datos["arcos"]
        red.activo = True
        red.archivo_pnml_origen = str(yaml_path)
        
        if patron_id:
            red.patron_ruta_id = patron_id

        # Guardar en metadatos información adicional del YAML
        red.metadatos = {
            "categoria_recurso": red_datos["categoria_recurso"],
            "compilado_desde": "YAML"
        }

        session.flush()

        # Re-crear transiciones detalladas en la tabla transicion_red para consistencia
        session.query(TransicionRed).filter_by(red_petri_id=red.id).delete()
        for tid, tinfo in red_datos["transiciones"].items():
            trans_db = TransicionRed(
                red_petri_id=red.id,
                id_pnml=tid,
                nombre=tinfo["name"],
                trigger_type=tinfo["trigger"] if tinfo["trigger"] else "automatico"
            )
            session.add(trans_db)

        session.commit()
        logger.info(f"✅ Red '{nombre_red}' persistida con éxito en base de datos.")
        return red
