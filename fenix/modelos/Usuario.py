# modelos/Usuario.py

from .declarative_base import Base
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash


class Usuario(Base):
    __tablename__ = "usuario"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    rol: Mapped[str] = mapped_column(String(20))  # 'admin' o 'operador'
    password_hash: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)  # ← Agregar esta línea
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    @property
    def es_admin(self) -> bool:
        return self.rol == 'admin'
    
    @property
    def es_operador(self) -> bool:
        return self.rol == 'operador'