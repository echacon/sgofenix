#!/usr/bin/env python3
# init_prueba.py - Inicialización completa del entorno de pruebas
# Usa:
#   - Importador de patrones para redes Petri y encadenamiento
#   - Config YAMLs para familias, tipos de operación, recursos, productos

import sys
import io
import yaml
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


from modelos.declarative_base import Base
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.Producto import Producto, FamiliaProducto, HolonRuta, AsignacionRecurso
from modelos.Taxonomia import PatronDeRuta, EtapaRuta, TipoDeOperacion
from modelos.Recursos import Recurso, RecursoEquipo, RecursoPersonal, UnidadFuncional, UnidadNegocio, Rol, RolJugado
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.MensajePendiente import MensajePendiente
from modelos.RedPetri import RedPetri
from importadores.importador_patrones import ImportadorPatrones

from importadores.cargador_yaml import CargadorYAML 


def crear_tablas(engine):
    print("\n[1/7] Creando tablas...")
    Base.metadata.create_all(engine)
    print("      ✅ Tablas listas")


def limpiar_todo(session):
    """Elimina todas las tablas de datos (para reinicio completo)"""
    print("\n[2/7] Limpiando base de datos (todo)...")
    session.query(MensajePendiente).delete()
    session.query(EventoRed).delete()
    session.query(InstanciaRed).delete()
    session.query(OrdenProduccion).delete()
    session.query(AsignacionRecurso).delete()
    session.query(HolonRuta).delete()
    session.query(Producto).delete()
    session.query(EtapaRuta).delete()
    session.query(PatronDeRuta).delete()
    session.query(TipoDeOperacion).delete()
    session.query(RecursoEquipo).delete()
    session.query(RecursoPersonal).delete()
    session.query(Recurso).delete()
    session.query(UnidadFuncional).delete()
    session.query(UnidadNegocio).delete()
    session.query(RolJugado).delete()
    session.query(Rol).delete()
    session.query(FamiliaProducto).delete()
    session.commit()
    print("      ✅ Datos eliminados")


def importar_patrones_desde_pendientes(session, base_path):
    """Ejecuta el importador de patrones para cargar redes, encadenamiento y metadatos"""
    print("\n[3/7] Importando patrones desde importacion/pendientes/...")
    importador = ImportadorPatrones(session, base_path)
    importador.procesar_pendientes()
    print("      ✅ Patrones importados")


def crear_familias(session, config):
    """Crea familias desde YAML (complementa las que ya vinieron de los metadatos de patrones)"""
    print("\n[4/7] Creando familias (desde config)...")
    familias = config.get('familias', [])
    for f in familias:
        familia = session.query(FamiliaProducto).filter_by(nombre=f['nombre']).first()
        if not familia:
            familia = FamiliaProducto(
                nombre=f['nombre'],
                descripcion=f.get('descripcion', '')
            )
            session.add(familia)
    session.flush()
    print(f"      ✅ {len(familias)} familias procesadas")

def obtener_o_crear_unidad_funcional(session, nombre_unidad="Planta Producción"):
    # Generar un código a partir del nombre (puedes personalizar)
    codigo_unidad = nombre_unidad.replace(" ", "_").upper()
    uf = session.query(UnidadFuncional).filter_by(codigo=codigo_unidad).first()
    if not uf:
        uf = UnidadFuncional(
            codigo=codigo_unidad,
            nombre=nombre_unidad,
            descripcion="Unidad funcional por defecto"
        )
        session.add(uf)
        session.flush()
    return uf


