# modelos/Recursos.py - Modelos del Holón Recurso (Supply Side) y Conectividad Física
"""
Módulo de representación ontológica del Lado de la Oferta (Supply Side) en el marco PPR Holónico.

Formalismo de Referencia:
-------------------------
1. Holón Genérico (Ec. 1):
   H = <id, type, A, C, H+>
   donde `id` es el identificador único, `type in {Product, Resource}`, `A` son los atributos
   de instancia, `C` es el conjunto de holones hijos y `H+` es el holón padre en la jerarquía
   de agregación (representado mediante `UnidadFuncional` y `UnidadNegocio`).

2. Holón Recurso (Resource Holon - RH, Ec. 3):
   RH = <id, S, P, Gamma, kappa, omega, delta, mu, Omega, Psi>
   - S: Conjunto de servicios técnicos ofrecidos (`ServicioTecnicoOfrecido`).
   - P: Redes de Petri de pasos de proceso asociadas al servicio.
   - Gamma: Función de rendimiento másico local gamma(p) in (0, 1] (`rendimiento_nominal`).
   - kappa: Tasa horaria de costo de energía y servicios industriales (`consumo_energia_kw * costo_energia_por_kwh`).
   - omega: Tasa horaria de mano de obra directa (`RecursoPersonal.costo_por_hora`).
   - delta: Tasa horaria de depreciación y desgaste de maquinaria (`costo_depreciacion_hora`).
   - mu: Tasa horaria de costos indirectos de gestión / overhead de planta (`costo_overhead_hora`).
   - Omega: Calendario de disponibilidad nominal (`disponible`).
   - Psi: Agenda dinámica de intervalos de reserva comprometidos por órdenes en curso.

3. Topología de Conectividad Física (K subseteq RH x RH):
   Modelada por la clase `ConexionFisica`, define qué pares de recursos (R_a, R_b) cuentan
   con enlace físico de transporte (tuberías, bombas, mangueras, multiplexores) para ejecutar
   etapas consecutivas (E_i, E_{i+1}).
"""

from typing import List, Optional, Any
from sqlalchemy import String, ForeignKey, Float, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base


class Recurso(Base):
    """
    Entidad base del Holón Recurso (RH).
    Agrupa de forma polimórfica recursos físicos de equipamiento (`RecursoEquipo`)
    y recursos de operación humana (`RecursoPersonal`), e incluye la agenda dinámica
    de reservas temporales Psi_R (Ec. 3).
    """
    __tablename__ = "recurso"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # 'equipo' o 'personal'
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    agenda: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # Agenda dinámica Psi_R (Ec. 3)
    
    equipo: Mapped[Optional["RecursoEquipo"]] = relationship(back_populates="recurso", uselist=False)
    personal: Mapped[Optional["RecursoPersonal"]] = relationship(back_populates="recurso", uselist=False)


class RecursoEquipo(Base):
    """
    Holón de Equipamiento Físico / Estación de Trabajo.
    Encapsula las tasas operativas basadas en actividad (ABC), el rendimiento
    másico nominal (gamma) y el indicador no intrusivo de condición energética (EDR).

    Correspondencia Matemática (Ec. 3 y Ec. 15):
    - kappa(R) = consumo_energia_kw * costo_energia_por_kwh
    - kappa_eff(R) = EDR(R) * kappa(R)
    - delta(R) = costo_depreciacion_hora
    - mu(R) = costo_overhead_hora
    - gamma(R) = rendimiento_nominal in (0, 1]
    """
    __tablename__ = "recurso_equipo"
    
    id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), primary_key=True)
    modelo: Mapped[Optional[str]] = mapped_column(String(50), default="Estándar", nullable=True)
    
    # Relación con unidad funcional (Holón Padre H+ en la jerarquía física)
    unidad_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unidad_funcional.id"), nullable=True)
    unidad: Mapped[Optional["UnidadFuncional"]] = relationship(back_populates="recursos")
    
    # Parámetros de capacidad y cinemática operativa
    capacidad_maxima: Mapped[Optional[float]] = mapped_column(Float)
    velocidad_procesamiento: Mapped[Optional[float]] = mapped_column(Float)
    rendimiento_nominal: Mapped[float] = mapped_column(Float, default=0.98)  # Factor de recuperación másica gamma in (0, 1]
    
    # Tasas horarias de Costeo Basado en Actividades (ABC): vector Phi = [kappa, omega, delta, mu]^T
    consumo_energia_kw: Mapped[float] = mapped_column(Float, default=0)
    costo_energia_por_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    costo_depreciacion_hora: Mapped[float] = mapped_column(Float, default=0)
    costo_overhead_hora: Mapped[float] = mapped_column(Float, default=12.0)  # Tasa mu_R de gestión/overhead
    
    # Disponibilidad nominal (Omega)
    disponible: Mapped[bool] = mapped_column(default=True)
    ultimo_mantenimiento: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Telemetría de Energía Opcional a nivel de Holón y Monitoreo de Condición (Ec. 15)
    medidor_energia: Mapped[bool] = mapped_column(default=False)
    edr_actual: Mapped[Optional[float]] = mapped_column(Float, default=1.0)  # Energy Deviation Ratio EDR(R)
    
    # Relación con Recurso base
    recurso: Mapped["Recurso"] = relationship(back_populates="equipo", foreign_keys=[id])


