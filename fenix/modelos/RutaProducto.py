# modelos/RutaProducto.py
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .Taxonomia import PatronDeRuta
    from .DocumentosNegocio import OrdenProduccion


class RutaProducto(Base):
    """Ruta de Producto - Define el proceso completo para fabricar un producto"""
    __tablename__ = "ruta_producto"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    version: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(256), nullable=True)
    
    # Archivos de configuración
    config_path: Mapped[str] = mapped_column(String(256))
    base_path: Mapped[str] = mapped_column(String(256))
    
    # Producto asociado
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"))
    
    # Relación con taxonomía
    patron_ruta_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"), nullable=True)
    
    # Estado
    activo: Mapped[bool] = mapped_column(default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.now)
    fecha_actualizacion: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # Cache de configuración (JSON)
    config_cache: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # Relaciones - Usar strings para evitar importación circular
    producto = relationship("Producto", foreign_keys=[producto_id])
    patron_ruta = relationship("PatronDeRuta", back_populates="rutas_producto")
    ordenes = relationship("OrdenProduccion", back_populates="ruta_producto")
    
    def __repr__(self):
        return f"<RutaProducto(id={self.id}, nombre='{self.nombre}', version='{self.version}')>"
    
    def obtener_config(self) -> dict:
        """Obtiene la configuración (desde cache o archivo)"""
        if self.config_cache:
            return self.config_cache
        
        import json
        from pathlib import Path
        
        config_path = Path(self.config_path)
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_cache = json.load(f)
                return self.config_cache
        
        return {}