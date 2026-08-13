# modelos/Colaevento.py
"""Modelo para cola de eventos asíncronos (SCADA / Tablets)"""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .declarative_base import Base


class ColaEvento(Base):
    __tablename__ = "cola_evento"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificación
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Red ahora es opcional (puede inferirse desde el recurso)
    red_nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Nuevo: recurso físico que originó el evento
    recurso_nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Nombre de la transición/evento semántico
    transicion_nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    # Datos adicionales (operador, timestamp, etc.)
    datos: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    # Estado del evento: pendiente, procesando, completado, error
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)

    # Control de reintentos
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    # Fechas
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    fecha_procesamiento: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ColaEvento(id={self.id}, orden={self.orden_id}, recurso='{self.recurso_nombre}', red='{self.red_nombre}', trans='{self.transicion_nombre}', estado={self.estado})>"