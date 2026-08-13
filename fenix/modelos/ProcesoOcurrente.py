# modelos/ProcesoOcurrente.py

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, JSON, Float, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base
from .DocumentosNegocio import OrdenProduccion





class InstanciaRed(Base):
    """Instancia de una red para una orden"""
    __tablename__ = "instancia_red"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("orden_produccion.id"))
    tipo: Mapped[str] = mapped_column(String(10))
    
    patron_ruta_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"), nullable=False)
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=False)
    
    marcado: Mapped[dict] = mapped_column(JSON)
    
    # ===== NUEVO CAMPO =====
    recursos_ocupados: Mapped[dict] = mapped_column(JSON, default={})
    # ========================
    
    token_o: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    token_m: Mapped[Optional[float]] = mapped_column(nullable=True)
    token_c: Mapped[Optional[float]] = mapped_column(nullable=True)
    token_t: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    activa: Mapped[bool] = mapped_column(default=True)
    
    # ===== NUEVOS CAMPOS PARA TERMINACIÓN =====
    completada: Mapped[bool] = mapped_column(default=False)
    tipo_terminacion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lugar_terminacion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # ==========================================
    
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    orden: Mapped["OrdenProduccion"] = relationship(back_populates="instancias")
    eventos: Mapped[List["EventoRed"]] = relationship(back_populates="instancia")


class EventoRed(Base):
    """Registro histórico de eventos disparados"""
    __tablename__ = "evento_red"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("orden_produccion.id"))
    instancia_id: Mapped[int] = mapped_column(ForeignKey("instancia_red.id"))
    
    transicion_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    transicion_nombre: Mapped[str] = mapped_column(String(100))
    
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)
    
    invariantes: Mapped[dict] = mapped_column(JSON)
    
    token_m: Mapped[Optional[float]] = mapped_column(nullable=True)
    token_c: Mapped[Optional[float]] = mapped_column(nullable=True)
    costo_real_paso: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Relaciones
    instancia: Mapped["InstanciaRed"] = relationship(back_populates="eventos")