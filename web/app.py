import sys
import os
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuración de rutas de importación para FÉNIX Core y Web
ROOT_DIR = Path(__file__).resolve().parent.parent
FENIX_DIR = ROOT_DIR / "fenix"
WEB_DIR = ROOT_DIR / "web"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FENIX_DIR))
sys.path.insert(0, str(WEB_DIR))

from routes.auth import auth_bp
from routes.carga_recursos import carga_recursos_bp
from routes.operador import operador_bp
from routes.cargas_validadas import cargas_validadas_bp
from routes.planificador import planificador_bp
from routes.aprendizaje import aprendizaje_bp
from routes.mes import mes_bp

# Modelos y servicios del núcleo FÉNIX
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from servicios.seguimiento_ordenes import ServicioSeguimiento
from servicios.cola_eventos import ServicioColaEventos
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN

# Inicializar Flask
app = Flask(__name__, template_folder=str(WEB_DIR / "templates"), static_folder=str(WEB_DIR / "static"))
app.secret_key = 'fenix-pyme-2024-cambiar-en-produccion'

# ==================== CONFIGURACIÓN BD ====================
DB_PATH = FENIX_DIR / 'fenix.db'
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)

# ==================== ORQUESTADOR GLOBAL (compartido) ====================
# El orquestador se crea una sola vez y se reutiliza en toda la app
motor = MotorABTPPN()
orquestador = Orquestador(motor, SessionLocal())
orquestador.cargar_configuracion_desde_bd()

# Registrar en app para acceso en rutas
app.config['ENGINE'] = engine
app.config['SESSION_MAKER'] = SessionLocal
app.config['ORQUESTADOR'] = orquestador
app.config['MOTOR'] = motor

# ==================== SERVICIOS ====================
def get_seguimiento():
    """Retorna una instancia de ServicioSeguimiento con sesión nueva"""
    session = SessionLocal()
    return ServicioSeguimiento(session)

# ==================== BLUEPRINTS ====================
app.register_blueprint(auth_bp)
app.register_blueprint(carga_recursos_bp)
app.register_blueprint(operador_bp)
app.register_blueprint(cargas_validadas_bp)
app.register_blueprint(planificador_bp)
app.register_blueprint(aprendizaje_bp)
app.register_blueprint(mes_bp)

# ==================== SEGMENTACIÓN DE RED OT / IT (ISA/IEC 62443) ====================
# El servidor FÉNIX actúa como puente seguro entre dos redes separadas:
#   1. Red Empresarial / Negocio (IT - Puerto por defecto 5000):
#      Acceso a Planificación ABC (/planificador), Centro MES (/mes), Cargas (/cargas/validar)
#      y Lazo de Aprendizaje (/aprendizaje).
#   2. Red Aislada de Piso de Planta / Borde (OT - Puerto por defecto 5001):
#      Red segura donde residen los nodos Arduino+Raspberry Pi (Modo C), PLCs/SCADA (Modo B)
#      y Tablets de Operador (Modo A). En este puerto se aplica una lista blanca estricta:
#      solo se permite el acceso a la pasarela de ingesta (/api/ingesta/*) y operación (/operador*).
app.config['FENIX_IT_HOST'] = os.environ.get('FENIX_IT_HOST', '0.0.0.0')
app.config['FENIX_IT_PORT'] = int(os.environ.get('FENIX_IT_PORT', '5000'))
app.config['FENIX_OT_HOST'] = os.environ.get('FENIX_OT_HOST', '0.0.0.0')
app.config['FENIX_OT_PORT'] = int(os.environ.get('FENIX_OT_PORT', '5001'))

PREFIJOS_PERMITIDOS_RED_OT = (
    '/api/ingesta/',
    '/api/orden/',
    '/operador',
    '/login',
    '/logout',
    '/static/'
)


@app.before_request
def verificar_aislamiento_red_ot():
    """
    Política de seguridad perimetral OT/IT:
    Si la petición ingresa por el puerto exclusivo de la Red Aislada de Planta (OT, ej. :5001)
    o incluye la cabecera X-Fenix-Zone: OT, bloquea cualquier acceso a las interfaces
    administrativas, de planificación financiera o de modificación de ontología.
    """
    puerto_ot = str(current_app_ot_port := app.config.get('FENIX_OT_PORT', 5001))
    host_header = request.host or ''
    zona_header = (request.headers.get('X-Fenix-Zone') or '').upper()
    es_canal_ot = host_header.endswith(f':{puerto_ot}') or zona_header == 'OT'

    if es_canal_ot:
        ruta = request.path or '/'
        if ruta == '/':
            return redirect(url_for('operador.dashboard'))
        if not any(ruta.startswith(pref) for pref in PREFIJOS_PERMITIDOS_RED_OT):
            return jsonify({
                'success': False,
                'error': (
                    f'Acceso bloqueado por política de aislamiento OT/IT (ISA/IEC 62443): '
                    f'La ruta "{ruta}" pertenece a la Red de Empresa (IT) y no está expuesta '
                    f'en el puerto de la Red Aislada de Planta (OT :{puerto_ot}).'
                )
            }), 403


# ==================== RUTAS PRINCIPALES ====================
@app.route('/')
def index():
    if 'usuario_id' in session:
        if session.get('usuario_rol') == 'admin':
            return redirect(url_for('operador.dashboard'))
        else:
            return redirect(url_for('operador.dashboard'))
    return redirect(url_for('auth.login'))

