# modelos/Encadenamiento.py

from datetime import datetime
from sqlalchemy import String, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .declarative_base import Base

class ConfiguracionEncadenamiento(Base):
    """Configuración de encadenamiento entre redes"""
    __tablename__ = "configuracion_encadenamiento"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))  # ej: "Encadenamiento_IntegracionRedes_V4"
    red_principal_pnml: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(String(100))
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # Reglas de encadenamiento (JSON)
    # Cada regla: {red_origen, evento_origen, red_destino, evento_destino, transicion_destino}
    reglas: Mapped[dict] = mapped_column(JSON)
    
    # Relación opcional con patrón de ruta
    patron_ruta_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"), nullable=True)
    
    # Metadatos
    fecha_importacion: Mapped[datetime] = mapped_column(default=datetime.now)
    activo: Mapped[bool] = mapped_column(default=True)  # ← Campo agregado