# modelos/MensajePendiente.py
"""Modelo para mensajes pendientes entre redes"""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .declarative_base import Base


class MensajePendiente(Base):
    """Mensaje pendiente de procesamiento entre redes"""
    __tablename__ = "mensaje_pendiente"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Origen
    red_origen: Mapped[str] = mapped_column(String(100))
    transicion_origen: Mapped[str] = mapped_column(String(50))
    
    # Destino
    red_destino: Mapped[str] = mapped_column(String(100))
    evento: Mapped[str] = mapped_column(String(50))
    transicion_destino: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # Datos del mensaje
    datos: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # Estado
    consumido: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Fechas
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fecha_consumo: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MensajePendiente(id={self.id}, {self.red_origen}.{self.transicion_origen} -> {self.red_destino}.{self.evento})>"