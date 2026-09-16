# scripts/carga_inicial.py - Versión simplificada (solo YAMLs)

#!/usr/bin/env python3
"""
Carga inicial del sistema FÉNIX - Versión simplificada
Solo carga los archivos YAML de configuración
"""

import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos.declarative_base import Base
from modelos.Taxonomia import (
    FamiliaProducto, TipoDeOperacion, PatronDeRuta, EtapaRuta, 
    TipoRecurso, CapacidadTipoOperacion
)
from modelos.Recursos import (
    Recurso, RecursoEquipo, RecursoPersonal, UnidadFuncional, UnidadNegocio,
    ConexionFisica
)
from modelos.Producto import Producto, HolonRuta, AsignacionRecurso
from modelos.Usuario import Usuario

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CargaInicial:
    """Clase para cargar la configuración inicial del sistema"""
    
    def __init__(self, db_url: str = "sqlite:///fenix.db"):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # Diccionarios para mapear nombres a IDs
        self.familia_map = {}
        self.tipo_operacion_map = {}
        self.tipo_recurso_map = {}
        self.patron_map = {}
        self.etapa_map = {}  # (patron_nombre, op_codigo) -> etapa_id
        self.recurso_map = {}
        self.producto_map = {}
        self.holon_ruta_map = {}
    
    def crear_tablas(self):
        """Crea todas las tablas en la base de datos"""
        logger.info("📋 Creando tablas...")
        Base.metadata.create_all(self.engine)
        logger.info("✅ Tablas creadas")
    
    def limpiar_datos(self):
        """Limpia los datos existentes (para recargar)"""
        logger.info("🧹 Limpiando datos existentes...")
        
        from sqlalchemy import text
        
        # Orden correcto: eliminar hijas primero
        self.session.execute(text("DELETE FROM asignacion_recurso"))
        self.session.execute(text("DELETE FROM holon_ruta"))
        self.session.execute(text("DELETE FROM producto"))
        self.session.execute(text("DELETE FROM capacidad_tipo_operacion"))
        self.session.execute(text("DELETE FROM conexion_fisica"))
        self.session.execute(text("DELETE FROM rol_jugado"))
        self.session.execute(text("DELETE FROM recurso_equipo"))
        self.session.execute(text("DELETE FROM recurso_personal"))
        self.session.execute(text("DELETE FROM recurso"))
        self.session.execute(text("DELETE FROM rol"))
        self.session.execute(text("DELETE FROM tipo_recurso"))
        self.session.execute(text("DELETE FROM patron_de_ruta"))
        self.session.execute(text("DELETE FROM etapa_ruta"))
        self.session.execute(text("DELETE FROM tipo_de_operacion"))
        self.session.execute(text("DELETE FROM familia_producto"))
        self.session.execute(text("DELETE FROM unidad_funcional"))
        self.session.execute(text("DELETE FROM unidad_negocio"))
        self.session.execute(text("DELETE FROM usuario"))
        self.session.execute(text("DELETE FROM servicio_tecnico_ofrecido"))
        self.session.execute(text("DELETE FROM servicio_tecnico"))
        self.session.execute(text("DELETE FROM servicio_negocio_ofrecido"))
        self.session.execute(text("DELETE FROM servicio_negocio"))
        
        self.session.commit()
        logger.info("✅ Datos limpiados")
    
    # ==================== CARGA DE YAMLs ====================
    
    def cargar_familias(self, yaml_path: Path):
        """Carga 01_familias.yaml"""
        logger.info("📦 Cargando familias de producto...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for familia_data in data.get('familias', []):
            familia = FamiliaProducto(
                nombre=familia_data['nombre'],
                descripcion=familia_data.get('descripcion', '')
            )
            self.session.add(familia)
            self.session.flush()
            self.familia_map[familia.nombre] = familia.id
            logger.info(f"   ✅ Familia: {familia.nombre}")
        
        self.session.commit()
        logger.info(f"✅ Cargadas {len(self.familia_map)} familias")
    
    def cargar_tipos_operacion(self, yaml_path: Path):
        """Carga 02_tipos_operacion.yaml"""
        logger.info("⚙️ Cargando tipos de operación...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for tipo_data in data.get('tipos_operacion', []):
            tipo = TipoDeOperacion(
                nombre=tipo_data['codigo'],
                descripcion=tipo_data.get('descripcion', '')
            )
            self.session.add(tipo)
            self.session.flush()
            self.tipo_operacion_map[tipo.nombre] = tipo.id
            logger.info(f"   ✅ Tipo: {tipo.nombre}")
        
        self.session.commit()
        logger.info(f"✅ Cargados {len(self.tipo_operacion_map)} tipos de operación")
    
    def cargar_recursos(self, yaml_path: Path):
        logger.info("🔧 Cargando recursos...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        recursos_list = data.get('recursos', [])
        
        # Crear unidades por defecto
        unidad_default = self.session.query(UnidadFuncional).first()
        if not unidad_default:
            unidad_default = UnidadFuncional(nombre="Planta Principal")
            self.session.add(unidad_default)
            self.session.flush()
        
        unidad_negocio_default = self.session.query(UnidadNegocio).first()
        if not unidad_negocio_default:
            unidad_negocio_default = UnidadNegocio(nombre="Producción")
            self.session.add(unidad_negocio_default)
            self.session.flush()
        
        for recurso_data in recursos_list:
            if not isinstance(recurso_data, dict):
                continue
            
            codigo = recurso_data.get('codigo')
            tipo = recurso_data.get('tipo')
            
            if not codigo or not tipo:
                continue
            
            params = recurso_data.get('parametros', {})
            
            # 1. Crear registro base en Recurso
            recurso_base = Recurso(
                nombre=codigo,
                tipo=tipo,
                descripcion=recurso_data.get('descripcion', '')
            )
            self.session.add(recurso_base)
            self.session.flush()  # Genera ID
            
            # 2. Crear registro especializado según tipo
            if tipo == 'equipo':
                recurso_equipo = RecursoEquipo(
                    id=recurso_base.id,
                    modelo=recurso_data.get('nombre', codigo),
                    unidad_id=unidad_default.id,
                    capacidad_maxima=params.get('capacidad_maxima_litros'),
                    consumo_energia_kw=params.get('consumo_energia_kw', 0),
                    costo_depreciacion_hora=params.get('costo_hora', 0),
                    disponible=True
                )
                self.session.add(recurso_equipo)
            else:  # personal
                recurso_personal = RecursoPersonal(
                    id=recurso_base.id,
                    unidad_id=unidad_negocio_default.id,
                    costo_por_hora=params.get('costo_hora', 0),
                    especialidad=params.get('especialidad', ''),
                    disponible=True
                )
                self.session.add(recurso_personal)
            
            self.recurso_map[codigo] = recurso_base.id
            logger.info(f"   ✅ Recurso: {codigo} ({tipo})")
        
        self.session.commit()
        logger.info(f"✅ Cargados {len(self.recurso_map)} recursos")
    
    def cargar_capacidades(self, yaml_path: Path):
        """Carga 05_capacidades.yaml"""
        logger.info("📊 Cargando capacidades...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for cap_data in data.get('capacidades', []):
            tipo_recurso_nombre = cap_data.get('tipo_recurso')
            tipo_operacion_nombre = cap_data.get('tipo_operacion')
            
            tipo_recurso_id = self.tipo_recurso_map.get(tipo_recurso_nombre)
            tipo_operacion_id = self.tipo_operacion_map.get(tipo_operacion_nombre)
            
            if tipo_recurso_id and tipo_operacion_id:
                capacidad = CapacidadTipoOperacion(
                    tipoRecurso_id=tipo_recurso_id,
                    tipoOperacion_id=tipo_operacion_id,
                    eficiencia_estimada=cap_data.get('eficiencia_estimada', 1.0),
                    costo_por_hora=cap_data.get('costo_por_hora', 0)
                )
                self.session.add(capacidad)
                logger.info(f"   ✅ Capacidad: {tipo_recurso_nombre} → {tipo_operacion_nombre}")
        
        self.session.commit()
        logger.info(f"✅ Capacidades cargadas")
    
    def cargar_patrones(self, yaml_path: Path):
        """Carga 03_patrones.yaml"""
        logger.info("📐 Cargando patrones de ruta...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for patron_data in data.get('patrones', []):
            familia_nombre = patron_data.get('familia')
            familia_id = self.familia_map.get(familia_nombre)
            
            if not familia_id:
                logger.warning(f"   ⚠️ Familia no encontrada: {familia_nombre}")
                continue
            
            patron = PatronDeRuta(
                nombre=patron_data['nombre'],
                descripcion=patron_data.get('descripcion', ''),
                version="1.0",
                familiaProducto_id=familia_id,
                activo=True
            )
            self.session.add(patron)
            self.session.flush()
            self.patron_map[patron.nombre] = patron.id
            
            # Crear etapas
            for idx, op_codigo in enumerate(patron_data.get('operaciones', [])):
                tipo_op_id = self.tipo_operacion_map.get(op_codigo)
                if tipo_op_id:
                    etapa = EtapaRuta(
                        nombre=f"{op_codigo}_{idx+1}",
                        patronRuta_id=patron.id,
                        tipoDeOperacion_id=tipo_op_id
                    )
                    self.session.add(etapa)
                    self.session.flush()
                    self.etapa_map[(patron.nombre, op_codigo)] = etapa.id
                    logger.info(f"   ✅ Etapa: {etapa.nombre}")
            
            logger.info(f"   ✅ Patrón: {patron.nombre}")
        
        self.session.commit()
        logger.info(f"✅ Cargados {len(self.patron_map)} patrones")
    
    def cargar_conectividad_fisica(self, yaml_path: Path):
        """Carga 07_conectividad.yaml"""
        logger.info("🔌 Cargando conexiones físicas...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for conn_data in data.get('conexiones_fisicas', []):
            origen_nombre = conn_data.get('origen')
            destino_nombre = conn_data.get('destino')
            
            origen_id = self.recurso_map.get(origen_nombre)
            destino_id = self.recurso_map.get(destino_nombre)
            
            if not origen_id:
                logger.warning(f"   ⚠️ Recurso origen no encontrado: {origen_nombre}")
                continue
            if not destino_id:
                logger.warning(f"   ⚠️ Recurso destino no encontrado: {destino_nombre}")
                continue
            
            conexion = ConexionFisica(
                recurso_origen_id=origen_id,
                recurso_destino_id=destino_id,
                tipo=conn_data.get('tipo', 'MANUAL'),
                diametro_pulgadas=conn_data.get('diametro_pulgadas'),
                flujo_maximo_lps=conn_data.get('flujo_maximo_lps'),
                perdida_material_pct=conn_data.get('perdida_material_pct', 0),
                requiere_bombeo=conn_data.get('requiere_bombeo', False),
                requiere_operador=conn_data.get('requiere_operador', False),
                activa=True,
                disponible=True
            )
            self.session.add(conexion)
            logger.info(f"   ✅ Conexión: {origen_nombre} → {destino_nombre}")
        
        self.session.commit()
        logger.info(f"✅ Conexiones físicas cargadas")
    
    def cargar_productos(self, yaml_path: Path):
        """Carga 06_productos.yaml"""
        logger.info("📦 Cargando productos...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for prod_data in data.get('productos', []):
            familia_nombre = prod_data.get('familia')
            patron_nombre = prod_data.get('patron')
            
            familia_id = self.familia_map.get(familia_nombre)
            patron_id = self.patron_map.get(patron_nombre)
            
            if not familia_id:
                logger.warning(f"   ⚠️ Familia no encontrada: {familia_nombre}")
                continue
            
            producto = Producto(
                codigo=prod_data['codigo'],
                nombre=prod_data.get('nombre', prod_data['codigo']),
                descripcion=f"Producto {prod_data['codigo']}",
                familia_id=familia_id,
                es_fabricado=True
            )
            self.session.add(producto)
            self.session.flush()
            self.producto_map[producto.codigo] = producto.id
            
            # Crear HolonRuta para cada ruta del producto
            for ruta_data in prod_data.get('rutas', []):
                holon = HolonRuta(
                    nombre=ruta_data['nombre'],
                    descripcion=f"Ruta {ruta_data['nombre']} para {producto.codigo}",
                    producto_id=producto.id,
                    patron_id=patron_id if patron_id else 1,
                    activa=True,
                    condiciones={
                        "lote_minimo_kg": ruta_data.get('lote_minimo_kg', 0),
                        "lote_maximo_kg": ruta_data.get('lote_maximo_kg', float('inf')),
                        "prioridad_minima": ruta_data.get('prioridad_minima', 1),
                        "tipo_ruta": ruta_data.get('tipo', 'normal'),
                        "orden_preferencia": ruta_data.get('orden_preferencia', 0),
                        "requiere_inventario": ruta_data.get('requiere_inventario')
                    }
                )
                self.session.add(holon)
                self.session.flush()
                
                # Asignaciones de recursos
                asignaciones = ruta_data.get('asignaciones', {})
                for op_codigo, asig_data in asignaciones.items():
                    recurso_nombre = asig_data.get('recurso')
                    recurso_id = self.recurso_map.get(recurso_nombre)
                    
                    if not recurso_id:
                        logger.warning(f"   ⚠️ Recurso no encontrado: {recurso_nombre}")
                        continue
                    
                    # Obtener etapa
                    etapa_id = self.etapa_map.get((patron_nombre, op_codigo))
                    
                    if etapa_id:
                        asignacion = AsignacionRecurso(
                            holon_ruta_id=holon.id,
                            etapa_ruta_id=etapa_id,
                            recurso_id=recurso_id,
                            duracion_estimada_min=asig_data.get('duracion_estimada_min', 60),
                            costo_por_hora_real=asig_data.get('costo_por_hora_real', 0),
                            eficiencia_real=1.0
                        )
                        self.session.add(asignacion)
                        logger.info(f"      ✅ Asignación: {op_codigo} → {recurso_nombre}")
                
                logger.info(f"   ✅ HolonRuta: {ruta_data['nombre']} para {producto.codigo}")
            
            logger.info(f"   ✅ Producto: {prod_data['codigo']}")
        
        self.session.commit()
        logger.info(f"✅ Cargados {len(self.producto_map)} productos")
    
    def crear_usuario_admin(self):
        """Crea un usuario administrador por defecto"""
        logger.info("👤 Creando usuario administrador...")
        
        admin = self.session.query(Usuario).filter_by(email="admin@fenix.com").first()
        if not admin:
            admin = Usuario(
                nombre="Administrador",
                email="admin@fenix.com",
                rol="admin",
                activo=True
            )
            admin.set_password("admin123")
            self.session.add(admin)
            self.session.commit()
            logger.info("   ✅ Usuario admin creado (email: admin@fenix.com, password: admin123)")
        else:
            logger.info("   ✅ Usuario admin ya existe")
    
    # ==================== EJECUCIÓN PRINCIPAL ====================
    
    def ejecutar(self, base_path: Path):
        """Ejecuta toda la carga inicial"""
        logger.info("🚀 INICIANDO CARGA INICIAL DEL SISTEMA FÉNIX")
        logger.info("=" * 60)
        
        # 1. Crear tablas
        self.crear_tablas()
        
        # 2. Limpiar datos existentes
        respuesta = input("¿Limpiar datos existentes? (s/N): ")
        if respuesta.lower() == 's':
            self.limpiar_datos()
        
        # 3. Cargar YAMLs
        config_dir = base_path / "config"
        
        # Verificar que existan los archivos
        required_files = [
            "01_familias.yaml", "02_tipos_operacion.yaml", "03_patrones.yaml",
            "04_recursos.yaml", "05_capacidades.yaml", "06_productos.yaml", "07_conectividad.yaml"
        ]
        
        for f in required_files:
            file_path = config_dir / f
            if not file_path.exists():
                logger.error(f"❌ Archivo no encontrado: {file_path}")
                logger.error(f"   Directorio actual: {Path.cwd()}")
                logger.error(f"   Buscando en: {config_dir.absolute()}")
                return
        
        self.cargar_familias(config_dir / "01_familias.yaml")
        self.cargar_tipos_operacion(config_dir / "02_tipos_operacion.yaml")
        self.cargar_recursos(config_dir / "04_recursos.yaml")
        self.cargar_capacidades(config_dir / "05_capacidades.yaml")
        self.cargar_patrones(config_dir / "03_patrones.yaml")
        self.cargar_conectividad_fisica(config_dir / "07_conectividad.yaml")
        self.cargar_productos(config_dir / "06_productos.yaml")
        
        # 4. Crear usuario admin
        self.crear_usuario_admin()
        
        logger.info("=" * 60)
        logger.info("🎉 CARGA INICIAL COMPLETADA")
        logger.info(f"📊 Resumen:")
        logger.info(f"   - Familias: {len(self.familia_map)}")
        logger.info(f"   - Tipos operación: {len(self.tipo_operacion_map)}")
        logger.info(f"   - Recursos: {len(self.recurso_map)}")
        logger.info(f"   - Patrones: {len(self.patron_map)}")
        logger.info(f"   - Productos: {len(self.producto_map)}")


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Carga inicial del sistema FÉNIX")
    parser.add_argument("--db", type=str, default="sqlite:///fenix.db",
                        help="URL de la base de datos")
    parser.add_argument("--path", type=str, default=".",
                        help="Ruta base donde está la carpeta config/")
    
    args = parser.parse_args()
    
    base_path = Path(args.path)
    if not base_path.exists():
        logger.error(f"❌ Ruta no encontrada: {base_path}")
        sys.exit(1)
    
    cargador = CargaInicial(db_url=args.db)
    cargador.ejecutar(base_path)


if __name__ == "__main__":
    main()