def crear_etapas_de_patrones(session, config):
    print("\n[Extra] Creando etapas de patrones...")
    patrones_data = config.get('patrones', [])
    if not patrones_data:
        print("      ℹ️ No hay patrones definidos en 03_patrones.yaml, saltando creación de etapas")
        return
    
    for p in patrones_data:
        nombre_patron = p.get('nombre')
        if not nombre_patron:
            continue
        patron = session.query(PatronDeRuta).filter_by(nombre=nombre_patron).first()
        if not patron:
            print(f"      ⚠️ Patrón '{nombre_patron}' no encontrado en BD, no se pueden crear etapas")
            continue
        # Crear etapas para cada operación en la lista 'operaciones'
        for op_codigo in p.get('operaciones', []):
            tipo_op = session.query(TipoDeOperacion).filter_by(codigo=op_codigo).first()
            if not tipo_op:
                print(f"      ⚠️ Tipo de operación '{op_codigo}' no encontrado, no se crea etapa")
                continue
            # Usar los nombres correctos de las columnas
            etapa = session.query(EtapaRuta).filter_by(
                nombre=op_codigo,
                patronRuta_id=patron.id
            ).first()
            if not etapa:
                etapa = EtapaRuta(
                    nombre=op_codigo,
                    tipoDeOperacion_id=tipo_op.id,   # ← nombre correcto
                    patronRuta_id=patron.id
                    # orden no existe en tu modelo, lo omitimos
                )
                session.add(etapa)
        session.flush()
        print(f"      ✅ Etapas creadas para patrón: {nombre_patron}")
    print("      ✅ Etapas de patrones listas")


def crear_tipos_operacion(session, config):
    print("\n[5/7] Creando tipos de operación...")
    tipos = config.get('tipos_operacion', [])
    if not isinstance(tipos, list):
        print("      ⚠️ tipos_operacion no es una lista, se omite")
        return
    for t in tipos:
        codigo = t.get('codigo')
        if not codigo:
            print(f"      ⚠️ Elemento sin 'codigo' omitido: {t}")
            continue
        descripcion = t.get('descripcion', '')
        tipo = session.query(TipoDeOperacion).filter_by(nombre=codigo).first()
        if not tipo:
            tipo = TipoDeOperacion(
                nombre=codigo,          # usamos el código como nombre
                codigo=codigo,
                descripcion=descripcion
            )
            session.add(tipo)
    session.flush()
    print(f"      ✅ Tipos procesados: {len(tipos)}")



def crear_unidades_funcionales_y_recursos(session, config):
    print("\n[6/7] Creando unidades funcionales y recursos...")
    recursos_data = config.get('recursos', [])
    if not isinstance(recursos_data, list):
        print("      ⚠️ 'recursos' no es una lista, se omite")
        return

    unidad_por_defecto = obtener_o_crear_unidad_funcional(session,"Planta Produccion")

    for r in recursos_data:
        nombre = r.get('nombre')
        codigo = r.get('codigo')
        if not nombre:
            nombre = codigo
        if not nombre:
            print(f"      ⚠️ Recurso sin nombre ni código omitido: {r}")
            continue

        tipo_recurso = r.get('tipo', 'equipo')
        recurso = session.query(Recurso).filter_by(nombre=nombre).first()
        if not recurso:
            recurso = Recurso(
                codigo=codigo,
                nombre=nombre,
                tipo=tipo_recurso,
                descripcion=r.get('descripcion', '')
            )
            session.add(recurso)
            session.flush()

        params = r.get('parametros', {})
        categoria = r.get('categoria', '')

        if tipo_recurso == 'equipo':
            equipo = session.query(RecursoEquipo).filter_by(id=recurso.id).first()
            if not equipo:
                # Asignar unidad funcional (podría venir en el recurso, si no, usar por defecto)
                uf_nombre = r.get('unidad_funcional', 'Planta Producción')
                uf = session.query(UnidadFuncional).filter_by(nombre=uf_nombre).first()
                if not uf:
                    uf = obtener_o_crear_unidad_funcional(session, uf_nombre)
                equipo = RecursoEquipo(
                    id=recurso.id,
                    modelo=categoria,
                    unidad_id=uf.id,
                    capacidad_maxima=params.get('capacidad_maxima_litros'),
                    velocidad_procesamiento=params.get('rendimiento'),
                    consumo_energia_kw=params.get('consumo_energia_kw', 0),
                    costo_depreciacion_hora=params.get('costo_hora', 0),
                    disponible=True
                )
                session.add(equipo)
                print(f"      ✅ Equipo creado: {nombre}")
        elif tipo_recurso == 'personal':
            personal = session.query(RecursoPersonal).filter_by(id=recurso.id).first()
            if not personal:
                personal = RecursoPersonal(
                    id=recurso.id,
                    costo_por_hora=params.get('costo_hora', 0),
                    especialidad=params.get('especialidad', ''),
                    disponible=True
                )
                session.add(personal)
                print(f"      ✅ Personal creado: {nombre}")

    session.commit()
    print(f"      ✅ Recursos procesados: {len(recursos_data)}")




