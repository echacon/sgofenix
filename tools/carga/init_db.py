# scripts/core/init_db.py

import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modelos.declarative_base import Base, engine
from modelos.Usuario import Usuario
from sqlalchemy.orm import Session

def init_database():
    """Crea todas las tablas y un usuario admin por defecto"""
    
    print("🔨 Creando tablas...")
    Base.metadata.drop_all(engine)  # Opcional: limpiar todo (cuidado)
    Base.metadata.create_all(engine)
    
    print("👤 Creando usuario administrador por defecto...")
    session = Session(engine)
    
    admin = Usuario(
        nombre="Administrador",
        email="admin@fenix.local",
        rol="admin",
        activo=True
    )
    admin.set_password("admin123")  # Cambiar en producción
    
    operador = Usuario(
        nombre="Operador",
        email="operador@fenix.local",
        rol="operador",
        activo=True
    )
    operador.set_password("operador123")
    
    session.add(admin)
    session.add(operador)
    session.commit()
    session.close()
    
    print("✅ Base de datos inicializada")
    print("   Admin: admin@fenix.local / admin123")
    print("   Operador: operador@fenix.local / operador123")

if __name__ == "__main__":
    init_database()