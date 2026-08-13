# routes/operador.py
from flask import Blueprint, render_template, jsonify, request
from .auth import login_required
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from modelos.ProcesoOcurrente import OrdenProduccion, InstanciaRed, EventoRed
from modelos.Producto import HolonRuta
from datetime import datetime
import json
import os

# Crear el Blueprint
operador_bp = Blueprint('operador', __name__)

def recargar_instancias_desde_bd():
    """Recupera instancias activas desde BD al iniciar el motor"""
    from flask import current_app
    from modelos.ProcesoOcurrente import InstanciaRed
    from utils.motor_abtppn import TokenColoreado
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    motor = current_app.config['MOTOR']
    
    instancias_activas = session.query(InstanciaRed).filter_by(activa=True).all()
    
    for inst_bd in instancias_activas:
        # Verificar si ya está en memoria
        ya_existe = False
        for mem_id, inst_mem in motor.instancias.items():
            if inst_mem.instancia_bd_id == inst_bd.id:
                ya_existe = True
                break
        
        if not ya_existe:
            # Reconstruir token
            token = None
            if inst_bd.token_o:
                token = TokenColoreado(
                    orden_id=inst_bd.token_o,
                    material=inst_bd.token_m or 0,
                    coste=inst_bd.token_c or 0,
                    timestamp=inst_bd.token_t or datetime.now()
                )
            
            # Cargar la red
            red_nombre = "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml"  # Obtener de algún lado
            red = motor.cargar_red(red_nombre)
            
            if red:
                marcado = json.loads(inst_bd.marcado) if inst_bd.marcado else {}
                
                # Crear instancia en memoria
                from utils.motor_abtppn import InstanciaRedMemoria
                nueva_instancia = InstanciaRedMemoria(
                    id=motor.proximo_id,
                    instancia_bd_id=inst_bd.id,
                    orden_id=inst_bd.orden_id,
                    red=red,
                    marcado=marcado,
                    token=token,
                    activa=inst_bd.activa
                )
                motor.instancias[motor.proximo_id] = nueva_instancia
                motor.proximo_id += 1
                print(f"🔄 Instancia recargada: ID {nueva_instancia.id} (BD: {inst_bd.id})")
    
    session.close()


def get_motor():
    """Obtiene el motor global y crea una sesión nueva"""
    from flask import current_app
    
    motor = current_app.config.get('MOTOR')
    if not motor:
        raise Exception("Motor no configurado en app")
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    
    # Actualizar la sesión del motor para este request
    motor.db_session = session
    
    return motor, session


@operador_bp.route('/operador')
@login_required
def dashboard():
    """Panel principal del operador - Qué hacer hoy"""
    return render_template('operador/dashboard.html')


@operador_bp.route('/operador/api/ordenes_activas')
@login_required
def api_ordenes_activas():
    """Retorna órdenes en ejecución con su estado"""
    motor, session = get_motor()
    
    try:
        # Buscar órdenes en estado 'en_proceso'
        ordenes = session.query(OrdenProduccion).filter(
            OrdenProduccion.estado.in_(['planificada', 'en_proceso']),
            OrdenProduccion.archivada == False
        ).all()
        
        resultado = []
        for orden in ordenes:
            # Obtener instancias activas para esta orden
            instancias = session.query(InstanciaRed).filter_by(
                orden_id=orden.id,
                activa=True
            ).all()
            
            # Obtener el holon_ruta para mostrar el producto
            holon = session.query(HolonRuta).filter_by(id=orden.holon_ruta_id).first()
            nombre_producto = "N/A"
            if holon and holon.producto:
                nombre_producto = holon.producto.nombre
            
            resultado.append({
                'id': orden.id,
                'holon_ruta_id': orden.holon_ruta_id,
                'producto_nombre': nombre_producto,
                'cantidad': orden.cantidad,
                'estado': orden.estado,
                'fecha_creacion': orden.fecha_creacion.isoformat(),
                'plazo_entrega': orden.plazo_entrega.isoformat(),
                'instancias_activas': len(instancias),
                'instancias': [{
                    'id': inst.id,
                    'tipo': inst.tipo,
                    'activa': inst.activa,
                    'marcado': json.loads(inst.marcado) if inst.marcado else {},
                    'token_m': inst.token_m,
                    'token_c': inst.token_c,
                    'token_t': inst.token_t.isoformat() if inst.token_t else None
                } for inst in instancias]
            })
        
        session.close()
        return jsonify({'success': True, 'ordenes': resultado})
    
    except Exception as e:
        session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/instancia/<int:instancia_id>/transiciones')
