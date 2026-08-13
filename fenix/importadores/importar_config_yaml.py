# script/importadores/importador_yaml.py

from pathlib import Path
import yaml

class ConfiguracionGlobal:
    """Carga configuración global desde config/*.yaml"""
    
    CONFIG_PATH = Path(__file__).parent.parent / "config"
    
    @classmethod
    def cargar_taxonomia(cls):
        with open(cls.CONFIG_PATH / "taxonomia.yaml") as f:
            return yaml.safe_load(f)
    
    @classmethod
    def cargar_recursos(cls):
        with open(cls.CONFIG_PATH / "recursos.yaml") as f:
            return yaml.safe_load(f)
    
    @classmethod
    def cargar_productos(cls):
        with open(cls.CONFIG_PATH / "productos.yaml") as f:
            return yaml.safe_load(f)

class ConfiguracionRuta:
    """Carga configuración específica de una ruta"""
    
    RUTAS_PATH = Path(__file__).parent.parent / "rutas_producto"
    
    @classmethod
    def cargar(cls, nombre_ruta: str):
        ruta_path = cls.RUTAS_PATH / nombre_ruta
        
        # Cargar YAML específico si existe
        yaml_path = ruta_path / "config.yaml"
        if yaml_path.exists():
            with open(yaml_path) as f:
                return yaml.safe_load(f)
        
        # Si no, cargar desde JSON (backward compatibility)
        json_path = ruta_path / "config.json"
        if json_path.exists():
            import json
            with open(json_path) as f:
                return json.load(f)
        
        raise FileNotFoundError(f"No config found for {nombre_ruta}")