# ==================== API PARA OPERADOR ====================
@app.route('/api/orden/crear', methods=['POST'])
def api_crear_orden():
    """
    Crea una nueva orden de producción.
    Body JSON: {
        "producto_id": 1,
        "cantidad": 500,
        "prioridad": 1,
        "cliente": "Cliente X"
    }
    """
    data = request.get_json()
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad')
    prioridad = data.get('prioridad', 1)
    cliente = data.get('cliente')

    if not producto_id or not cantidad:
        return jsonify({'error': 'Faltan producto_id o cantidad'}), 400

    seguimiento = get_seguimiento()
    try:
        orden = seguimiento.crear_orden(producto_id, cantidad, prioridad, cliente)
        return jsonify({
            'success': True,
            'orden_id': orden.id,
            'numero_orden': orden.numero_orden,
            'estado': orden.estado
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        seguimiento.session.close()

@app.route('/api/orden/<int:orden_id>/iniciar', methods=['POST'])
def api_iniciar_orden(orden_id):
    """Inicia la ejecución de una orden pendiente"""
    seguimiento = get_seguimiento()
    try:
        exito = seguimiento.iniciar_ejecucion(orden_id)
        if exito:
            return jsonify({'success': True, 'mensaje': f'Orden {orden_id} iniciada'})
        else:
            return jsonify({'error': 'No se pudo iniciar la orden'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        seguimiento.session.close()

@app.route('/api/orden/<int:orden_id>/estado', methods=['GET'])
def api_estado_orden(orden_id):
    """Consulta el estado actual de una orden"""
    seguimiento = get_seguimiento()
    try:
        estado = seguimiento.obtener_estado(orden_id)
        return jsonify(estado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        seguimiento.session.close()

@app.route('/api/orden/<int:orden_id>/evento', methods=['POST'])
def api_enviar_evento(orden_id):
    """
    Encola un evento manual (operador) para ser procesado por main.py.
    Body: {
        "red": "nombre_red",
        "transicion": "nombre_transicion",
        "recurso": "codigo_recurso",
        "datos": {}
    }
    """
    data = request.get_json()
    red_nombre = data.get('red')
    transicion_nombre = data.get('transicion')
    recurso = data.get('recurso')
    datos = data.get('datos', {})

    if not red_nombre or not transicion_nombre:
        return jsonify({'error': 'Faltan red o transicion'}), 400

    session = SessionLocal()
    try:
        servicio_cola = ServicioColaEventos(session)
        evento = servicio_cola.encolar(
            orden_id=orden_id,
            red_nombre=red_nombre,
            transicion_nombre=transicion_nombre,
            datos={
                'recurso': recurso,
                'timestamp': datetime.now().isoformat(),
                **datos
            }
        )
        session.commit()
        return jsonify({
            'success': True,
            'evento_id': evento.id,
            'mensaje': f'Evento {transicion_nombre} encolado para orden {orden_id}'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

# ==================== ENDPOINTS PARA DISEÑADOR (carga de productos, redes, etc.) ====================
# Estos endpoints deberían delegar en los importadores (ej. importador_patrones, importador_taxonomia)
# Por ahora, redirigimos a los blueprints existentes (carga_recursos, etc.)

@app.route('/carga/encadenamiento', methods=['GET', 'POST'])
def carga_encadenamiento():
    """Vista para cargar archivo de encadenamiento Excel"""
    if request.method == 'GET':
        return render_template('carga_encadenamiento.html')
    
    if 'archivo' not in request.files:
        return render_template('carga_errores.html', errores=["No se seleccionó ningún archivo"])
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return render_template('carga_errores.html', errores=["No se seleccionó ningún archivo"])
    
    # Guardar archivo temporal
    filepath = os.path.join('uploads', archivo.filename)
    archivo.save(filepath)
    
    # Validar e importar usando tus importadores
    from validadores.validador_encadenamiento import ValidadorEncadenamientoExcel
    from importadores.importador_encadenamiento import ImportadorEncadenamiento
    
    validador = ValidadorEncadenamientoExcel(filepath)
    es_valido, reglas, errores = validador.validar()
    
    if not es_valido:
        return render_template('carga_errores.html', errores=errores)
    
    with SessionLocal() as session:
        importador = ImportadorEncadenamiento(session)
        if importador.importar(reglas, archivo.filename.replace('.xlsx', '')):
            return redirect(url_for('dashboard'))
        else:
            return render_template('carga_errores.html', errores=["Error al importar a la base de datos"])

# Nota: El resto de rutas de carga (productos, taxonomía, etc.) ya están en sus blueprints.

@app.route('/admin/cargar_red', methods=['POST'])
def cargar_red():
    pnml_file = request.files['pnml']
    yaml_file = request.files.get('yaml')
    # Guardar temporalmente, validar, insertar
    # ...


# ==================== INICIO DUAL-PORT (RED IT + RED AISLADA OT) ====================
if __name__ == '__main__':
    import threading
    from werkzeug.serving import make_server

    it_host = app.config['FENIX_IT_HOST']
    it_port = app.config['FENIX_IT_PORT']
    ot_host = app.config['FENIX_OT_HOST']
    ot_port = app.config['FENIX_OT_PORT']
    habilitar_ot = os.environ.get('FENIX_HABILITAR_PUERTO_OT', '1') == '1'

    print("🚀 Iniciando Servidor Central FÉNIX con Segmentación de Red OT / IT")
    print(f"   🏢 Puerto hacia Red de Empresa (IT)        : http://{it_host}:{it_port}  (/mes, /planificador, /cargas, /aprendizaje)")

    if habilitar_ot and ot_port != it_port:
        servidor_ot = make_server(ot_host, ot_port, app, threaded=True)
        hilo_ot = threading.Thread(target=servidor_ot.serve_forever, daemon=True)
        hilo_ot.start()
        print(f"   🛡️  Puerto hacia Red Aislada de Planta (OT) : http://{ot_host}:{ot_port}  (SOLO /api/ingesta/evento_planta y /operador)")

    app.run(debug=False, host=it_host, port=it_port, threaded=True)