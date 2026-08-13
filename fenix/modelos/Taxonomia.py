# modelos/Taxonomia

from .declarative_base import Base


from typing import List
from typing import Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from datetime import datetime
from .RutaProducto import RutaProducto


class FamiliaProducto(Base):
    __tablename__ = "familia_producto"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(256))
    patrones: Mapped[List["PatronDeRuta"]] = relationship(back_populates="familiaProducto")
    
    # Usar string para evitar importación circular
    productos: Mapped[List["Producto"]] = relationship(back_populates="familia")

class TipoDeOperacion(Base):
    __tablename__ = "tipo_de_operacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=True)


class PatronDeRuta(Base):
    """Patrón de Ruta - Define la estructura base del proceso"""
    __tablename__ = "patron_de_ruta"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256), nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Familia de producto asociada
    familiaProducto_id: Mapped[int] = mapped_column(ForeignKey("familia_producto.id"))
    
    # Estado
    activo: Mapped[bool] = mapped_column(default=True)
    
    # Relaciones - Usar strings para evitar importación circular
    familiaProducto: Mapped["FamiliaProducto"] = relationship(back_populates="patrones")
    etapasRuta: Mapped[List["EtapaRuta"]] = relationship(back_populates="patronRuta")
    transiciones: Mapped[List["TransicionPatron"]] = relationship(back_populates="patron")
    holones_ruta: Mapped[List["HolonRuta"]] = relationship(back_populates="patron")
    redes_petri: Mapped[List["RedPetri"]] = relationship(back_populates="patron_ruta")
    # Referencia a RutaProducto - usar string
    rutas_producto: Mapped[List["RutaProducto"]] = relationship(back_populates="patron_ruta")
    
    def __repr__(self):
        return f"<PatronDeRuta(id={self.id}, nombre='{self.nombre}')>"
    
class EtapaRuta(Base):
    __tablename__ = "etapa_ruta"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    patronRuta: Mapped["PatronDeRuta"] = relationship(back_populates="etapasRuta")
    patronRuta_id:  Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"))
    tipoDeOperacion: Mapped["TipoDeOperacion"] = relationship()
    tipoDeOperacion_id: Mapped[int] = mapped_column(ForeignKey("tipo_de_operacion.id"))
    arcos_entrada: Mapped[List["TParcoEnt"]] = relationship(back_populates="etapa")
    arcos_salida: Mapped[List["TParcoSal"]] = relationship(back_populates="etapa")


class TransicionPatron(Base):
    __tablename__ = "transicion_patron"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    patron_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"))
    patron: Mapped["PatronDeRuta"] = relationship(back_populates="transiciones")
    arc_ent_l: Mapped[List["TParcoEnt"]] = relationship(back_populates="trans")
    arc_sal_l: Mapped[List["TParcoSal"]] = relationship(back_populates="trans")


""" Arcos que van de una Etapa a una Transicion"""
class TParcoEnt(Base):
    __tablename__ = "tp_arc_ent"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    trans_id:  Mapped[int] = mapped_column(ForeignKey("transicion_patron.id"))
    trans: Mapped["TransicionPatron"] = relationship(back_populates="arc_ent_l")
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"))
    etapa: Mapped["EtapaRuta"] = relationship(back_populates="arcos_entrada")

""" Arcos que van de una Transicion a una Etapa"""
class TParcoSal(Base):
    __tablename__ = "tp_arc_sal"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    trans_id:  Mapped[int] = mapped_column(ForeignKey("transicion_patron.id"))
    trans: Mapped["TransicionPatron"] = relationship(back_populates="arc_sal_l")
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"))
    etapa: Mapped["EtapaRuta"] = relationship(back_populates="arcos_salida")


class TipoRecurso(Base):
    __tablename__ = "tipo_recurso"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(256))
    CapacidadTipoOperacionLista: Mapped[List["CapacidadTipoOperacion"]] = relationship(back_populates="tipoRecurso")


class CapacidadTipoOperacion(Base):
    __tablename__ = "capacidad_tipo_operacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipoRecurso_id: Mapped[int] = mapped_column(ForeignKey("tipo_recurso.id"))
    tipoRecurso: Mapped["TipoRecurso"] = relationship(back_populates="CapacidadTipoOperacionLista")
    tipoOperacion: Mapped["TipoDeOperacion"] = relationship()
    tipoOperacion_id: Mapped[int] = mapped_column(ForeignKey("tipo_de_operacion.id"))
    eficiencia_estimada: Mapped[float] = mapped_column(default=1.0)  # 0 a 1
    costo_por_hora: Mapped[float] = mapped_column(default=0.0)  # costo en moneda local
