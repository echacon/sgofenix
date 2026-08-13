# importadores/cargador_yaml.py

from pathlib import Path
import yaml
from typing import Dict, Any

class CargadorYAML:
    """Carga todos los archivos YAML de configuración"""
    
    CONFIG_DIR = Path(__file__).parent.parent / "config"
    
    @classmethod
    def cargar_todo(cls) -> Dict[str, Any]:
        """Carga y combina toda la configuración"""
        
        config = {}
        
        # Orden de carga (respetando dependencias)
        archivos = [
            "01_familias.yaml",
            "02_tipos_operacion.yaml",
            "03_patrones.yaml",
            "04_recursos.yaml",
            "05_capacidades.yaml",
            "06_productos.yaml",
            "07_conectividad.yaml"
        ]
        
        for archivo in archivos:
            ruta = cls.CONFIG_DIR / archivo
            if ruta.exists():
                with open(ruta, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # Fusionar con config general
                        for key, value in data.items():
                            if key in config:
                                if isinstance(config[key], list):
                                    config[key].extend(value)
                                else:
                                    config[key] = value
                            else:
                                config[key] = value
                        print(f"   ✅ Cargado: {archivo}")
            else:
                print(f"   ⚠️ No existe: {archivo}")
        
        return config
    
    @classmethod
    def cargar_uno(cls, nombre: str) -> Dict:
        """Carga un archivo YAML específico"""
        ruta = cls.CONFIG_DIR / nombre
        if ruta.exists():
            with open(ruta, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}