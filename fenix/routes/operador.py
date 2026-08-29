# routes/operador.py
from flask import Blueprint, render_template, jsonify, request, current_app
from .auth import login_required
from utils.motor_abtppn import MotorABTPPN, TokenColoreado
from modelos.ProcesoOcurrente import OrdenProduccion, InstanciaRed, EventoRed
from modelos.Producto import HolonRuta, Producto, AsignacionRecurso
from modelos.Recursos import Recurso
from servicios.planificador import PlanificadorProduccion
from datetime import datetime
import json
import os

# Crear el Blueprint
operador_bp = Blueprint('operador', __name__)

def recargar_instancias_desde_bd():
    """Recupera instancias activas desde BD y sincroniza el estado en memoria de Flask"""
    from flask import current_app
    from modelos.ProcesoOcurrente import InstanciaRed
    from utils.motor_abtppn import TokenColoreado
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    motor = current_app.config['MOTOR']
    orquestador = current_app.config['ORQUESTADOR']
    
    instancias_activas = session.query(InstanciaRed).filter_by(activa=True).all()
    
    for inst_bd in instancias_activas:
        # Verificar si ya está en memoria
        ya_existe = False
        for mem_id, inst_mem in motor.instancias.items():
            if inst_mem.instancia_bd_id == inst_bd.id:
                # Sincronizar estado actual
                inst_mem.marcado = inst_bd.marcado if isinstance(inst_bd.marcado, dict) else (json.loads(inst_bd.marcado) if inst_bd.marcado else {})
                inst_mem.token_o = inst_bd.token_o
                inst_mem.token_m = inst_bd.token_m or 0.0
                inst_mem.token_c = inst_bd.token_c or 0.0
                inst_mem.token_t = inst_bd.token_t
                if not inst_mem.red:
                    inst_mem.red = motor.redes_cargadas.get(inst_mem.red_nombre) or orquestador.cargar_red_desde_bd(inst_mem.red_nombre)
                ya_existe = True
                break
        
        if not ya_existe:
            # Reconstruir token
            token = TokenColoreado(
                orden_id=inst_bd.token_o or f"ORD-{inst_bd.orden_id}",
                material=inst_bd.token_m or 0.0,
                coste=inst_bd.token_c or 0.0,
                timestamp=inst_bd.token_t or datetime.now()
            )
            
            # Cargar la red
            red_nombre = inst_bd.tipo
            red = orquestador.cargar_red_desde_bd(red_nombre)
            if red and red_nombre not in motor.redes_cargadas:
                motor.redes_cargadas[red_nombre] = red
            
            if red:
                marcado = inst_bd.marcado if isinstance(inst_bd.marcado, dict) else (json.loads(inst_bd.marcado) if inst_bd.marcado else {})
                
                # Crear instancia en memoria
                from utils.motor_abtppn import InstanciaRedMem as InstanciaRedMemoria
                nueva_instancia = InstanciaRedMemoria(
                    id=motor.proximo_id,
                    red_nombre=red_nombre,
                    orden_id=inst_bd.orden_id,
                    marcado=marcado,
                    token=token
                )
                nueva_instancia.bd_id = inst_bd.id
                nueva_instancia.red = red
                motor.instancias[motor.proximo_id] = nueva_instancia
                motor.proximo_id += 1
                print(f"🔄 Instancia recargada: ID {nueva_instancia.id} (BD: {inst_bd.id}, tipo: {red_nombre})")
    
    session.close()


def get_motor():
    """Obtiene el motor global, recarga las instancias de la BD y crea una sesión nueva"""
    from flask import current_app
    
    motor = current_app.config.get('MOTOR')
    if not motor:
        raise Exception("Motor no configurado en app")
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    
    # Actualizar la sesión del motor para este request
    motor.db_session = session
    
    # Sincronizar instancias en memoria con la BD
    recargar_instancias_desde_bd()
    
    return motor, session


@operador_bp.route('/operador')
@login_required
def dashboard():
    """Panel principal del operador - Qué hacer hoy"""
    return render_template('operador/dashboard.html')


