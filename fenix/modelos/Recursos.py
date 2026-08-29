# modelos/Recursos.py - Manteniendo todas las clases SIN herencia polimórfica

from typing import List, Optional
from sqlalchemy import String, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base


class Recurso(Base):
    __tablename__ = "recurso"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)   # ← NUEVO
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # 'equipo' o 'personal'
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    
    equipo: Mapped[Optional["RecursoEquipo"]] = relationship(back_populates="recurso", uselist=False)
    personal: Mapped[Optional["RecursoPersonal"]] = relationship(back_populates="recurso", uselist=False)

class RecursoEquipo(Base):
    """Recurso de tipo equipo/máquina"""
    __tablename__ = "recurso_equipo"
    
    id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), primary_key=True)
    modelo: Mapped[str] = mapped_column(String(50))
    
    # Relación con unidad funcional
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_funcional.id"))
    unidad: Mapped["UnidadFuncional"] = relationship(back_populates="recursos")
    
    # Parámetros operativos
    capacidad_maxima: Mapped[Optional[float]] = mapped_column(Float)
    velocidad_procesamiento: Mapped[Optional[float]] = mapped_column(Float)
    consumo_energia_kw: Mapped[float] = mapped_column(Float, default=0)
    costo_energia_por_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    costo_depreciacion_hora: Mapped[float] = mapped_column(Float, default=0)
    
    # Disponibilidad
    disponible: Mapped[bool] = mapped_column(default=True)
    ultimo_mantenimiento: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Telemetría de Energía Opcional a nivel de Holón
    medidor_energia: Mapped[bool] = mapped_column(default=False)
    edr_actual: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    
    # Relación con Recurso base
    recurso: Mapped["Recurso"] = relationship(back_populates="equipo", foreign_keys=[id])


class RecursoPersonal(Base):
    """Recurso de tipo personal/operador"""
    __tablename__ = "recurso_personal"
    
    id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), primary_key=True)
    
    # Relación con unidad de negocio
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_negocio.id"), nullable=True)
    unidad: Mapped["UnidadNegocio"] = relationship(back_populates="recursos")
    
    # Roles que puede jugar (mantener esta relación)
    roles: Mapped[List["RolJugado"]] = relationship(back_populates="recurso")
    
    # Datos del empleado
    costo_por_hora: Mapped[float] = mapped_column(Float, default=0)
    especialidad: Mapped[Optional[str]] = mapped_column(String(100))
    disponible: Mapped[bool] = mapped_column(default=True)
    
    # Relación con Recurso base
    recurso: Mapped["Recurso"] = relationship(back_populates="personal", foreign_keys=[id])


class UnidadFuncional(Base):
    __tablename__ = 'unidad_funcional'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    
    recursos: Mapped[List["RecursoEquipo"]] = relationship(back_populates="unidad")
    
    unidadesHijas: Mapped[List["UnidadFuncional"]] = relationship(back_populates="unidadPadre")
    unidadPadre_id: Mapped[int] = mapped_column(ForeignKey("unidad_funcional.id"), nullable=True)
    unidadPadre: Mapped["UnidadFuncional"] = relationship(remote_side=[id], back_populates="unidadesHijas")
    
    servicios: Mapped[List["ServicioTecnicoOfrecido"]] = relationship(back_populates="unidadFuncional")
    
    unidadNegocio_id: Mapped[int] = mapped_column(ForeignKey("unidad_negocio.id"), nullable=True)
    unidadNegocio: Mapped["UnidadNegocio"] = relationship(back_populates="unidadesFuncionales")


class ServicioTecnico(Base):
    __tablename__ = 'servicio_tecnico'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(120))


class ServicioTecnicoOfrecido(Base):
    __tablename__ = 'servicio_tecnico_ofrecido'
    id: Mapped[int] = mapped_column(primary_key=True)
    unidadFuncional_id: Mapped[int] = mapped_column(ForeignKey("unidad_funcional.id"))
    unidadFuncional: Mapped["UnidadFuncional"] = relationship(back_populates="servicios")
    servicio_id: Mapped[int] = mapped_column(ForeignKey('servicio_tecnico.id'))
    servicio: Mapped["ServicioTecnico"] = relationship()
    capacidad: Mapped[float]


class UnidadNegocio(Base):
    __tablename__ = 'unidad_negocio'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    
    recursos: Mapped[List["RecursoPersonal"]] = relationship(back_populates='unidad')
    
    unidadesHijas: Mapped[List["UnidadNegocio"]] = relationship(back_populates='unidadPadre')
    unidadPadre_id: Mapped[int] = mapped_column(ForeignKey('unidad_negocio.id'), nullable=True)
    unidadPadre: Mapped["UnidadNegocio"] = relationship(back_populates="unidadesHijas", remote_side=[id])
    
    servicios: Mapped[List["ServicioNegocioOfrecido"]] = relationship(back_populates="unidadNegocio")
    unidadesFuncionales: Mapped[List["UnidadFuncional"]] = relationship(back_populates="unidadNegocio")


class Rol(Base):
    __tablename__ = 'rol'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(250))


class RolJugado(Base):
    __tablename__ = 'rol_jugado'
    id: Mapped[int] = mapped_column(primary_key=True)
    recurso_id: Mapped[int] = mapped_column(ForeignKey('recurso_personal.id'))
    recurso: Mapped["RecursoPersonal"] = relationship(back_populates="roles")
    rol_id: Mapped[int] = mapped_column(ForeignKey('rol.id'))
    rol: Mapped["Rol"] = relationship()
    fechaInicio: Mapped[Optional[str]] = mapped_column(String(20))
    fechaFin: Mapped[Optional[str]] = mapped_column(String(20))


class ServicioNegocio(Base):
    __tablename__ = 'servicio_negocio'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(250))


class ServicioNegocioOfrecido(Base):
    __tablename__ = 'servicio_negocio_ofrecido'
    id: Mapped[int] = mapped_column(primary_key=True)
    unidadNegocio_id: Mapped[int] = mapped_column(ForeignKey('unidad_negocio.id'))
    unidadNegocio: Mapped["UnidadNegocio"] = relationship(back_populates="servicios")
    servicio_id: Mapped[int] = mapped_column(ForeignKey('servicio_negocio.id'))
    servicio: Mapped["ServicioNegocio"] = relationship()
    capacidad: Mapped[float]


class ConexionFisica(Base):
    __tablename__ = "conexion_fisica"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    recurso_origen_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), nullable=False)
    recurso_destino_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    diametro_pulgadas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud_metros: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    material_tuberia: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    flujo_maximo_lps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    perdida_material_pct: Mapped[float] = mapped_column(Float, default=0.0)
    requiere_bombeo: Mapped[bool] = mapped_column(default=False)
    requiere_operador: Mapped[bool] = mapped_column(default=False)
    activa: Mapped[bool] = mapped_column(default=True)
    disponible: Mapped[bool] = mapped_column(default=True)
    ultimo_mantenimiento: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    recurso_origen = relationship("Recurso", foreign_keys=[recurso_origen_id])
    recurso_destino = relationship("Recurso", foreign_keys=[recurso_destino_id])
    
    __table_args__ = (
        UniqueConstraint('recurso_origen_id', 'recurso_destino_id', name='uq_conexion_unica'),
        {'extend_existing': True}
    )