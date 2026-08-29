from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from routes.auth import auth_bp
from routes.carga_recursos import carga_recursos_bp
from routes.operador import operador_bp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import json

# Modelos y servicios
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed
from servicios.seguimiento_ordenes import ServicioSeguimiento
from servicios.cola_eventos import ServicioColaEventos
from servicios.orquestador import Orquestador
from utils.motor_abtppn import MotorABTPPN

# Inicializar Flask
app = Flask(__name__)
app.secret_key = 'fenix-pyme-2024-cambiar-en-produccion'

# ==================== CONFIGURACIÓN BD ====================
DATABASE_URL = 'sqlite:///fenix.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)

# ==================== ORQUESTADOR GLOBAL (compartido) ====================
# El orquestador se crea una sola vez y se reutiliza en toda la app
# Nota: No configuramos refinamientos ni mapeos manuales; esos vienen de BD.
motor = MotorABTPPN()  # sin directorio PNML, porque las redes se cargan desde BD
orquestador = Orquestador(motor, SessionLocal())
orquestador.cargar_configuracion_desde_bd()

# Registrar en app para acceso en rutas
app.config['ENGINE'] = engine
app.config['SESSION_MAKER'] = SessionLocal
app.config['ORQUESTADOR'] = orquestador
app.config['MOTOR'] = motor  # por si alguna ruta vieja lo necesita, pero idealmente usar orquestador

# ==================== SERVICIOS ====================
def get_seguimiento():
    """Retorna una instancia de ServicioSeguimiento con sesión nueva"""
    session = SessionLocal()
    return ServicioSeguimiento(session)

# ==================== BLUEPRINTS ====================
app.register_blueprint(auth_bp)
app.register_blueprint(carga_recursos_bp)
app.register_blueprint(operador_bp)

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


# ==================== INICIO ====================
if __name__ == '__main__':
    # Cargar datos iniciales si es necesario (podría llamar a init_prueba.main() una vez)
    # Pero no queremos ejecutar init_prueba cada vez que arranca la app.
    print("🚀 Iniciando servidor web FÉNIX")
    print("   El orquestador principal debe correr en otro proceso (main.py)")
    print("   Los eventos se encolan en BD y son procesados por main.py")
    app.run(debug=True, host='0.0.0.0', port=5000)