def crear_productos_y_holones(session, config):
    print("\n[7/7] Creando productos y holones de ruta...")
    productos_data = config.get('productos', [])
    if not isinstance(productos_data, list):
        print("      ⚠️ 'productos' no es una lista, se omite")
        return

    for prod in productos_data:
        codigo = prod.get('codigo')
        nombre = prod.get('nombre')
        if not codigo or not nombre:
            print(f"      ⚠️ Producto sin código o nombre omitido: {prod}")
            continue

        familia_nombre = prod.get('familia')
        familia = session.query(FamiliaProducto).filter_by(nombre=familia_nombre).first()
        if not familia:
            print(f"      ⚠️ Familia '{familia_nombre}' no encontrada, producto omitido")
            continue

        producto = session.query(Producto).filter_by(codigo=codigo).first()
        if not producto:
            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                familia_id=familia.id,
                descripcion=prod.get('descripcion', ''),
                es_fabricado=True,
                es_final=True
            )
            session.add(producto)
            session.flush()
            print(f"      📦 Producto creado: {codigo} - {nombre}")
        else:
            print(f"      📦 Producto existente: {codigo}")

        patron_nombre = prod.get('patron')
        if not patron_nombre:
            print(f"      ⚠️ Producto {codigo} sin patrón, no se pueden crear rutas")
            continue
        patron = session.query(PatronDeRuta).filter_by(nombre=patron_nombre).first()
        if not patron:
            print(f"      ⚠️ Patrón '{patron_nombre}' no encontrado, no se crean rutas para {codigo}")
            continue

        for ruta_info in prod.get('rutas', []):
            condiciones = ruta_info.get('condiciones', {})
            for campo in ['lote_minimo_kg', 'lote_maximo_kg', 'prioridad_minima', 'tipo_ruta', 'orden_preferencia']:
                if campo in ruta_info and campo not in condiciones:
                    condiciones[campo] = ruta_info[campo]

            holon = session.query(HolonRuta).filter_by(
                producto_id=producto.id,
                patron_id=patron.id,
                activa=True
            ).first()
            if not holon:
                holon = HolonRuta(
                    nombre=ruta_info.get('nombre', f"Ruta {codigo}"),
                    descripcion=ruta_info.get('descripcion', ''),
                    producto_id=producto.id,
                    patron_id=patron.id,
                    activa=True,
                    condiciones=condiciones
                )
                session.add(holon)
                session.flush()
                print(f"         🔗 HolonRuta creado: {holon.nombre}")

            # Asignaciones: formato { "DIS": { "recurso": "...", "duracion_estimada_min": ... } }
            asignaciones_dict = ruta_info.get('asignaciones', {})
            for op_codigo, asig_data in asignaciones_dict.items():
                # Buscar la etapa del patrón cuyo nombre coincide con el código de operación
                etapa = session.query(EtapaRuta).filter_by(
                    nombre=op_codigo,
                    patronRuta_id=patron.id   # ← nombre correcto
                ).first()
                if not etapa:
                    print(f"            ⚠️ Etapa '{op_codigo}' no encontrada para patrón {patron.nombre}")
                    continue
                recurso_codigo = asig_data.get('recurso')
                if not recurso_codigo:
                    print(f"            ⚠️ Asignación para {op_codigo} sin recurso")
                    continue
                recurso = session.query(Recurso).filter_by(codigo=recurso_codigo).first()
                if not recurso:
                    print(f"            ⚠️ Recurso '{recurso_codigo}' no encontrado")
                    continue

                asignacion = session.query(AsignacionRecurso).filter_by(
                    holon_ruta_id=holon.id,
                    etapa_ruta_id=etapa.id
                ).first()
                if not asignacion:
                    asignacion = AsignacionRecurso(
                        holon_ruta_id=holon.id,
                        etapa_ruta_id=etapa.id,
                        recurso_id=recurso.id,
                        duracion_estimada_min=asig_data.get('duracion_estimada_min', 60),
                        costo_por_hora_real=asig_data.get('costo_por_hora', 0),
                        eficiencia_real=asig_data.get('eficiencia', 1.0)
                    )
                    session.add(asignacion)
                    print(f"            ✅ {recurso.nombre} → {etapa.nombre} (operación {op_codigo})")

    session.commit()
    print(f"      ✅ Productos y holones listos")

    


