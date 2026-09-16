# scripts/diagnosticar_asignacion.py
"""Diagnostica el problema con AsignacionRecurso"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("🔍 DIAGNOSTICANDO ASIGNACIONRECURSO")
print("=" * 60)

# 1. Verificar importación de Recurso
print("\n1. Importando Recurso...")
try:
    from modelos.Recurso import Recurso, RecursoEquipo, RecursoPersonal
    print("   ✅ Recurso importado correctamente")
    print(f"   Tipo de Recurso: {Recurso}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Verificar importación de AsignacionRecurso
print("\n2. Importando AsignacionRecurso...")
try:
    from modelos.Producto import AsignacionRecurso
    print("   ✅ AsignacionRecurso importado correctamente")
    
    # Verificar sus atributos
    print("\n   Atributos de AsignacionRecurso:")
    for attr in dir(AsignacionRecurso):
        if not attr.startswith('_'):          
            print(f"      - {attr}")
            
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Verificar la relación en Producto.py
print("\n3. Leyendo Producto.py...")
try:
    import inspect
    from pathlib import Path
    
    producto_path = Path(__file__).parent.parent / "modelos" / "Producto.py"
    if producto_path.exists():
        with open(producto_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
            
        # Buscar la definición de AsignacionRecurso
        if 'class AsignacionRecurso' in contenido:
            print("   ✅ Clase AsignacionRecurso encontrada")
            
            # Buscar relaciones problemáticas
            lines = contenido.split('\n')
            in_asignacion = False
            for i, line in enumerate(lines):
                if 'class AsignacionRecurso' in line:
                    in_asignacion = True
                elif in_asignacion and 'class ' in line and i > 0:
                    break
                elif in_asignacion and 'relationship' in line:
                    print(f"      Línea {i+1}: {line.strip()[:80]}")
        else:
            print("   ❌ Clase AsignacionRecurso NO encontrada")
    else:
        print(f"   ❌ No existe: {producto_path}")
        
except Exception as e:
    print(f"   ❌ Error leyendo archivo: {e}")

print("\n" + "=" * 60)