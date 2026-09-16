# scripts/inicializar_entorno_prueba.py
"""
Script completo para inicializar el entorno de prueba:
- Crea familias, patrones, productos
- Registra las 3 redes Petri desde PNML
- Configura refinamientos y encadenamiento
"""

import sys
import io
import os
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

# Importar modelos
from modelos.declarative_base import Base
from modelos.Producto import Producto, FamiliaProducto
from modelos.Taxonomia import PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.RedPetri import RedPetri, TransicionRed, RefinamientoRed
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.ProcesoOcurrente import OrdenProduccion, InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente
from utils.parser_pnml import cargar_red_desde_pnml


def limpiar_base_datos(session):
    """Limpia todas las tablas relevantes para empezar de cero"""
    print("\n🧹 Limpiando base de datos...")
    
    # Orden de eliminación respetando FK
    session.query(MensajePendiente).delete()
    session.query(EventoRed).delete()
    session.query(InstanciaRed).delete()
    session.query(OrdenProduccion).delete()
    session.query(ConfiguracionEncadenamiento).delete()
    session.query(RefinamientoRed).delete()
    session.query(TransicionRed).delete()
    session.query(RedPetri).delete()
    session.query(EtapaRuta).delete()
    session.query(PatronDeRuta).delete()
    session.query(Producto).delete()
    session.query(FamiliaProducto).delete()
    session.query(TipoDeOperacion).delete()
    
    session.commit()
    print("✅ Base de datos limpiada")


def crear_familia_y_patron(session):
    """Crea la familia de productos y el patrón de ruta"""
    print("\n📁 Creando familia y patrón...")
    
    # Crear familia
    familia = FamiliaProducto(
        nombre="Pinturas Base Agua",
        descripcion="Familia de pinturas base agua para dispersión y dilución"
    )
    session.add(familia)
    session.flush()
    print(f"   ✅ Familia creada: ID {familia.id} - {familia.nombre}")
    
    # Crear patrón de ruta
    patron = PatronDeRuta(
        nombre="Patron Integracion Dis Dil V1",
        descripcion="Patrón para producción de pintura base agua con dispersión y dilución",
        familiaProducto_id=familia.id
    )
    session.add(patron)
    session.flush()
    print(f"   ✅ Patrón creado: ID {patron.id} - {patron.nombre}")
    
    return familia, patron


def crear_producto(session, familia_id):
    """Crea el producto Pintura Blanca"""
    print("\n🎨 Creando producto...")
    
    producto = Producto(
        codigo="PINT-BLANCA-001",
        nombre="Pintura Blanca Base Agua",
        descripcion="Pintura blanca base agua para interiores",
        familia_id=familia_id,
        unidad_medida="L",
        precio_unitario=15.50,
        activo=True
    )
    session.add(producto)
    session.flush()
    print(f"   ✅ Producto creado: ID {producto.id} - {producto.nombre}")
    
    return producto


def registrar_red_desde_pnml(session, patron_id, nombre_archivo):
    """Registra una red Petri desde archivo PNML"""
    print(f"\n📄 Registrando red: {nombre_archivo}")
    
    # Ruta del archivo PNML
    pnml_path = Path(__file__).parent.parent / 'static' / 'archivospnml' / f"{nombre_archivo}.pnml"
    
    if not pnml_path.exists():
        print(f"   ❌ Archivo no encontrado: {pnml_path}")
        return None
    
    # Cargar red desde PNML
    red_pnml = cargar_red_desde_pnml(str(pnml_path))
    if not red_pnml:
        print(f"   ❌ Error cargando PNML")
        return None
    
    # Convertir a JSON para almacenar
    lugares_json = {}
    for pid, place in red_pnml.places.items():
        lugares_json[pid] = {
            'nombre': place.nombre,
            'marcado_inicial': place.marking_inicial
        }
    
    transiciones_json = {}
    for tid, trans in red_pnml.transitions.items():
        transiciones_json[tid] = {
            'nombre': trans.nombre,
            'trigger_type': trans.trigger_type or "manual"
        }
    
    arcos_json = []
    for tid, arcos in red_pnml.arcos_entrada.items():
        for arc in arcos:
            arcos_json.append({
                'tipo': 'entrada',
                'transicion': tid,
                'lugar': arc.source,
                'peso': arc.peso
            })
    
    for tid, arcos in red_pnml.arcos_salida.items():
        for arc in arcos:
            arcos_json.append({
                'tipo': 'salida',
                'transicion': tid,
                'lugar': arc.target,
                'peso': arc.peso
            })
    
    # Crear red en BD
    red = RedPetri(
        nombre=red_pnml.nombre,
        descripcion=f"Red de Petri para {red_pnml.nombre}",
        version=1,
        lugares=lugares_json,
        transiciones=transiciones_json,
        arcos=arcos_json,
        patron_ruta_id=patron_id,
        archivo_pnml_origen=f"{nombre_archivo}.pnml",
        activo=True
    )
    session.add(red)
    session.flush()
    
    # Registrar transiciones
    for tid, trans in red_pnml.transitions.items():
        trans_bd = TransicionRed(
            red_petri_id=red.id,
            id_pnml=tid,
            nombre=trans.nombre,
            trigger_type=trans.trigger_type or "manual"
        )
        session.add(trans_bd)
    
    print(f"   ✅ Red registrada: ID {red.id} - {red.nombre}")
    return red