@login_required
def api_instancia_transiciones(instancia_id):
    """Retorna las transiciones habilitadas para una instancia"""
    motor, session = get_motor()
    
    try:
        transiciones_habilitadas = []
        
        print(f"🔍 Buscando instancia {instancia_id} en memoria...")
        print(f"   Instancias en motor: {list(motor.instancias.keys())}")
        
        # Buscar en instancias del motor
        for mem_id, inst_mem in motor.instancias.items():
            print(f"   Comparando mem_id={mem_id}, instancia_bd_id={inst_mem.instancia_bd_id}")
            if inst_mem.instancia_bd_id == instancia_id:
                transiciones = inst_mem.obtener_transiciones_habilitadas()
                transiciones_habilitadas = [
                    {'id': t[0], 'nombre': t[1].nombre} 
                    for t in transiciones
                ]
                print(f"   ✅ Encontrada! Transiciones: {transiciones_habilitadas}")
                break
        
        if not transiciones_habilitadas:
            print(f"   ⚠️ No se encontraron transiciones para instancia {instancia_id}")
        
        session.close()
        return jsonify({'success': True, 'instancia_id': instancia_id, 'transiciones': transiciones_habilitadas})
    
    except Exception as e:
        session.close()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/disparar', methods=['POST'])
@login_required
def api_disparar():
    """Dispara una transición en una instancia"""
    data = request.get_json()
    
    instancia_id = data.get('instancia_id')
    transicion_id = data.get('transicion_id')
    invariantes = data.get('invariantes', {})
    
    if not instancia_id or not transicion_id:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
    
    motor, session = get_motor()
    
    try:
        # Buscar la instancia en memoria
        instancia_mem_id = None
        for mem_id, inst_mem in motor.instancias.items():
            if inst_mem.instancia_bd_id == instancia_id:
                instancia_mem_id = mem_id
                break
        
        if not instancia_mem_id:
            return jsonify({'success': False, 'error': 'Instancia no está en memoria'}), 400
        
        # Disparar
        exito, mensaje = motor.disparar(instancia_mem_id, transicion_id, invariantes)
        
        session.commit()
        session.close()
        
        return jsonify({'success': exito, 'mensaje': mensaje})
    
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/instancia/<int:instancia_id>/estado')
@login_required
def api_instancia_estado(instancia_id):
    """Retorna estado detallado de una instancia"""
    motor, session = get_motor()
    
    try:
        # Buscar en memoria
        estado = None
        for mem_id, inst_mem in motor.instancias.items():
            if inst_mem.instancia_bd_id == instancia_id:
                estado = inst_mem.obtener_estado()
                break
        
        if not estado:
            # Buscar en BD
            instancia_bd = session.query(InstanciaRed).filter_by(id=instancia_id).first()
            if instancia_bd:
                estado = {
                    'id': instancia_bd.id,
                    'orden_id': instancia_bd.orden_id,
                    'tipo': instancia_bd.tipo,
                    'activa': instancia_bd.activa,
                    'marcado': json.loads(instancia_bd.marcado) if instancia_bd.marcado else {},
                    'token_o': instancia_bd.token_o,
                    'token_m': instancia_bd.token_m,
                    'token_c': instancia_bd.token_c,
                    'token_t': instancia_bd.token_t.isoformat() if instancia_bd.token_t else None,
                    'fecha_creacion': instancia_bd.fecha_creacion.isoformat(),
                    'fecha_cierre': instancia_bd.fecha_cierre.isoformat() if instancia_bd.fecha_cierre else None
                }
        
        session.close()
        return jsonify({'success': True, 'estado': estado})
    
    except Exception as e:
        session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/historial/<int:orden_id>')
@login_required
def api_historial(orden_id):
    """Retorna historial de eventos de una orden"""
    motor, session = get_motor()
    
    try:
        historial = motor.obtener_historial(orden_id)
        session.close()
        return jsonify({'success': True, 'historial': historial})
    
    except Exception as e:
        session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/crear_orden', methods=['POST'])
