from typing import Optional, List
from sqlalchemy import String, ForeignKey, JSON, Float, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base
from .Taxonomia import TipoDeOperacion


class ProcesoModelo(Base):
    """ Describe el comportamiento de un Servicio de Manufactura.
        Es de un tipo de operación
    """
    __tablename__ = "proceso_modelo"
    
    id: Mapped[int] = mapped_column(primary_key=True)

    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    tipoDeOperacion_id: Mapped[int] = mapped_column(ForeignKey("tipo_de_operacion.id"), nullable=True)
    tipoDeOperacion: Mapped["TipoDeOperacion"] = relationship()
    pasos: Mapped[List["ProcesoPaso"]] = relationship(back_populates="procesoModelo")
    transiciones: Mapped[List["ProcesoTransicion"]] = relationship(back_populates="procesoModelo")

class ProcesoPaso(Base):
    """ Describe los pasos dentro de un recurso autónomo para prestar un servicio"""

    __tablename__ = "proceso_paso"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    duracionEstimada: Mapped[float] = mapped_column(Float)

    procesoModelo_id:  Mapped[int] = mapped_column(ForeignKey("proceso_modelo.id"))
    procesoModelo: Mapped["ProcesoModelo"] = relationship(back_populates="pasos")

    arcEntPaso: Mapped[List["PMarcoEnt"]] = relationship(back_populates="paso")
    arcSalPaso: Mapped[List["PMarcoSal"]] = relationship(back_populates="paso")



class ProcesoTransicion(Base):
    """ Describe las transiciones entre pasos"""

    __tablename__ = "proceso_transicion"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    disparador: Mapped[str] = mapped_column(String(64), nullable=True)

    procesoModelo: Mapped["ProcesoModelo"] = relationship(back_populates="transiciones")
    procesoModelo_id: Mapped[int] = mapped_column(ForeignKey("proceso_modelo.id"))

    arcEntTrans: Mapped[List["PMarcoEnt"]] = relationship(back_populates="trans")
    arcSalTrans: Mapped[List["PMarcoSal"]] = relationship(back_populates="trans")

class PMarcoEnt(Base):
    """ Arcos que van de Paso a transcion"""
    __tablename__ = "p_m_arco_ent"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    trans: Mapped["ProcesoTransicion"] = relationship()
    trans_id: Mapped[int] = mapped_column(ForeignKey("proceso_transicion.id"))
    paso: Mapped["ProcesoPaso"] = relationship()
    paso_id: Mapped[int] = mapped_column(ForeignKey("proceso_paso.id"))


class PMarcoSal(Base):
    """ Arcos que van de Paso a transcion"""
    __tablename__ = "p_m_arco_sal"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    trans: Mapped["ProcesoTransicion"] = relationship()
    trans_id: Mapped[int] = mapped_column(ForeignKey("proceso_transicion.id"))
    paso: Mapped["ProcesoPaso"] = relationship()
    paso_id: Mapped[int] = mapped_column(ForeignKey("proceso_paso.id"))




    