def crear_refinamientos(session):
    """Crea los refinamientos entre redes padre e hijas"""
    print("\n🔗 Creando refinamientos...")
    
    # Obtener redes
    red_padre = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4"
    ).first()
    
    red_dispersion = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1"
    ).first()
    
    red_dilucion = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2"
    ).first()
    
    if not all([red_padre, red_dispersion, red_dilucion]):
        print("   ❌ No se encontraron todas las redes")
        return
    
    # Refinamiento: t2 (Iniciar disp) -> red de dispersión
    ref1 = RefinamientoRed(
        red_padre_id=red_padre.id,
        transicion_padre="t2",  # Iniciar disp
        red_hija_id=red_dispersion.id,
        eventos={"evento_inicio": "Iniciar disp", "evento_fin": "Fin dispersion"},
        activo=True
    )
    session.add(ref1)
    
    # Refinamiento: t6 (Iniciar diluidor) -> red de dilución
    ref2 = RefinamientoRed(
        red_padre_id=red_padre.id,
        transicion_padre="t6",  # Iniciar diluidor
        red_hija_id=red_dilucion.id,
        eventos={"evento_inicio": "Iniciar diluidor", "evento_fin": "Diluidor ok"},
        activo=True
    )
    session.add(ref2)
    
    session.commit()
    print(f"   ✅ Refinamientos creados:")
    print(f"      - {red_padre.nombre}.t2 → {red_dispersion.nombre}")
    print(f"      - {red_padre.nombre}.t6 → {red_dilucion.nombre}")


def crear_encadenamiento(session):
    """Crea la configuración de encadenamiento entre redes"""
    print("\n📨 Creando encadenamiento...")
    
    # Obtener redes
    red_padre = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4"
    ).first()
    
    red_dispersion = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1"
    ).first()
    
    red_dilucion = session.query(RedPetri).filter_by(
        nombre="Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2"
    ).first()
    
    # Configuración de encadenamiento
    # Diccionario: red_origen -> {transicion_id: {red_destino, evento}}
    reglas = {
        red_dispersion.nombre: {
            "t41": {"red_destino": red_padre.nombre, "evento": "Fin dispersion"}
        },
        red_dilucion.nombre: {
            "t14": {"red_destino": red_padre.nombre, "evento": "Diluidor ok"},
            "t20": {"red_destino": red_padre.nombre, "evento": "Fin carga"},
            "t31": {"red_destino": red_padre.nombre, "evento": "Liberar diluidor"}
        }
    }
    
    config = ConfiguracionEncadenamiento(
        nombre="Encadenamiento_Complejo_V1",
        descripcion="Encadenamiento entre redes de dispersión y dilución",
        reglas=reglas,
        activo=True,
        fecha_creacion=datetime.now()
    )
    session.add(config)
    session.commit()
    
    print(f"   ✅ Encadenamiento creado: {config.nombre}")
    print(f"      Reglas: {len(reglas)} redes origen")


def verificar_entorno(session):
    """Verifica que todo se haya creado correctamente"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DEL ENTORNO")
    print("=" * 60)
    
    # Contar registros
    familias = session.query(FamiliaProducto).count()
    patrones = session.query(PatronDeRuta).count()
    productos = session.query(Producto).count()
    redes = session.query(RedPetri).count()
    transiciones = session.query(TransicionRed).count()
    refinamientos = session.query(RefinamientoRed).count()
    encadenamientos = session.query(ConfiguracionEncadenamiento).count()
    
    print(f"\n📊 Resumen:")
    print(f"   Familias: {familias}")
    print(f"   Patrones: {patrones}")
    print(f"   Productos: {productos}")
    print(f"   Redes Petri: {redes}")
    print(f"   Transiciones: {transiciones}")
    print(f"   Refinamientos: {refinamientos}")
    print(f"   Encadenamientos: {encadenamientos}")
    
    # Mostrar redes
    print(f"\n📄 Redes registradas:")
    for red in session.query(RedPetri).all():
        trans_count = session.query(TransicionRed).filter_by(red_petri_id=red.id).count()
        print(f"   - {red.nombre} (ID:{red.id}, transiciones:{trans_count}, patron_id:{red.patron_ruta_id})")
    
    # Mostrar producto
    producto = session.query(Producto).first()
    if producto:
        print(f"\n🎨 Producto de prueba:")
        print(f"   ID: {producto.id}")
        print(f"   Nombre: {producto.nombre}")
        print(f"   Familia ID: {producto.familia_id}")
    
    print("\n✅ Entorno listo para pruebas!")


def main():
    print("=" * 60)
    print("INICIALIZACIÓN DE ENTORNO DE PRUEBA")
    print("=" * 60)
    
    # Conectar a la base de datos
    engine = create_engine('sqlite:///fenix.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Limpiar base de datos
        limpiar_base_datos(session)
        
        # 2. Crear familia y patrón
        familia, patron = crear_familia_y_patron(session)
        
        # 3. Crear producto
        producto = crear_producto(session, familia.id)
        
        # 4. Registrar redes PNML
        redes_nombres = [
            "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4",
            "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1",
            "Pintuco_BaseAgua_dilucion_RedHija_Dis_Dil_V2"
        ]
        
        redes_registradas = []
        for nombre in redes_nombres:
            red = registrar_red_desde_pnml(session, patron.id, nombre)
            if red:
                redes_registradas.append(red)
        
        # 5. Crear refinamientos
        crear_refinamientos(session)
        
        # 6. Crear encadenamiento
        crear_encadenamiento(session)
        
        # 7. Commit final
        session.commit()
        
        # 8. Verificar
        verificar_entorno(session)
        
        print("\n" + "=" * 60)
        print("✅ INICIALIZACIÓN COMPLETADA")
        print("=" * 60)
        print("\nAhora puedes ejecutar:")
        print("   python test_orquestador_persistente.py")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()