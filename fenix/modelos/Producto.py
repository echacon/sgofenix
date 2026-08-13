#modelos/Producto.py
#Modulo para la descripción del producto y su modelo

"""
Modelo de Producto - Refactorizado
Representa productos concretos que instancian patrones de taxonomía
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import String, ForeignKey, Float, JSON, DateTime, Boolean, Integer, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint

from .declarative_base import Base
from .Taxonomia import FamiliaProducto, PatronDeRuta, EtapaRuta


class Producto(Base):
    """
    Producto concreto que se fabrica.
    Pertenece a una FamiliaProducto (taxonomía).
    """
    __tablename__ = "producto"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    
    # Clasificación (útiles para filtros)
    es_fabricado: Mapped[bool] = mapped_column(default=True)
    es_adquirido: Mapped[bool] = mapped_column(default=False)
    es_final: Mapped[bool] = mapped_column(default=True)
    es_insumo: Mapped[bool] = mapped_column(default=False)
    es_intermedio: Mapped[bool] = mapped_column(default=False)
    
    # Relación con taxonomía
    familia_id: Mapped[int] = mapped_column(ForeignKey("familia_producto.id"), nullable=False)
    familia: Mapped["FamiliaProducto"] = relationship(back_populates="productos")
    
    # Rutas concretas para este producto
    rutas: Mapped[List["HolonRuta"]] = relationship(back_populates="producto", cascade="all, delete-orphan")

class HolonRuta(Base):
    __tablename__ = "holon_ruta"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    
    # Fechas de vigencia
    fecha_desde: Mapped[Optional[str]] = mapped_column(String(20))
    fecha_hasta: Mapped[Optional[str]] = mapped_column(String(20))
    
    # ═══════════════════════════════════════════════════════════════
    # NUEVO: Condiciones genéricas como JSON
    # ═══════════════════════════════════════════════════════════════
    condiciones: Mapped[Dict[str, Any]] = mapped_column(JSON, default={})
    
    # Estado
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relación con producto y familia producto
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=True)
    producto = relationship("Producto", back_populates="rutas")
    
    familia_id: Mapped[Optional[int]] = mapped_column(ForeignKey("familia_producto.id"), nullable=True)
    
    # Relación con taxonomía
    patron_id: Mapped[int] = mapped_column(ForeignKey("patron_de_ruta.id"), nullable=False)
    patron: Mapped["PatronDeRuta"] = relationship(back_populates="holones_ruta")
    
    # Asignaciones concretas
    asignaciones: Mapped[List["AsignacionRecurso"]] = relationship(
        back_populates="holon_ruta", cascade="all, delete-orphan"
    )
    
    # Conexiones reales
    conexiones: Mapped[List["ConexionReal"]] = relationship(
        back_populates="holon_ruta", cascade="all, delete-orphan"
    )
    
    # Fórmula
    formula: Mapped[Optional["Formula"]] = relationship(
        back_populates="holon_ruta", cascade="all, delete-orphan", uselist=False
    )
    
    # Criterios de calidad asociados a esta ruta
    criterios_calidad: Mapped[List["CriterioAceptacionEtapa"]] = relationship(
        back_populates="holon_ruta", cascade="all, delete-orphan"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE UTILIDAD PARA CONDICIONES
    # ═══════════════════════════════════════════════════════════════
    
    def get_condicion(self, key: str, default=None):
        """Obtiene una condición específica"""
        return self.condiciones.get(key, default)
    
    def cumple_condiciones(self, cantidad: float, prioridad: int, 
                           inventario: Dict[str, float] = None) -> bool:
        """
        Verifica si la ruta cumple con todas las condiciones.
        """
        # Rango de lote
        lote_min = self.get_condicion("lote_minimo_kg", 0)
        lote_max = self.get_condicion("lote_maximo_kg", float('inf'))
        
        if cantidad < lote_min or cantidad > lote_max:
            return False
        
        # Prioridad mínima
        prioridad_min = self.get_condicion("prioridad_minima", 1)
        if prioridad < prioridad_min:
            return False
        
        # Condiciones de inventario (si aplica)
        requiere_inventario = self.get_condicion("requiere_inventario")
        if requiere_inventario and inventario:
            tipo = requiere_inventario.get("tipo")
            cantidad_min = requiere_inventario.get("cantidad_minima_kg", 0)
            
            if inventario.get(tipo, 0) < cantidad_min:
                return False
        
        # Otras condiciones personalizadas se pueden agregar aquí
        
        return True

class AsignacionRecurso(Base):
    """
    Asigna un recurso REAL a una etapa abstracta del patrón.
    Ahora usa la tabla base 'recurso' (polimórfica).
    """
    __tablename__ = "asignacion_recurso"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"))
    etapa_ruta_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"))
    recurso_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"))
    
    # Relaciones
    holon_ruta = relationship("HolonRuta", back_populates="asignaciones")
    
    etapa_ruta_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"), nullable=False)
    etapa = relationship("EtapaRuta")
    
    # Recurso REAL (ahora referenciando la tabla base)
    recurso_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"))
    recurso  = relationship("Recurso")  # Importar Recursos primero
    
    # Parámetros concretos de esta asignación
    duracion_estimada_min: Mapped[float] = mapped_column(Float, nullable=False)
    costo_por_hora_real: Mapped[float] = mapped_column(Float, default=0)
    eficiencia_real: Mapped[float] = mapped_column(Float, default=1.0)  # 0 a 1
    
    # Parámetros operativos específicos para esta asignación
    velocidad_procesamiento: Mapped[Optional[float]] = mapped_column(Float)  # L/min, kg/h
    capacidad_maxima_lote: Mapped[Optional[float]] = mapped_column(Float)
    requiere_preparacion_min: Mapped[float] = mapped_column(Float, default=0)
    requiere_limpieza_min: Mapped[float] = mapped_column(Float, default=0)
    
    # Invariantes operativos del paso
    invariantes: Mapped[List["InvariantePaso"]] = relationship(
        back_populates="asignacion_recurso", cascade="all, delete-orphan"
    )


class ConexionReal(Base):
    """
    Define CÓMO se conectan físicamente dos etapas/recursos.
    Esto NO está en la taxonomía porque depende del producto y lote.
    """
    __tablename__ = "conexion_real"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relaciones
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=False)
    holon_ruta: Mapped["HolonRuta"] = relationship(back_populates="conexiones")
    
    etapa_origen_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"), nullable=False)
    etapa_origen: Mapped["EtapaRuta"] = relationship(foreign_keys=[etapa_origen_id])
    
    etapa_destino_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"), nullable=False)
    etapa_destino: Mapped["EtapaRuta"] = relationship(foreign_keys=[etapa_destino_id])
    
    # Tipo de conexión (determina lógica de ejecución)
    tipo_conexion: Mapped[str] = mapped_column(String(50), nullable=False)
    # Opciones: "MANUAL", "BOMBA", "TUBERIA_GRAVEDAD", "NEUMATICO", "SUSPENSION"
    
    # Parámetros de la conexión
    perdida_material_pct: Mapped[float] = mapped_column(Float, default=0)  # 0.05 = 5%
    tiempo_transvase_min: Mapped[float] = mapped_column(Float, default=0)
    costo_operacion: Mapped[float] = mapped_column(Float, default=0)
    
    # Si requiere operador específico
    requiere_operador: Mapped[bool] = mapped_column(default=False)
    costo_operador_por_hora: Mapped[float] = mapped_column(Float, default=0)
    
    # Si la conexión puede ejecutarse en paralelo con otras
    permite_paralelismo: Mapped[bool] = mapped_column(default=False)
    
    # Condiciones adicionales (JSON string para flexibilidad)
    condiciones_json: Mapped[Optional[str]] = mapped_column(String(500))


class Formula(Base):
    """
    Fórmula del producto (Bill of Materials).
    Define insumos y cantidades para producir el lote.
    """
    __tablename__ = "formula"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=False, unique=True)
    holon_ruta: Mapped["HolonRuta"] = relationship(back_populates="formula")
    
    cantidad_producir_lote: Mapped[float] = mapped_column(Float, nullable=False)  # litros, kg
    unidad_medida: Mapped[str] = mapped_column(String(20), default="L")
    
    # Insumos (materias primas)
    insumos: Mapped[List["InsumoFormula"]] = relationship(
        back_populates="formula", cascade="all, delete-orphan"
    )


class InsumoFormula(Base):
    """
    Insumo específico para una fórmula.
    Referencia a otro Producto (materia prima) o a un insumo externo.
    """
    __tablename__ = "insumo_formula"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    formula_id: Mapped[int] = mapped_column(ForeignKey("formula.id"), nullable=False)
    formula: Mapped["Formula"] = relationship(back_populates="insumos")
    
    # Puede ser un producto interno o un nombre genérico
    producto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("producto.id"))
    producto: Mapped[Optional["Producto"]] = relationship()
    
    nombre_insumo: Mapped[str] = mapped_column(String(100), nullable=False)  # "Agua", "Resina XYZ"
    cantidad: Mapped[float] = mapped_column(Float, nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), default="kg")
    
    costo_unitario_estimado: Mapped[float] = mapped_column(Float, default=0)

    # Etapa específica donde se adiciona el insumo (opcional)
    etapa_ruta_id: Mapped[Optional[int]] = mapped_column(ForeignKey("etapa_ruta.id"), nullable=True)
    etapa: Mapped[Optional["EtapaRuta"]] = relationship("EtapaRuta")


class EspecificacionCalidad(Base):
    """
    Especificación de calidad requerida para un producto (pH, Viscosidad, etc.).
    """
    __tablename__ = "especificacion_calidad"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., pH, Viscosidad KU, Finura Hegman
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))
    limite_minimo: Mapped[Optional[float]] = mapped_column(Float)
    limite_maximo: Mapped[Optional[float]] = mapped_column(Float)
    valor_objetivo: Mapped[Optional[float]] = mapped_column(Float)
    unidad_medida: Mapped[Optional[str]] = mapped_column(String(20))


class CriterioAceptacionEtapa(Base):
    """
    Enlaza una etapa de proceso específica con una especificación de calidad.
    """
    __tablename__ = "criterio_aceptacion_etapa"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=False)
    etapa_ruta_id: Mapped[int] = mapped_column(ForeignKey("etapa_ruta.id"), nullable=False)
    especificacion_id: Mapped[int] = mapped_column(ForeignKey("especificacion_calidad.id"), nullable=False)
    
    # Relaciones
    holon_ruta: Mapped["HolonRuta"] = relationship("HolonRuta", back_populates="criterios_calidad")
    etapa: Mapped["EtapaRuta"] = relationship("EtapaRuta")
    especificacion: Mapped["EspecificacionCalidad"] = relationship("EspecificacionCalidad")


class InvariantePaso(Base):
    """
    Define valores continuos permitidos para un parámetro en un paso de proceso específico.
    (ej. Temperatura < 55°C, Velocidad del agitador entre 500 y 1000 RPM).
    """
    __tablename__ = "invariante_paso"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    asignacion_recurso_id: Mapped[int] = mapped_column(ForeignKey("asignacion_recurso.id"), nullable=False)
    parametro: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Temperatura", "Velocidad"
    valor_minimo: Mapped[Optional[float]] = mapped_column(Float)
    valor_maximo: Mapped[Optional[float]] = mapped_column(Float)
    unidad: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Relaciones
    asignacion_recurso: Mapped["AsignacionRecurso"] = relationship(
        "AsignacionRecurso", back_populates="invariantes"
    )


# Actualizar FamiliaProducto en Taxonomia.py para que tenga productos
# Agregar esta línea a la clase FamiliaProducto existente:
# productos: Mapped[List["Producto"]] = relationship(back_populates="familia")