def crear_orden_prueba(session):
    print("\n[Extra] Creando orden de prueba...")
    producto = session.query(Producto).filter_by(codigo="LAT-1000").first()
    if not producto:
        print("      ⚠️ Producto LAT-1000 no encontrado, no se crea orden")
        return

    holon = session.query(HolonRuta).filter_by(producto_id=producto.id, activa=True).first()
    if not holon:
        print("      ⚠️ No hay HolonRuta activo para LAT-1000")
        return

    from datetime import date
    orden = session.query(OrdenProduccion).filter_by(numero_orden="ORD-20260515-0001").first()
    if not orden:
        orden = OrdenProduccion(
            numero_orden="ORD-20260515-0001",
            producto_id=producto.id,
            holon_ruta_id=holon.id,
            cantidad=500.0,
            estado="pendiente",
            prioridad=1,
            fecha_requerida=date(2025, 5, 20)   # ← objeto date, no cadena
        )
        session.add(orden)
        session.commit()
        print(f"      🆕 Orden creada: {orden.numero_orden} (ID {orden.id})")
    else:
        print(f"      ℹ️ Orden ya existe: {orden.numero_orden}")


def crear_conectividad(session, config):
    print("\n[Extra] Creando conexiones físicas...")
    conexiones = config.get('conexiones_fisicas', [])
    if not conexiones:
        print("      ℹ️ No hay conexiones definidas en 07_conectividad.yaml")
        return

    from modelos.Recursos import ConexionFisica
    for conn in conexiones:
        origen_nombre = conn.get('origen')
        destino_nombre = conn.get('destino')
        if not origen_nombre or not destino_nombre:
            print(f"      ⚠️ Conexión sin origen o destino: {conn}")
            continue
        origen = session.query(Recurso).filter_by(nombre=origen_nombre).first()
        destino = session.query(Recurso).filter_by(nombre=destino_nombre).first()
        if not origen or not destino:
            print(f"      ⚠️ Recursos no encontrados para conexión {origen_nombre} → {destino_nombre}")
            continue
        tipo = conn.get('tipo', 'TUBERIA')
        conexion = session.query(ConexionFisica).filter_by(
            recurso_origen_id=origen.id,
            recurso_destino_id=destino.id
        ).first()
        if not conexion:
            conexion = ConexionFisica(
                recurso_origen_id=origen.id,
                recurso_destino_id=destino.id,
                tipo=tipo,
                diametro_pulgadas=conn.get('diametro_pulgadas'),
                longitud_metros=conn.get('longitud_metros'),
                flujo_maximo_lps=conn.get('flujo_maximo_lps'),
                perdida_material_pct=conn.get('perdida_material_pct', 0),
                requiere_bombeo=conn.get('requiere_bombeo', False),
                requiere_operador=conn.get('requiere_operador', False),
                activa=True
            )
            session.add(conexion)
            print(f"      🔌 Conexión creada: {origen.nombre} → {destino.nombre}")
    session.commit()
    print(f"      ✅ Conectividad procesada: {len(conexiones)} conexiones")

