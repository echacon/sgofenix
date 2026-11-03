# web/routes/planificador.py
"""
Rutas del Planificador y Cotizador Holónico Basado en Actividades (ABC).
Expone en la interfaz web el Algoritmo 1 del artículo IEEE TII:
- Poda en Dos Etapas y Ramificación y Acotación (Branch-and-Bound) con cota inferior admisible LB(nu).
- Retropropagación exacta de mermas (Proposición 1, Ec. 9): m_0 = q_n / prod(gamma_k).
- Verificación de factibilidad temporal contra las agendas Psi_R de los recursos y fecha límite d.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from .auth import login_required
from servicios.planificador import PlanificadorProduccion
from modelos.Producto import Producto
from modelos.Recursos import Recurso
from modelos.DocumentosNegocio import OrdenProduccion

planificador_bp = Blueprint('planificador', __name__)


def _enriquecer_resultado_plan(resultado: dict) -> dict:
    """Normaliza alias de claves de masa inicial/final y por etapa para la interfaz web."""
    if not resultado:
        return resultado
    resultado.setdefault("masa_inicial_kg", resultado.get("masa_inicial", 0.0))
    resultado.setdefault("masa_final_kg", resultado.get("masa_salida", 0.0))
    m_prev = float(resultado.get("masa_inicial_kg", 0.0))
    for _etapa_nom, info in (resultado.get("asignacion") or {}).items():
        m_out = float(info.get("masa_acumulada_etapa", m_prev))
        info.setdefault("masa_entrada_kg", m_prev)
        info.setdefault("masa_salida_kg", m_out)
        m_prev = m_out
    return resultado


def _reservar_agenda_en_bd(session, resultado: dict, orden_id: int) -> None:
    """Registra los intervalos [EST_k, EFT_k] comprometidos en la agenda Psi_R (Ec. 3) de cada recurso."""
    for etapa_nom, info in (resultado.get("asignacion") or {}).items():
        rec_id = info.get("recurso_id")
        if not rec_id:
            continue
        recurso = session.query(Recurso).get(int(rec_id))
        if not recurso:
            continue
        agenda_actual = list(recurso.agenda) if isinstance(recurso.agenda, list) else []
        agenda_actual.append({
            "orden_id": orden_id,
            "etapa": etapa_nom,
            "inicio_min": float(info.get("est_min", 0.0)),
            "fin_min": float(info.get("eft_min", info.get("duracion_min", 0.0)))
        })
        recurso.agenda = agenda_actual
    session.flush()


@planificador_bp.route('/planificador')
@login_required
def vista_planificador():
    """Vista principal del Cotizador y Planificador Holónico ABC."""
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
    Ejecuta el Algoritmo 1 de Planificación Holónica (IEEE TII):
    Composición selectiva, poda por factibilidad física/temporal (d) y económica (V_target),
    retropropagación de mermas (Ec. 9) y costeo dinámico ABC con factor EDR.
    """
    data = request.get_json() or {}
    producto_id = data.get('producto_id')
    cantidad = float(data.get('cantidad', 0.0))
    prioridad = int(data.get('prioridad', 1))
    v_target = float(data['v_target']) if data.get('v_target') not in (None, '') else None
    deadline_min = float(data['deadline_min']) if data.get('deadline_min') not in (None, '') else None
    retropropagar_merma = bool(data.get('retropropagar_merma', True))

    if not producto_id or cantidad <= 0:
        return jsonify({
            'success': False,
            'error': 'Parámetros inválidos. Indique producto y cantidad mayor a cero.'
        }), 400

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        planificador = PlanificadorProduccion(session)
        resultado = planificador.seleccionar_recursos_para_orden(
            producto_id=int(producto_id),
            cantidad=cantidad,
            prioridad=prioridad,
            v_target=v_target,
            deadline_min=deadline_min,
            retropropagar_merma=retropropagar_merma
        )

        if not resultado:
            return jsonify({
                'success': False,
                'error': (
                    'No se encontró ninguna ruta viable para los parámetros indicados '
                    '(posible poda por cota económica V_target, plazo límite d, rango de lote o conectividad física K).'
                )
            }), 404

        _enriquecer_resultado_plan(resultado)
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
    """
    Crea una Orden de Producción persistiendo la asignación óptima de recursos
    y reservando los intervalos [EST_k, EFT_k] en la agenda Psi_R de cada Holón Recurso.
    """
    data = request.get_json() or {}
    producto_id = data.get('producto_id')
    cantidad = float(data.get('cantidad', 0.0))
    prioridad = int(data.get('prioridad', 1))
    v_target = float(data['v_target']) if data.get('v_target') not in (None, '') else None
    deadline_min = float(data['deadline_min']) if data.get('deadline_min') not in (None, '') else None
    retropropagar_merma = bool(data.get('retropropagar_merma', True))
    plazo_entrega_str = data.get('plazo_entrega')

    if not producto_id or cantidad <= 0:
        return jsonify({'success': False, 'error': 'Faltan parámetros requeridos'}), 400

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        planificador = PlanificadorProduccion(session)
        resultado = planificador.seleccionar_recursos_para_orden(
            producto_id=int(producto_id),
            cantidad=cantidad,
            prioridad=prioridad,
            v_target=v_target,
            deadline_min=deadline_min,
            retropropagar_merma=retropropagar_merma
        )

        if not resultado:
            return jsonify({'success': False, 'error': 'No hay ruta viable para generar la orden.'}), 400

        _enriquecer_resultado_plan(resultado)

        asignacion_orden = {}
        for etapa_nom, info in resultado['asignacion'].items():
            asignacion_orden[etapa_nom] = {
                'recurso_id': info['recurso_id'],
                'recurso_nombre': info['recurso_nombre'],
                'est_min': info.get('est_min', 0.0),
                'eft_min': info.get('eft_min', info.get('duracion_min', 0.0))
            }

        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        numero_orden = f"ORD-{timestamp_str}"
        plazo = datetime.fromisoformat(plazo_entrega_str) if plazo_entrega_str else datetime.now()

        cantidad_orden = float(resultado.get('masa_inicial_kg', cantidad))

        nueva_orden = OrdenProduccion(
            numero_orden=numero_orden,
            producto_id=int(producto_id),
            cantidad=cantidad_orden,
            prioridad=prioridad,
            plazo_entrega=plazo,
            estado='pendiente',
            holon_ruta_id=resultado['holon_ruta_id'],
            asignacion_recursos=asignacion_orden
        )
        session.add(nueva_orden)
        session.flush()

        # Comprometer intervalos en la agenda dinámica Psi_R de cada Holón Recurso
        _reservar_agenda_en_bd(session, resultado, orden_id=nueva_orden.id)
        session.commit()

        orden_id = nueva_orden.id
        return jsonify({
            'success': True,
            'orden_id': orden_id,
            'numero_orden': numero_orden,
            'masa_inicial_kg': resultado.get('masa_inicial_kg', cantidad),
            'masa_final_kg': resultado.get('masa_final_kg', cantidad),
            'costo_total': resultado['costo_total'],
            'costo_unitario': resultado['costo_unitario'],
            'duracion_total_min': resultado['duracion_total_min'],
            'mensaje': f'Orden {numero_orden} planificada bajo ruta {resultado["holon_ruta_nombre"]} y reservada en agenda Psi_R.'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
