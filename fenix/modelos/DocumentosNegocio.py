# modelos/DocumentosNegocio.py

"""
Documentos del Negocio
Ordenes de Producción, Pedidos, Facturas, etc.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, JSON, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .RutaProducto import RutaProducto




class OrdenProduccion(Base):
    __tablename__ = "orden_produccion"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    numero_orden: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"))
    
    # Referencia a la ruta de producto
    ruta_producto_id: Mapped[int] = mapped_column(ForeignKey("ruta_producto.id"), nullable=True)
    
    cantidad: Mapped[float] = mapped_column(default=0)
    unidad: Mapped[str] = mapped_column(String(20), default='L')
    
    # Estado del proceso
    estado: Mapped[str] = mapped_column(String(50), default='pendiente')
    
    # Fechas
    fecha_solicitud: Mapped[datetime] = mapped_column(default=datetime.now)
    fecha_requerida: Mapped[datetime] = mapped_column(nullable=True)
    fecha_inicio: Mapped[datetime] = mapped_column(nullable=True)
    fecha_fin: Mapped[datetime] = mapped_column(nullable=True)
    
    # Prioridad (1=normal, 2=urgente, 3=express)
    prioridad: Mapped[int] = mapped_column(default=1)
    
    # Datos adicionales
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)
    cliente: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Datos ocurrentes (para seguimiento)
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=True)
    plazo_entrega: Mapped[datetime] = mapped_column(nullable=True)
    archivada: Mapped[bool] = mapped_column(default=False)
    fecha_completado: Mapped[datetime] = mapped_column(nullable=True)
    fecha_archivo: Mapped[datetime] = mapped_column(nullable=True)
    asignacion_recursos: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Ejemplo: {"dispersion": {"recurso_id": 5, "nombre": "Dispersor_22"},
    #           "dilucion": {"recurso_id": 8, "nombre": "Diluidor_1"}}
    
    # Relaciones - Usar strings
    producto = relationship("Producto", foreign_keys=[producto_id])
    instancias = relationship("InstanciaRed", back_populates="orden")
    ruta_producto = relationship("RutaProducto", back_populates="ordenes")
    version_ruta_id: Mapped[Optional[int]] = mapped_column(ForeignKey("version_ruta.id"), nullable=True)
    version_ruta: Mapped[Optional["VersionRuta"]] = relationship("VersionRuta", back_populates="ordenes")
    
    def __repr__(self):
        return f"<OrdenProduccion(id={self.id}, num='{self.numero_orden}', estado='{self.estado}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_orden': self.numero_orden,
            'producto_id': self.producto_id,
            'ruta_producto_id': self.ruta_producto_id,
            'cantidad': self.cantidad,
            'estado': self.estado,
            'fecha_solicitud': self.fecha_solicitud.isoformat() if self.fecha_solicitud else None,
            'fecha_requerida': self.fecha_requerida.isoformat() if self.fecha_requerida else None,
            'prioridad': self.prioridad
        }

class Pedido(Base):
    """Pedido de cliente - Nivel superior a OrdenProduccion"""
    __tablename__ = "pedido"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    numero_pedido: Mapped[str] = mapped_column(String(50), unique=True)
    cliente: Mapped[str] = mapped_column(String(100))
    fecha_pedido: Mapped[datetime] = mapped_column(default=datetime.now)
    fecha_entrega: Mapped[datetime] = mapped_column(nullable=True)
    estado: Mapped[str] = mapped_column(String(50), default='recibido')
    # recibido, en_planificacion, en_produccion, despachado, entregado
    
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Pedido(id={self.id}, num='{self.numero_pedido}', cliente='{self.cliente}')>"


class DocumentoEstado(Base):
    """Historial de estados de documentos (auditoría)"""
    __tablename__ = "documento_estado"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    documento_tipo: Mapped[str] = mapped_column(String(50))  # 'orden_produccion', 'pedido'
    documento_id: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(50))
    observacion: Mapped[str] = mapped_column(Text, nullable=True)
    usuario: Mapped[str] = mapped_column(String(100), nullable=True)
    fecha: Mapped[datetime] = mapped_column(default=datetime.now)
    
    def __repr__(self):
        return f"<DocumentoEstado({self.documento_tipo}#{self.documento_id}: {self.estado})>"
    