def asignar_estados_finales_todos_patrones(session_factory, procesados_dir: Path):
    """
    Recorre todos los subdirectorios en 'procesados_dir', lee metadatos.yaml
    y actualiza directamente la columna 'metadatos' de la tabla red_petri
    con los estados finales definidos para cada red.
    """
    session = session_factory()
    try:
        for patron_dir in procesados_dir.glob("*"):
            if not patron_dir.is_dir():
                continue
            yaml_file = patron_dir / "metadatos.yaml"
            if not yaml_file.exists():
                continue
            with open(yaml_file, 'r', encoding='utf-8') as f:
                metadatos = yaml.safe_load(f)
            estados_config = metadatos.get('estados_finales', {})
            if not estados_config:
                continue

            for red_nombre, config in estados_config.items():
                # Construir el diccionario 'finales' en el formato esperado
                finales = {}
                for categoria in ['exito', 'falla', 'descarte']:
                    if categoria in config:
                        raw = config[categoria]
                        if isinstance(raw, list):
                            if all(isinstance(x, str) for x in raw):
                                lugares = raw
                            elif all(isinstance(x, dict) for x in raw):
                                lugares = [item['lugar'] for item in raw if 'lugar' in item]
                            else:
                                continue
                            # Normalizar 'falla' a 'fallo' para consistencia
                            cat = 'fallo' if categoria == 'falla' else categoria
                            finales[cat] = lugares
                if finales:
                    # Crear el objeto JSON que irá dentro de metadatos
                    # (respetando cualquier otro contenido existente)
                    # Para simplificar, sobrescribimos solo la clave 'estados_finales'
                    # y mantenemos el resto de metadatos (si los hubiera)
                    # Primero recuperamos los metadatos actuales (si existen)
                    result = session.execute(
                        text("SELECT metadatos FROM red_petri WHERE nombre = :nombre"),
                        {"nombre": red_nombre}
                    ).first()
                    current_metadatos = result[0] if result else {}
                    if current_metadatos is None:
                        current_metadatos = {}
                    elif isinstance(current_metadatos, str):
                        # Si por alguna razón viene como string, lo parseamos
                        current_metadatos = json.loads(current_metadatos)
                    # Actualizar la clave 'estados_finales'
                    current_metadatos['estados_finales'] = finales
                    # Convertir a JSON string
                    json_str = json.dumps(current_metadatos)
                    # Ejecutar UPDATE directo
                    session.execute(
                        text("UPDATE red_petri SET metadatos = :metadatos WHERE nombre = :nombre"),
                        {"metadatos": json_str, "nombre": red_nombre}
                    )
                    print(f"   → Actualizado {red_nombre} con {finales}")
            # Commit por cada patrón
            session.commit()
            print(f"   ✅ Commit realizado para {patron_dir.name}")
        session.commit()
        print("   ✅ Todos los estados finales asignados correctamente")
    except Exception as e:
        session.rollback()
        print(f"   ❌ Error durante la asignación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    

def main():
    print("=" * 60)
    print("INICIALIZACIÓN COMPLETA DE FÉNIX")
    print("=" * 60)

    base_path = Path(__file__).parent
    engine = create_engine('sqlite:///fenix.db')
    crear_tablas(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Cargar configuraciones YAML
    config = CargadorYAML.cargar_todo()
    
    # 2. Importar patrones (sin asignar estados finales)
    importar_patrones_desde_pendientes(session, base_path)
    
    # 3. Crear entidades (familias, tipos, etapas, recursos, productos, conectividad, orden)
    crear_familias(session, config)
    crear_tipos_operacion(session, config)
    crear_etapas_de_patrones(session, config)
    crear_unidades_funcionales_y_recursos(session, config)
    crear_productos_y_holones(session, config)
    crear_conectividad(session, config)
    crear_orden_prueba(session)
    
    # 4. Asignar estados finales al final (después de todas las modificaciones)
    print("\n[8/7] Asignando estados finales desde YAML de patrones procesados...")
    procesados_dir = base_path / "importacion" / "procesados"
    asignar_estados_finales_todos_patrones(Session, procesados_dir)
    
    # 5. Commit final
    session.commit()
    
    print("\n" + "=" * 60)
    print("✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()