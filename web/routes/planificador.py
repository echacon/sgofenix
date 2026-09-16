# web/routes/planificador.py
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from .auth import login_required
from servicios.planificador import PlanificadorProduccion
from modelos.Producto import Producto, HolonRuta
from modelos.DocumentosNegocio import OrdenProduccion

planificador_bp = Blueprint('planificador', __name__)

@planificador_bp.route('/planificador')
@login_required
def vista_planificador():
    """Vista principal del Cotizador y Planificador Holónico ABC"""
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()
    try:
        productos = session.query(Producto).filter_by(es_fabricado=True).all()
        productos_json = [{'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre} for p in productos]
        return render_template('planificador/cotizador.html', productos=productos_json)
    finally:
        session.close()


@planificador_bp.route('/planificador/api/cotizar', methods=['POST'])
@login_required
def api_cotizar():
    """
    Ejecuta el algoritmo de Planificación Holónica:
    Composición selectiva, ruteo en grafo (BFS), costeo dinámico ABC y absorción de mermas.
    """
    data = request.get_json() or {}
    producto_id = data.get('producto_id')
    cantidad = float(data.get('cantidad', 0.0))
    prioridad = int(data.get('prioridad', 1))
    v_target = float(data['v_target']) if data.get('v_target') else None

    if not producto_id or cantidad <= 0:
        return jsonify({'success': False, 'error': 'Parámetros inválidos. Indique producto y cantidad mayor a cero.'}), 400

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        planificador = PlanificadorProduccion(session)
        resultado = planificador.seleccionar_recursos_para_orden(
            producto_id=producto_id,
            cantidad=cantidad,
            prioridad=prioridad,
            v_target=v_target
        )

        if not resultado:
            return jsonify({
                'success': False,
                'error': 'No se encontró ninguna ruta viable para los parámetros indicados (posible violación de cota V_target, rango de lote o conectividad rota).'
            }), 404

        return jsonify({
            'success': True,
            'plan': resultado
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@planificador_bp.route('/planificador/api/crear_orden_optimizada', methods=['POST'])
@login_required
def api_crear_orden_optimizada():
    """Crea una Orden de Producción persistiendo la asignación de recursos óptima calculada por el Planificador"""
    data = request.get_json() or {}
    producto_id = data.get('producto_id')
    cantidad = float(data.get('cantidad', 0.0))
    prioridad = int(data.get('prioridad', 1))
    v_target = float(data['v_target']) if data.get('v_target') else None
    plazo_entrega_str = data.get('plazo_entrega')

    if not producto_id or cantidad <= 0:
        return jsonify({'success': False, 'error': 'Faltan parámetros requeridos'}), 400

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        planificador = PlanificadorProduccion(session)
        resultado = planificador.seleccionar_recursos_para_orden(
            producto_id=producto_id,
            cantidad=cantidad,
            prioridad=prioridad,
            v_target=v_target
        )

        if not resultado:
            return jsonify({'success': False, 'error': 'No hay ruta viable para generar la orden.'}), 400

        # Construir mapeo de asignación para la orden
        asignacion_orden = {}
        for etapa_nom, info in resultado['asignacion'].items():
            asignacion_orden[etapa_nom] = {
                'recurso_id': info['recurso_id'],
                'recurso_nombre': info['recurso_nombre']
            }

        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        numero_orden = f"ORD-{timestamp_str}"
        plazo = datetime.fromisoformat(plazo_entrega_str) if plazo_entrega_str else datetime.now()

        nueva_orden = OrdenProduccion(
            numero_orden=numero_orden,
            producto_id=producto_id,
            cantidad=cantidad,
            prioridad=prioridad,
            plazo_entrega=plazo,
            estado='pendiente',
            holon_ruta_id=resultado['holon_ruta_id'],
            asignacion_recursos=asignacion_orden
        )
        session.add(nueva_orden)
        session.commit()

        orden_id = nueva_orden.id
        return jsonify({
            'success': True,
            'orden_id': orden_id,
            'numero_orden': numero_orden,
            'costo_total': resultado['costo_total'],
            'duracion_total_min': resultado['duracion_total_min'],
            'mensaje': f'Orden {numero_orden} planificada con éxito bajo ruta {resultado["holon_ruta_nombre"]}.'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
