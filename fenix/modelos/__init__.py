"""
Modelos del Sistema FÉNIX
=========================

Este paquete contiene todos los modelos SQLAlchemy que representan
la ontología del sistema de seguimiento de producción.

Estructura:
- Continuants (Saber Hacer): Taxonomía, Recursos, Redes de Petri
- Perdurants (Hacer): Órdenes, Instancias, Eventos, Mensajes
- Históricos (Aprender): Versiones, Trazas, Auditoría
"""

# ============================================================
# DECLARATIVE BASE
# ============================================================
from .declarative_base import Base

# ============================================================
# DOCUMENTOS DE NEGOCIO (Perdurants - El Hacer)
# ============================================================
from .DocumentosNegocio import (
    OrdenProduccion,
    Pedido,
    DocumentoEstado,
)

# ============================================================
# PROCESO OCURRENTE (Perdurants - Ejecución)
# ============================================================
from .ProcesoOcurrente import (
    InstanciaRed,
    EventoRed,
)

# ============================================================
# MENSAJES ENTRE REDES (Coordinación)
# ============================================================
from .MensajePendiente import (
    MensajePendiente,
)

# ============================================================
# ENCADENAMIENTO (Handshakes)
# ============================================================
from .Encadenamiento import (
    ConfiguracionEncadenamiento,
)

# ============================================================
# PRODUCTO Y TAXONOMÍA (Continuants - El Saber Hacer)
# ============================================================
from .Producto import (
    Producto,
    HolonRuta,
    AsignacionRecurso,
    ConexionReal,
    Formula,
    InsumoFormula,
    EspecificacionCalidad,
    CriterioAceptacionEtapa,
    InvariantePaso,
)

from .Taxonomia import (
    FamiliaProducto,
    TipoDeOperacion,
    PatronDeRuta,
    EtapaRuta,
    TransicionPatron,
    TParcoEnt,
    TParcoSal,
    TipoRecurso,
    CapacidadTipoOperacion,
)

# ============================================================
# RECURSOS (Continuants - Equipos y Personal)
# ============================================================
from .Recursos import (
    Recurso,
    RecursoEquipo,
    RecursoPersonal,
    UnidadFuncional,
    UnidadNegocio,
    ServicioTecnico,
    ServicioTecnicoOfrecido,
    ServicioNegocio,
    ServicioNegocioOfrecido,
    Rol,
    RolJugado,
)

# ============================================================
# REDES DE PETRI (Continuants - Definición de Procesos)
# ============================================================
from .RedPetri import (
    RedPetri,
    TransicionRed,
    RefinamientoRed,
    SuscripcionEvento,
    DuracionEstimadaLugar,

)

# ============================================================
# RUTA DE PRODUCTO (Continuants - Instanciación de Patrones)
# ============================================================
from .RutaProducto import (
    RutaProducto,
)

# ===========================================================
# MODELO DE PROCESO (Mantiene el conocimiento del 
# funcionamiento de los procesos)
# ===========================================================
from .ProcesoDescripcion import(
    ProcesoModelo,
    ProcesoPaso,
    ProcesoTransicion,
    PMarcoEnt,
    PMarcoSal,
)


# ============================================================
# PROCESO DE NEGOCIO (Modelado de Alto Nivel)
# ============================================================
from .ProcesoNegocio import (
    ProcesoNegocio,
    OperacionNegocio,
    TransicionProcNeg,
    ArcoEntrProcNeg,
    ArcoSalidaProcNeg,
    DocumentoNegocio,
    Renglon,
)

# ============================================================
# VERSIONAMIENTO (Históricos - El Aprender) - NUEVO
# ============================================================
from .Versionamiento import (
    VersionRuta,
    VersionRed,
    VersionRecurso,
    VersionEncadenamiento,
    VersionFormula,
)

# ============================================================
# Cola de eventos
# ============================================================
from .Colaevento import (
    ColaEvento,
)

# ============================================================
# USUARIOS Y SEGURIDAD
# ============================================================
from .Usuario import (
    Usuario,
)




# ============================================================
# EXPORTACIÓN EXPLÍCITA (para IDE y type hints)
# ============================================================

__all__ = [
    # Base
    "Base",
    
    # Documentos de Negocio
    "OrdenProduccion",
    "Pedido",
    "DocumentoEstado",
    
    # Proceso Ocurrente
    "InstanciaRed",
    "EventoRed",
    
    # Mensajes
    "MensajePendiente",
    
    # Encadenamiento
    "ConfiguracionEncadenamiento",
    
    # Producto y Taxonomía
    "Producto",
    "HolonRuta",
    "AsignacionRecurso",
    "ConexionReal",
    "Formula",
    "InsumoFormula",
    "EspecificacionCalidad",
    "CriterioAceptacionEtapa",
    "InvariantePaso",
    "FamiliaProducto",
    "TipoDeOperacion",
    "PatronDeRuta",
    "EtapaRuta",
    "TransicionPatron",
    "TParcoEnt",
    "TParcoSal",
    "TipoRecurso",
    "CapacidadTipoOperacion",
    
    # Recursos
    "Recurso",
    "RecursoEquipo",
    "RecursoPersonal",
    "UnidadFuncional",
    "UnidadNegocio",
    "ServicioTecnico",
    "ServicioTecnicoOfrecido",
    "ServicioNegocio",
    "ServicioNegocioOfrecido",
    "Rol",
    "RolJugado",
    
    #Procesos descripcion
    "ProcesoModelo",
    "ProcesoPaso",
    "ProcesoTransicion",
    "PMarcoEnt",
    "PMarcoSal",
  
  
    # Redes de Petri
    "RedPetri",
    "TransicionRed",
    "RefinamientoRed",
    "SuscripcionEvento",
    "DuracionEstimadaLugar",
    
    # Ruta de Producto
    "RutaProducto",
    
    # Proceso de Negocio
    "ProcesoNegocio",
    "OperacionNegocio",
    "TransicionProcNeg",
    "ArcoEntrProcNeg",
    "ArcoSalidaProcNeg",
    "DocumentoNegocio",
    "Renglon",
    
    # Versionamiento (NUEVO)
    "VersionRuta",
    "VersionRed",
    "VersionRecurso",
    "VersionEncadenamiento",
    "VersionFormula",

    # Cola de eventos
    "ColaEvento",
    
    # Usuarios
    "Usuario",
]

# ============================================================
# METADATA DEL PAQUETE
# ============================================================

__version__ = "2.0.0"
__author__ = "FÉNIX Team"
__description__ = "Modelos ontológicos para sistema de seguimiento de producción"