# web/routes/aprendizaje.py
from flask import Blueprint, render_template, jsonify, current_app
from .auth import login_required
from modelos.Recursos import Recurso, RecursoEquipo
from modelos.Producto import AsignacionRecurso, HolonRuta
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from modelos.DocumentosNegocio import OrdenProduccion

aprendizaje_bp = Blueprint('aprendizaje', __name__)

@aprendizaje_bp.route('/aprendizaje')
@login_required
def vista_aprendizaje():
    """Panel de Auditoría del Lazo de Aprendizaje Continuo (EWMA y EDR)"""
    return render_template('aprendizaje/panel_calibracion.html')


@aprendizaje_bp.route('/aprendizaje/api/recursos_calibrados')
@login_required
def api_recursos_calibrados():
    """Retorna el estado de auto-calibración de todos los recursos físicos de planta"""
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        recursos = session.query(Recurso).all()
        resultado = []

        for r in recursos:
            eq = r.equipo
            
            # Eficiencias en asignaciones de rutas
            asigs = session.query(AsignacionRecurso).filter_by(recurso_id=r.id).all()
            eficiencia_promedio = 1.0
            if asigs:
                eficiencias = [a.eficiencia_real for a in asigs if a.eficiencia_real is not None]
                if eficiencias:
                    eficiencia_promedio = sum(eficiencias) / len(eficiencias)

            # EDR
            edr_actual = getattr(eq, 'edr_actual', 1.0) if eq else 1.0
            consumo_kw = getattr(eq, 'consumo_energia_kw', 0.0) if eq else 0.0

            resultado.append({
                'id': r.id,
                'codigo': r.codigo or f"REC-{r.id}",
                'nombre': r.nombre,
                'tipo': r.tipo,
                'eficiencia_real': eficiencia_promedio,
                'edr_actual': edr_actual or 1.0,
                'consumo_kw': consumo_kw or 0.0,
                'tiene_telemetria_energia': getattr(eq, 'medidor_energia', False) if eq else False
            })

        return jsonify({'success': True, 'recursos': resultado})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@aprendizaje_bp.route('/aprendizaje/api/historial_calibraciones')
@login_required
def api_historial_calibraciones():
    """Retorna el historial de lotes procesados, indicando estado de calibración o exclusión por tracking error"""
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        ordenes = session.query(OrdenProduccion).order_by(OrdenProduccion.id.desc()).limit(30).all()
        resultado = []

        for o in ordenes:
            instancias = session.query(InstanciaRed).filter_by(orden_id=o.id).all()
            tiene_error_seguimiento = any(i.tipo_terminacion == 'error_seguimiento' for i in instancias)
            
            eventos_count = session.query(EventoRed).filter_by(orden_id=o.id).count()

            resultado.append({
                'orden_id': o.id,
                'numero_orden': o.numero_orden or f"ORD-{o.id}",
                'producto_nombre': o.holon_ruta.producto.nombre if (o.holon_ruta and o.holon_ruta.producto) else "N/A",
                'cantidad': o.cantidad,
                'estado': o.estado,
                'eventos_registrados': eventos_count,
                'tipo_calibracion': 'EXCLUIDO (Tracking Error)' if tiene_error_seguimiento else ('CALIBRADO (EWMA/EDR)' if o.estado == 'completada' else 'EN CURSO')
            })

        return jsonify({'success': True, 'historial': resultado})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