@operador_bp.route('/operador/api/ordenes_activas')
@login_required
def api_ordenes_activas():
    """Retorna órdenes en ejecución con su estado, productos y eficiencias de recursos"""
    motor, session = get_motor()
    
    try:
        # Buscar órdenes en estado 'pendiente', 'planificada', 'en_proceso'
        ordenes = session.query(OrdenProduccion).filter(
            OrdenProduccion.estado.in_(['pendiente', 'planificada', 'en_proceso', 'en_produccion']),
            OrdenProduccion.archivada == False
        ).all()
        
        resultado = []
        for orden in ordenes:
            instancias = session.query(InstanciaRed).filter_by(
                orden_id=orden.id,
                activa=True
            ).all()
            
            holon = session.query(HolonRuta).filter_by(id=orden.holon_ruta_id).first()
            nombre_producto = "N/A"
            if holon and holon.producto:
                nombre_producto = holon.producto.nombre
            
            resultado.append({
                'id': orden.id,
                'numero_orden': orden.numero_orden or f"ORD-{orden.id}",
                'holon_ruta_id': orden.holon_ruta_id,
                'producto_nombre': nombre_producto,
                'cantidad': orden.cantidad,
                'estado': orden.estado,
                'fecha_creacion': orden.fecha_solicitud.isoformat() if orden.fecha_solicitud else datetime.now().isoformat(),
                'plazo_entrega': orden.plazo_entrega.isoformat() if orden.plazo_entrega else datetime.now().isoformat(),
                'instancias_activas': len(instancias),
                'instancias': [{
                    'id': inst.id,
                    'tipo': inst.tipo,
                    'activa': inst.activa,
                    'marcado': inst.marcado if isinstance(inst.marcado, dict) else (json.loads(inst.marcado) if inst.marcado else {}),
                    'token_m': inst.token_m,
                    'token_c': inst.token_c,
                    'token_t': inst.token_t.isoformat() if inst.token_t else None
                } for inst in instancias]
            })
        
        # Obtener todos los productos para cargarlos dinámicamente en el selector
        productos = session.query(Producto).all()
        productos_lista = [{'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre} for p in productos]
        
        # Obtener eficiencias de recursos actuales para visualización
        asigs = session.query(AsignacionRecurso).all()
        recursos_eficiencias = {}
        for a in asigs:
            if a.recurso:
                recursos_eficiencias[a.recurso.nombre] = a.eficiencia_real or 1.0
                
        session.close()
        return jsonify({
            'success': True, 
            'ordenes': resultado,
            'productos': productos_lista,
            'eficiencias': recursos_eficiencias
        })
    
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
                transiciones = motor.obtener_transiciones_habilitadas(mem_id, tiene_mensaje_externo=True)
                transiciones_habilitadas = [
                    {'id': tid, 'nombre': inst_mem.red.transitions[tid].nombre or tid} 
                    for tid in transiciones
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
    """Dispara una transición en una instancia usando el Orquestador y validando invariantes"""
    from flask import session as flask_session
    data = request.get_json()
    
    instancia_id = data.get('instancia_id')
    transicion_id = data.get('transicion_id')
    invariantes = data.get('invariantes', {})  # Mediciones físicas del SCADA
    forzar = data.get('forzar', False)         # Bypass de invariantes
    
    if forzar and flask_session.get('usuario_rol') not in ['admin', 'supervisor']:
        return jsonify({'success': False, 'mensaje': '⚠️ Acceso denegado: Se requiere rol de administrador o supervisor para bypass.'}), 403
        
    if not instancia_id or not transicion_id:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
    from flask import current_app
    orquestador = current_app.config['ORQUESTADOR']
    motor = current_app.config['MOTOR']
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    
    try:
        # 1. Obtener la InstanciaRed de la BD
        inst_bd = session.query(InstanciaRed).get(instancia_id)
        if not inst_bd:
            session.close()
            return jsonify({'success': False, 'error': 'Instancia no encontrada en BD'}), 404
            
        orden_id = inst_bd.orden_id
        red_nombre = inst_bd.tipo
        
        # 2. Buscar en memoria
        instancia_mem = None
        for inst in motor.instancias.values():
            if inst.instancia_bd_id == instancia_id:
                instancia_mem = inst
                break
                
        if not instancia_mem:
            session.close()
            return jsonify({'success': False, 'error': 'Instancia no activa en memoria'}), 400
            
        # 3. Obtener el nombre de la transición física para orquestador
        transicion_obj = instancia_mem.red.transitions.get(transicion_id)
        if not transicion_obj:
            session.close()
            return jsonify({'success': False, 'error': f'Transición {transicion_id} no encontrada'}), 400
            
        evento_nombre = transicion_obj.nombre or transicion_id
        
        # 4. Determinar recurso físico asociado
        from modelos.DocumentosNegocio import OrdenProduccion
        orden = session.query(OrdenProduccion).get(orden_id)
        recurso_nombre = None
        if orden and orden.asignacion_recursos:
            in_places = [a.source for a in instancia_mem.red.arcs.values() if a.target == transicion_id]
            if in_places:
                lugar_origen_nombre = instancia_mem.red.places[in_places[0]].nombre
                for etapa_key, res_val in orden.asignacion_recursos.items():
                    if etapa_key.lower() in lugar_origen_nombre.lower() or lugar_origen_nombre.lower() in etapa_key.lower():
                        recurso_nombre = res_val.get('recurso_nombre')
                        break
                        
        # 5. Temporalmente apuntar la sesión del orquestador a nuestra sesión del request
        orquestador.session = session
        
        # 6. Procesar evento a través del Orquestador (aquí se chequean invariantes)
        try:
            exito = orquestador.procesar_evento_planta(
                orden_id=orden_id,
                evento_nombre=evento_nombre,
                recurso_nombre=recurso_nombre,
                red_nombre=red_nombre,
                timestamp=datetime.now(),
                mediciones=invariantes,
                forzar=forzar
            )
        except ValueError as ve:
            session.rollback()
            session.close()
            return jsonify({
                'success': False, 
                'mensaje': f'⚠️ ALERTA DE SEGURIDAD FÍSICA: Avance bloqueado. {str(ve)}'
            })
            
        if exito:
            # Estabilizar e informar
            orquestador.estabilizar_red(orden_id)
            orquestador._verificar_y_finalizar_orden(orden_id)
            session.commit()
            session.close()
            return jsonify({'success': True, 'mensaje': f'Acción "{evento_nombre}" ejecutada con éxito.'})
        else:
            session.close()
            return jsonify({'success': False, 'mensaje': 'La transición no está habilitada o no cumple las condiciones.'})
            
    except Exception as e:
        session.rollback()
        session.close()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/forzar_marcado', methods=['POST'])
@login_required
def api_forzar_marcado():
    """Forza el marcado (token) a un lugar específico bypassando las transiciones"""
    from flask import session as flask_session
    if flask_session.get('usuario_rol') not in ['admin', 'supervisor']:
        return jsonify({'success': False, 'mensaje': '⚠️ Acceso denegado: Se requiere rol de administrador o supervisor.'}), 403
        
    data = request.get_json()
    instancia_id = data.get('instancia_id')
    nuevo_marcado = data.get('marcado') # Diccionario, ej: {"p5": 1}
    
    if not instancia_id or not nuevo_marcado:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
    motor, session = get_motor()
    
    try:
        # 1. Actualizar en base de datos
        inst_bd = session.query(InstanciaRed).get(instancia_id)
        if not inst_bd:
            session.close()
            return jsonify({'success': False, 'error': 'Instancia no encontrada en BD'}), 404
            
        inst_bd.marcado = json.dumps(nuevo_marcado)
        session.commit()
        
        # 2. Sincronizar en memoria
        for inst_mem in motor.instancias.values():
            if inst_mem.instancia_bd_id == instancia_id:
                inst_mem.marcado = nuevo_marcado.copy()
                print(f"🔄 Marcado forzado en memoria para instancia BD {instancia_id}: {nuevo_marcado}")
                break
                
        session.close()
        return jsonify({'success': True, 'mensaje': 'Marcado de la red alineado manualmente con éxito.'})
        
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@operador_bp.route('/operador/api/control_calidad', methods=['POST'])
@login_required
def api_control_calidad():
    """Recibe mediciones de calidad de laboratorio y las evalúa contra especificaciones"""
    data = request.get_json()
    
    instancia_id = data.get('instancia_id')
    mediciones_qc = data.get('mediciones_qc', {})
    
    if not instancia_id or not mediciones_qc:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
    from flask import current_app
    orquestador = current_app.config['ORQUESTADOR']
    
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    
    try:
        inst_bd = session.query(InstanciaRed).get(instancia_id)
        if not inst_bd:
            session.close()
            return jsonify({'success': False, 'error': 'Instancia no encontrada'}), 404
            
        orden_id = inst_bd.orden_id
        red_nombre = inst_bd.tipo
        
        # En la BD cargada, el recurso QA se asume que es "Laboratorio de Calidad"
        recurso_nombre = "Laboratorio de Calidad"
        
        orquestador.session = session
        
        exito = orquestador.procesar_control_calidad(
            orden_id=orden_id,
            recurso_nombre=recurso_nombre,
            mediciones_qc=mediciones_qc,
            red_nombre=red_nombre
        )
        
        if exito:
            from modelos.ProcesoOcurrente import EventoRed
            ultimo_evento = session.query(EventoRed).filter_by(orden_id=orden_id).order_by(EventoRed.timestamp.desc()).first()
            mensaje = "Control de calidad procesado."
            es_aprobado = True
            if ultimo_evento:
                mensaje = ultimo_evento.transicion_nombre
                if "Rechazado" in mensaje:
                    es_aprobado = False
                    
            session.commit()
            session.close()
            return jsonify({
                'success': True, 
                'aprobado': es_aprobado, 
                'mensaje': f'Resultado de Calidad: {mensaje}'
            })
        else:
            session.close()
            return jsonify({'success': False, 'error': 'No se pudo procesar el control de calidad. Verifique el estado de la orden.'})
            
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
    """Crea una nueva orden de producción usando el Planificador y la pone en estado pendiente"""
    data = request.get_json()
    
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad', 0)
    plazo_entrega = data.get('plazo_entrega')
    
    if not producto_id or not cantidad:
        return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
    from flask import current_app
    Session = current_app.config['SESSION_MAKER']
    session = Session()
    
    try:
        from servicios.planificador import PlanificadorProduccion
        from modelos.Producto import Producto
        
        producto = session.query(Producto).get(producto_id)
        if not producto:
            session.close()
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
            
        # 1. Ejecutar el Planificador para encontrar el HolonRuta óptimo y componer la red
        planificador = PlanificadorProduccion(session)
        plan = planificador.seleccionar_recursos_para_orden(producto_id, cantidad, prioridad=1)
        
        if not plan:
            session.close()
            return jsonify({'success': False, 'error': 'No hay ninguna ruta o recursos disponibles para producir esta cantidad.'}), 400
            
        # 2. Generar número de orden único
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        numero_orden = f"ORD-{timestamp_str}"
        
        # 3. Crear Orden en BD en estado 'pendiente'
        orden = OrdenProduccion(
            numero_orden=numero_orden,
            producto_id=producto_id,
            cantidad=cantidad,
            plazo_entrega=datetime.fromisoformat(plazo_entrega) if plazo_entrega else datetime.now(),
            estado='pendiente',  # Dejar en pendiente para que main.py la inicialice
            holon_ruta_id=plan['holon_ruta_id'],
            asignacion_recursos=plan['asignacion']
        )
        session.add(orden)
        session.commit()
        
        orden_id = orden.id
        session.close()
        
        print(f"✅ Orden {numero_orden} (ID: {orden_id}) creada en estado pendiente a través del Planificador.")
        
        return jsonify({
            'success': True,
            'orden_id': orden_id,
            'numero_orden': numero_orden,
            'mensaje': f'Orden {numero_orden} planificada con éxito. Costo ABC estimado: ${plan["costo_total"]:.2f}. Iniciando orquestación...'
        })
        
    except Exception as e:
        session.rollback()
        session.close()
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