@login_required
def api_crear_orden():
    """Crea una nueva orden de producción y la instancia en el motor"""
    data = request.get_json()
    
    holon_ruta_id = data.get('holon_ruta_id')
    cantidad = data.get('cantidad', 0)
    plazo_entrega = data.get('plazo_entrega')
    red_pnml = data.get('red_pnml')
    
    if not holon_ruta_id or not red_pnml:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
    
    motor, session = get_motor()
    orden_id = None
    
    try:
        # Verificar si ya existe una orden activa para evitar duplicados
        orden_existente = session.query(OrdenProduccion).filter_by(
            holon_ruta_id=holon_ruta_id,
            estado='en_proceso',
            archivada=False
        ).first()
        
        if orden_existente:
            session.close()
            return jsonify({'success': False, 'error': f'Ya existe una orden activa (ID: {orden_existente.id})'}), 400
        
        # Crear orden en BD
        orden = OrdenProduccion(
            holon_ruta_id=holon_ruta_id,
            cantidad=cantidad,
            plazo_entrega=datetime.fromisoformat(plazo_entrega) if plazo_entrega else datetime.now(),
            estado='en_proceso'
        )
        session.add(orden)
        session.flush()  # Esto asigna el ID sin cerrar la transacción
        orden_id = orden.id  # ✅ Guardar el ID ANTES de cerrar la sesión
        session.commit()
        
        print(f"📝 Orden creada en BD: ID {orden_id}")
        
        # Crear token inicial
        token = TokenColoreado(
            orden_id=f"ORD-{orden_id}",
            material=cantidad,
            coste=0.0,
            timestamp=datetime.now()
        )
        
        # Configurar refinamientos (desde BD o manual)
        motor.configurar_refinamiento(
            "Pintuco_BaseAgua_Dis_Dil_IntegracionRedes_V4.pnml",
            "Iniciar disp",
            "Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml"
        )
        
        motor.mapeo_eventos["Pintuco_BaseAgua_dispersion_RedHija_Dis_Dil_V1.pnml"] = {
            "Libre": "27",
            "Descargar": "11",
            "Transportar": "3"
        }
        
        # Configurar parámetros de operación (si no están cargados)
        if not motor.parametros_operacion:
            motor.parametros_operacion = {
                "OrdenEn WIP": {"duracion_estimada": 10, "costo_por_hora": 50, "eficiencia": 1.0},
                "Iniciar disp": {"duracion_estimada": 5, "costo_por_hora": 30, "eficiencia": 1.0},
                "Dispersando": {"duracion_estimada": 120, "costo_por_hora": 100, "eficiencia": 0.97},
                "Diluyendo": {"duracion_estimada": 90, "costo_por_hora": 80, "eficiencia": 0.99}
            }
        
        # Crear instancia en el motor
        instancia_id = motor.crear_instancia(
            red_pnml,
            orden_id,  # Usar el ID guardado
            token
        )
        
        print(f"✅ Instancia creada en motor: ID {instancia_id}")
        
        # Verificar que la instancia se creó correctamente
        if instancia_id not in motor.instancias:
            session.close()
            return jsonify({'success': False, 'error': 'La instancia no se creó correctamente en el motor'}), 500
        
        instancia = motor.instancias[instancia_id]
        transiciones = instancia.obtener_transiciones_habilitadas()
        transiciones_nombres = [t[1].nombre for t in transiciones]
        print(f"   Transiciones habilitadas iniciales: {transiciones_nombres}")
        
        session.close()
        
        return jsonify({
            'success': True, 
            'orden_id': orden_id,
            'instancia_id': instancia_id,
            'transiciones_habilitadas': transiciones_nombres,
            'mensaje': f'Orden {orden_id} creada exitosamente'
        })
    
    except Exception as e:
        session.rollback()
        session.close()
        print(f"❌ Error al crear orden: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@operador_bp.route('/operador/api/orquestador/estado')
@login_required
def api_orquestador_estado():
    """Retorna si el bucle está activo."""
    from flask import current_app
    orq = current_app.config.get('ORQUESTADOR')
    if not orq:
        return jsonify({'success': False, 'error': 'Orquestador no inicializado'})
    return jsonify({
        'success': True,
        'activo': getattr(orq, '_bucle_activo', False)
    })

@operador_bp.route('/operador/api/orquestador/reiniciar', methods=['POST'])
@login_required
def api_orquestador_reiniciar():
    """Reinicia el bucle (útil si se detuvo por error)."""
    from flask import current_app
    orq = current_app.config.get('ORQUESTADOR')
    if orq:
        if getattr(orq, '_bucle_activo', False):
            orq.detener_bucle()
        orq.iniciar_bucle(session_factory=SessionLocal, intervalo_segundos=5)
        return jsonify({'success': True, 'mensaje': 'Bucle reiniciado'})
    return jsonify({'success': False, 'error': 'Orquestador no disponible'}), 500