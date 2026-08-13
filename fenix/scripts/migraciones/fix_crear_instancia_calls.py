# scripts/fix_crear_instancia_calls.py
"""Corrige todas las llamadas a crear_instancia que faltan el parámetro pnml_path"""

import re
from pathlib import Path

def fix_files():
    archivos = [
        Path(__file__).parent.parent / 'scripts' / 'depurar_paso_a_paso.py',
        Path(__file__).parent.parent / 'servicios' / 'orquestador.py'
    ]
    
    for archivo in archivos:
        if not archivo.exists():
            print(f"⚠️ {archivo} no encontrado")
            continue
        
        print(f"\n📝 Procesando: {archivo.name}")
        
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar patrones de crear_instancia sin pnml_path
        patron = r"(motor\.crear_instancia\([^)]*?marcado_inicial\s*=\s*[^,)]+)(\))"
        
        # Reemplazar agregando pnml_path
        nuevo_contenido = re.sub(
            patron,
            r'\1, pnml_path=str(pnml_full_path)\2',
            contenido
        )
        
        # Verificar si hubo cambios
        if nuevo_contenido != contenido:
            # Crear backup
            backup = archivo.with_suffix('.py.bak')
            with open(backup, 'w', encoding='utf-8') as f:
                f.write(contenido)
            print(f"   ✅ Backup creado: {backup.name}")
            
            # Guardar cambios
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            print(f"   ✅ Corregido: se agregó pnml_path")
        else:
            print(f"   ⚠️ No se encontró el patrón o ya está corregido")

if __name__ == "__main__":
    fix_files()