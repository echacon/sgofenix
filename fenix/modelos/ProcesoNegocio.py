# paquete ProcesoNegocio
from .declarative_base import Base
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from typing import List


class ProcesoNegocio(Base):
    __tablename__='proceso_negocio'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    documento: Mapped["DocumentoNegocio"] = relationship(uselist= False, back_populates="procesoAsociado")
    operaciones: Mapped[List["OperacionNegocio"]] = relationship(back_populates="modeloProcNeg")
    transiciones: Mapped[List["TransicionProcNeg"]] =relationship(back_populates="modeloProcNeg")
    arcosEntrada: Mapped[List["ArcoEntrProcNeg"]] =relationship(back_populates="modeloProcNeg")
    arcosSalida: Mapped[List["ArcoSalidaProcNeg"]] =relationship(back_populates="modeloProcNeg")


class OperacionNegocio(Base):
    __tablename__ = 'operacion_negocio'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    pnid: Mapped[str] = mapped_column(String(8))
    marcacion: Mapped[int] # marcacion inicial
    servicio: Mapped[str] = mapped_column(String(50)) # Antes 'competencia'
    modeloProcNeg_id: Mapped[int] = mapped_column(ForeignKey("proceso_negocio.id"))
    modeloProcNeg: Mapped["ProcesoNegocio"] = relationship(back_populates="operaciones")



class TransicionProcNeg(Base):
    __tablename__ = "proceso_negocio_trans"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20))
    pnid: Mapped[str] = mapped_column(String(8))
    tipoDisparador: Mapped[int]
    rol: Mapped[str] = mapped_column(String(20))
    mensaje: Mapped[str] = mapped_column(String(20)) # Símbolos desde otro sistema
    tiempo: Mapped[int] #en minutos desde el ingreso al lugar de entrada
    mensajeSalida: Mapped[str] = mapped_column(String(60)) 
    modeloProcNeg_id: Mapped[int] = mapped_column(ForeignKey("proceso_negocio.id"))
    modeloProcNeg: Mapped["ProcesoNegocio"] = relationship(back_populates="transiciones")

class ArcoEntrProcNeg(Base):
    __tablename__ = "proceso_negocio_arc_ent"
    id: Mapped[int] = mapped_column(primary_key=True)
    modeloProcNeg_id: Mapped[int] = mapped_column(ForeignKey("proceso_negocio.id"))
    modeloProcNeg: Mapped["ProcesoNegocio"] = relationship(back_populates="arcosEntrada")
    es_inhibidor: Mapped[bool]
    lugar: Mapped[str] = mapped_column(String(8))
    trans: Mapped[str] = mapped_column(String(8))

class ArcoSalidaProcNeg(Base):
    __tablename__ = "proceso_negocio_arc_sal"
    id: Mapped[int] = mapped_column(primary_key=True)
    modeloProcNeg_id: Mapped[int] = mapped_column(ForeignKey("proceso_negocio.id"))
    modeloProcNeg: Mapped["ProcesoNegocio"] = relationship(back_populates="arcosSalida")
    lugar: Mapped[str] = mapped_column(String(8))
    trans: Mapped[str] = mapped_column(String(8))


class DocumentoNegocio(Base):
    __tablename__ = "documento_negocio"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    procesoAsociado_id = mapped_column(ForeignKey("proceso_negocio.id"))
    procesoAsociado: Mapped["ProcesoNegocio"] = relationship(back_populates="documento")
    fechaCreacion: Mapped[str] = mapped_column(String(20))
    creador_id: Mapped[int] = mapped_column(nullable=True) #creador del documento
    organizacion_id: Mapped[int] #unidad de negocio
    renglones: Mapped[List["Renglon"]] = relationship(back_populates="documento")
    documentosHijos: Mapped[List["DocumentoNegocio"]] = relationship(back_populates="documentoPadre")
    documentoPadre_id = mapped_column( ForeignKey("documento_negocio.id"))
    documentoPadre: Mapped["DocumentoNegocio"] = relationship(remote_side = [id], back_populates="documentosHijos")
    enproceso: Mapped[bool]
    completado: Mapped[bool]
    rechazado: Mapped[bool]

class Renglon(Base):
    __tablename__ = "documento_renglon"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto: Mapped[str] =  mapped_column(String(20))
    productoReal: Mapped[int] = mapped_column(nullable = True) # id de la instancia real del producto en inventario
    cantidad: Mapped[float]
    precio: Mapped[float]
    documento_id = mapped_column(ForeignKey("documento_negocio.id"))
    documento: Mapped["DocumentoNegocio"] = relationship(back_populates="renglones")