class RecursoPersonal(Base):
    """
    Recurso de tipo Personal / Operador de Planta.
    Aporta la tasa horaria de mano de obra directa (omega) al vector de costos ABC Phi(p).
    """
    __tablename__ = "recurso_personal"
    
    id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), primary_key=True)
    
    # Relación con unidad de negocio
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_negocio.id"), nullable=True)
    unidad: Mapped["UnidadNegocio"] = relationship(back_populates="recursos")
    
    # Roles que puede jugar
    roles: Mapped[List["RolJugado"]] = relationship(back_populates="recurso")
    
    # Datos del empleado (Tasa omega)
    costo_por_hora: Mapped[float] = mapped_column(Float, default=0)
    especialidad: Mapped[Optional[str]] = mapped_column(String(100))
    disponible: Mapped[bool] = mapped_column(default=True)
    
    # Relación con Recurso base
    recurso: Mapped["Recurso"] = relationship(back_populates="personal", foreign_keys=[id])


class UnidadFuncional(Base):
    """
    Holón Contenedor Físico (H+): agrupa jerárquicamente equipos de planta (C subseteq 2^H)
    y declara los servicios técnicos ofrecidos en esa sección de la planta.
    """
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
    """Catálogo de servicios de transformación técnica S (ej. Dispersión, Molienda, Dilución)."""
    __tablename__ = 'servicio_tecnico'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(120))


class ServicioTecnicoOfrecido(Base):
    """Asociación entre una UnidadFuncional y los servicios técnicos S que provee."""
    __tablename__ = 'servicio_tecnico_ofrecido'
    id: Mapped[int] = mapped_column(primary_key=True)
    unidadFuncional_id: Mapped[int] = mapped_column(ForeignKey("unidad_funcional.id"))
    unidadFuncional: Mapped["UnidadFuncional"] = relationship(back_populates="servicios")
    servicio_id: Mapped[int] = mapped_column(ForeignKey('servicio_tecnico.id'))
    servicio: Mapped["ServicioTecnico"] = relationship()
    capacidad: Mapped[float]


class UnidadNegocio(Base):
    """Holón Organizacional / Administrativo de la empresa."""
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
    """Rol operativo desempeñado por el personal de planta."""
    __tablename__ = 'rol'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(250))


class RolJugado(Base):
    """Asignación temporal de un Rol a un RecursoPersonal."""
    __tablename__ = 'rol_jugado'
    id: Mapped[int] = mapped_column(primary_key=True)
    recurso_id: Mapped[int] = mapped_column(ForeignKey('recurso_personal.id'))
    recurso: Mapped["RecursoPersonal"] = relationship(back_populates="roles")
    rol_id: Mapped[int] = mapped_column(ForeignKey('rol.id'))
    rol: Mapped["Rol"] = relationship()
    fechaInicio: Mapped[Optional[str]] = mapped_column(String(20))
    fechaFin: Mapped[Optional[str]] = mapped_column(String(20))


class ServicioNegocio(Base):
    """Servicio de nivel organizacional o de gestión."""
    __tablename__ = 'servicio_negocio'
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(String(250))


class ServicioNegocioOfrecido(Base):
    """Capacidad de servicio de negocio ofrecida por una UnidadNegocio."""
    __tablename__ = 'servicio_negocio_ofrecido'
    id: Mapped[int] = mapped_column(primary_key=True)
    unidadNegocio_id: Mapped[int] = mapped_column(ForeignKey('unidad_negocio.id'))
    unidadNegocio: Mapped["UnidadNegocio"] = relationship(back_populates="servicios")
    servicio_id: Mapped[int] = mapped_column(ForeignKey('servicio_negocio.id'))
    servicio: Mapped["ServicioNegocio"] = relationship()
    capacidad: Mapped[float]


class ConexionFisica(Base):
    """
    Grafo de Conectividad Física de Planta: K subseteq RH x RH.
    Representa tuberías, bombas, mangueras o multiplexores entre dos recursos físicos
    (recurso_origen_id -> recurso_destino_id). Se emplea en la Fase 1 del Algoritmo 1
    para la poda de factibilidad estructural y el cálculo de mermas de trasvase.
    """
    __tablename__ = "conexion_fisica"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    recurso_origen_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), nullable=False)
    recurso_destino_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="TUBERIA", nullable=False)
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