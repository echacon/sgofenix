# modelos/RedPetri.py - Versión unificada

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, JSON, ForeignKey, Boolean, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base
from .Taxonomia import PatronDeRuta
from .Producto import Producto
from .Recursos import Recurso

class RedPetri(Base):
    __tablename__ = "red_petri"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256), nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    
    lugares: Mapped[dict] = mapped_column(JSON)
    transiciones: Mapped[dict] = mapped_column(JSON)
    arcos: Mapped[dict] = mapped_column(JSON)
    
    patron_ruta_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    
    archivo_pnml_origen: Mapped[str] = mapped_column(String(200), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)
    fecha_actualizacion: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    metadatos: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    
    # Relaciones
    patron_ruta: Mapped["PatronDeRuta"] = relationship(back_populates="redes_petri")
    transiciones_detalle: Mapped[List["TransicionRed"]] = relationship(
        back_populates="red", cascade="all, delete-orphan"
    )



class TransicionRed(Base):
    __tablename__ = "transicion_red"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    red_petri_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"))
    id_pnml: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(100))
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual")
    
    red: Mapped["RedPetri"] = relationship(back_populates="transiciones_detalle")


class RefinamientoRed(Base):
    __tablename__ = "refinamiento_red"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    red_padre_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"))
    transicion_padre: Mapped[str] = mapped_column(String(50))
    red_hija_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"))
    eventos: Mapped[dict] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)


class SuscripcionEvento(Base):
    __tablename__ = "suscripcion_evento"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    red_origen_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"))
    evento: Mapped[str] = mapped_column(String(50))
    red_destino_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"))
    accion: Mapped[str] = mapped_column(String(50))
    destino_param: Mapped[str] = mapped_column(String(50))
    parametros: Mapped[dict] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)

class DuracionEstimadaLugar(Base):
    __tablename__ = "duracion_estimada_lugar"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    red_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"), nullable=False)
    lugar_id: Mapped[str] = mapped_column(String(50), nullable=False)
    lugar_nombre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recurso_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recurso.id"), nullable=True)
    cantidad_min_kg: Mapped[float] = mapped_column(Float, default=0.0)
    cantidad_max_kg: Mapped[float] = mapped_column(Float, default=float('inf'))
    duracion_segundos: Mapped[float] = mapped_column(Float, nullable=False)
    costo_operacion_extra: Mapped[float] = mapped_column(Float, default=0.0)
    costo_variable_por_kg: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relaciones (usar strings para evitar circular imports)
    producto: Mapped["Producto"] = relationship(foreign_keys=[producto_id])
    red: Mapped["RedPetri"] = relationship(foreign_keys=[red_id])
    recurso: Mapped[Optional["Recurso"]] = relationship(foreign_keys=[recurso_id])