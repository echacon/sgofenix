#modelos/Versionamiento.py
"""
Modelos de Versionamiento - Permiten trazabilidad completa de cambios
en la configuración del sistema.

Filosofía:
- Cada cambio significativo genera una nueva versión
- Las órdenes de producción referencian la versión de ruta que usaron
- Se puede hacer "time travel" para auditoría y análisis histórico
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Float, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .declarative_base import Base


class VersionRuta(Base):
    """
    Versión completa de una ruta de producción.
    
    Una versión congela todos los componentes que definen cómo se fabrica
    un producto: el patrón, los recursos asignados, las redes PNML, y las
    reglas de encadenamiento.
    
    Las órdenes de producción se vinculan a la versión activa en el momento
    de su creación. Esto permite que cambios posteriores no afecten órdenes
    ya en curso o finalizadas.
    """
    __tablename__ = "version_ruta"
    __table_args__ = (
        UniqueConstraint('nombre', 'version_semver', name='uq_version_ruta_nombre_vers'),
        {'extend_existing': True}
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Identificación
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    version_semver: Mapped[str] = mapped_column(String(20), nullable=False)  # "1.0.0", "2.1.3"
    
    # Estado del ciclo de vida
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    # Valores posibles:
    # - borrador: En construcción, no se usa para producción
    # - validacion: En prueba, solo órdenes de prueba
    # - activa: Usada para nuevas órdenes de producción
    # - historica: Solo para órdenes existentes, no para nuevas
    # - deprecated: Obsoleta, no usar
    
    # Fechas de transición entre estados
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fecha_activacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fecha_deprecacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fecha_archivo: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata de la versión
    creado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Cambios respecto a versión anterior (formato libre para humanos)
    changelog: Mapped[Dict[str, Any]] = mapped_column(JSON, default={})
    # Ejemplo:
    # {
    #   "cambios": [
    #     "Se agregó etapa de control de calidad intermedio",
    #     "Se actualizó rendimiento del Dispersor_22 de 0.95 a 0.97",
    #     "Se corrigió handshake entre dispersión y dilución"
    #   ],
    #   "motivo": "Mejora continua - reducción de pérdidas"
    # }
    
    # ═══════════════════════════════════════════════════════════════
    # REFERENCIAS A COMPONENTES (versiones congeladas)
    # ═══════════════════════════════════════════════════════════════
    
    # Componente 1: El producto y su patrón de ruta
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    holon_ruta_id: Mapped[int] = mapped_column(ForeignKey("holon_ruta.id"), nullable=False)
    
    # Componente 2: Las reglas de encadenamiento (handshakes)
    encadenamiento_id: Mapped[int] = mapped_column(ForeignKey("configuracion_encadenamiento.id"), nullable=False)
    
    # Componente 3: Versiones específicas de redes PNML
    # Guardamos el ID de la red y su contenido congelado
    redes_versiones: Mapped[List["VersionRed"]] = relationship(
        back_populates="version_ruta", cascade="all, delete-orphan"
    )
    
    # Alternativa: guardar como JSON simple (más rápido, menos relaciones)
    redes_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    # Ejemplo:
    # {
    #   "integradora": {
    #     "red_petri_id": 5,
    #     "archivo_pnml": "redes/IntegracionV4.pnml",
    #     "checksum": "a1b2c3d4e5f6",
    #     "lugares": {...},
    #     "transiciones": {...}
    #   },
    #   "dispersion": {...},
    #   "dilucion": {...}
    # }
    
    # Componente 4: Asignaciones de recursos (qué recurso hace qué etapa)
    asignaciones_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    # Ejemplo:
    # {
    #   "dispersion": {
    #     "etapa": "Dispersión",
    #     "recurso_asignado": "Dispersor_22",
    #     "duracion_estimada_min": 45,
    #     "costo_por_hora": 45000,
    #     "eficiencia": 0.97
    #   }
    # }
    
    # Componente 5: Conexiones entre etapas (cómo se mueve material)
    conexiones_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Configuración de terminación por red
    terminacion_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    # Ejemplo:
    # {
    #   "integradora": {
    #     "lugares_exito": ["p8", "p24"],
    #     "lugares_fallo": ["p4", "p22"],
    #     "lugares_descarte": ["p17"]
    #   },
    #   "dispersion": {
    #     "lugares_exito": ["p8"],
    #     "lugares_fallo": ["p4", "p11"]
    #   },
    #   "dilucion": {
    #     "lugares_exito": ["p24"],
    #     "lugares_fallo": ["p22"]
    #   }
    # }
    
    # ═══════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════
    
    producto = relationship("Producto", foreign_keys=[producto_id])
    holon_ruta = relationship("HolonRuta", foreign_keys=[holon_ruta_id])
    encadenamiento = relationship("ConfiguracionEncadenamiento", foreign_keys=[encadenamiento_id])
    
    # Órdenes que usaron esta versión
    ordenes: Mapped[List["OrdenProduccion"]] = relationship(
        "OrdenProduccion", back_populates="version_ruta"
    )
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE UTILIDAD
    # ═══════════════════════════════════════════════════════════════
    
    def activar(self, usuario: str):
        """Cambia estado a 'activa'"""
        self.estado = "activa"
        self.fecha_activacion = datetime.now()
        
    def deprecar(self, usuario: str, motivo: str):
        """Cambia estado a 'deprecated'"""
        self.estado = "deprecated"
        self.fecha_deprecacion = datetime.now()
        if not self.changelog:
            self.changelog = {}
        self.changelog['motivo_deprecacion'] = motivo
        self.changelog['deprecado_por'] = usuario
    
    def archivar(self, usuario: str):
        """Archiva la versión (ya no se usa en ningún contexto)"""
        self.estado = "archivada"
        self.fecha_archivo = datetime.now()
    
    def es_usable_para_nueva_orden(self) -> bool:
        """Retorna True si esta versión puede usarse para una orden nueva"""
        return self.estado in ["activa", "validacion"]
    
    def __repr__(self):
        return f"<VersionRuta(id={self.id}, nombre='{self.nombre}', version='{self.version_semver}', estado='{self.estado}')>"


class VersionRed(Base):
    """
    Versión congelada de una Red de Petri.
    
    Permite rastrear qué versión exacta de una red se usó en una ruta.
    Esto es crucial porque las redes pueden evolucionar (corrección de bugs,
    mejora de procesos) sin afectar órdenes antiguas.
    """
    __tablename__ = "version_red"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relación con la versión de ruta
    version_ruta_id: Mapped[int] = mapped_column(ForeignKey("version_ruta.id"), nullable=False)
    
    # Identificación de la red
    nombre_red: Mapped[str] = mapped_column(String(100), nullable=False)  # "integradora", "dispersion", "dilucion"
    red_petri_id: Mapped[int] = mapped_column(ForeignKey("red_petri.id"), nullable=False)
    
    # Snapshot del contenido (congelado)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Contiene:
    # - lugares: definición completa
    # - transiciones: definición completa
    # - arcos: definición completa
    # - archivo_pnml_origen: ruta al PNML original
    # - checksum: para verificar integridad
    
    # Metadata
    version_numero: Mapped[int] = mapped_column(Integer, default=1)
    fecha_snapshot: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relaciones
    version_ruta: Mapped["VersionRuta"] = relationship(back_populates="redes_versiones")
    red_petri = relationship("RedPetri", foreign_keys=[red_petri_id])
    
    def __repr__(self):
        return f"<VersionRed(id={self.id}, red='{self.nombre_red}', version={self.version_numero})>"


class VersionRecurso(Base):
    """
    Historial de cambios en recursos.
    
    Los recursos (equipos y personal) cambian con el tiempo:
    - Mantenimiento modifica disponibilidad
    - Entrenamiento mejora eficiencia
    - Depreciación cambia costos
    - Nueva instrumentación añade capacidades
    
    Este modelo guarda cada cambio significativo para trazabilidad.
    """
    __tablename__ = "version_recurso"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Recurso afectado
    recurso_id: Mapped[int] = mapped_column(ForeignKey("recurso.id"), nullable=False)
    tipo_recurso: Mapped[str] = mapped_column(String(20), nullable=False)  # 'equipo' o 'personal'
    
    # Versión (número secuencial por recurso)
    version_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Fechas de vigencia
    fecha_desde: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fecha_hasta: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # NULL = vigente
    
    # Estado en esta versión
    disponible: Mapped[bool] = mapped_column(default=True)
    
    # Snapshot de parámetros (congelados)
    parametros: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Para equipo:
    # {
    #   "capacidad_maxima": 5000,
    #   "velocidad_procesamiento": 120.5,
    #   "consumo_energia_kw": 45.0,
    #   "costo_depreciacion_hora": 5000
    # }
    # Para personal:
    # {
    #   "costo_por_hora": 15000,
    #   "especialidad": "mezcla",
    #   "roles": ["operador", "supervisor"]
    # }
    
    # Metadata del cambio
    modificado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_cambio: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relaciones
    recurso = relationship("Recurso", foreign_keys=[recurso_id])
    
    def __repr__(self):
        return f"<VersionRecurso(id={self.id}, recurso_id={self.recurso_id}, version={self.version_numero}, desde={self.fecha_desde})>"


class VersionEncadenamiento(Base):
    """
    Versión de las reglas de encadenamiento (handshakes).
    
    Las reglas de coordinación entre redes también pueden evolucionar.
    """
    __tablename__ = "version_encadenamiento"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Referencia a la configuración base
    configuracion_id: Mapped[int] = mapped_column(ForeignKey("configuracion_encadenamiento.id"), nullable=False)
    
    # Versión
    version_numero: Mapped[int] = mapped_column(Integer, default=1)
    
    # Snapshot de reglas (congelado)
    reglas_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Estado
    activo: Mapped[bool] = mapped_column(default=True)
    
    # Metadata
    creado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relaciones
    configuracion = relationship("ConfiguracionEncadenamiento", foreign_keys=[configuracion_id])
    
    def __repr__(self):
        return f"<VersionEncadenamiento(id={self.id}, config_id={self.configuracion_id}, version={self.version_numero})>"


class VersionFormula(Base):
    """
    Versión de la fórmula (BOM - Bill of Materials).
    
    Las fórmulas cambian por:
    - Sustitución de proveedores
    - Optimización de costos
    - Cambios en especificaciones del producto
    """
    __tablename__ = "version_formula"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Referencia a la fórmula base
    formula_id: Mapped[int] = mapped_column(ForeignKey("formula.id"), nullable=False)
    
    # Versión
    version_numero: Mapped[int] = mapped_column(Integer, default=1)
    
    # Fechas de vigencia
    fecha_desde: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fecha_hasta: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Snapshot de la fórmula (congelado)
    formula_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Ejemplo:
    # {
    #   "cantidad_producir_lote": 1000,
    #   "unidad_medida": "L",
    #   "insumos": [
    #     {"nombre": "Agua", "cantidad": 350, "costo_unitario": 50},
    #     {"nombre": "Resina", "cantidad": 400, "costo_unitario": 2500}
    #   ],
    #   "costo_total_materiales": 1125000
    # }
    
    # Metadata
    modificado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_cambio: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relaciones
    formula = relationship("Formula", foreign_keys=[formula_id])
    
    def __repr__(self):
        return f"<VersionFormula(id={self.id}, formula_id={self.formula_id}, version={self.version_numero})>"