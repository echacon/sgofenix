# web/routes/mes.py
"""
Módulo de Visualización Ejecutiva MES e Ingesta Unificada de Planta (Modos A, B y C).

Propósito en la Arquitectura PPR Holónica / AB-TPPN (IEEE TII):
---------------------------------------------------------------
1. Centro de Control Ejecutivo MES (`/mes` y `/mes/api/resumen`):
   Consolida en tiempo real:
   - La Ruta de Carga Canónica en 6 pasos (progreso estructural de la planta).
   - El estado de los Holones de Recurso (RH, Ec. 3): disponibilidad, reservas en agenda Psi_R,
     vector de tasas horarias ABC Phi_R = [kappa_eff, omega, delta, mu]^T, factor de rendimiento
     másico gamma_R, relación de desviación energética EDR(R) (Ec. 15) y modalidad de captura (A/B/C).
   - La ejecución concurrente de Redes de Petri (N_E de Ejecución Física y N_S de Seguimiento/ERP)
     junto con la evolución en vivo del Token Coloreado tau = (o, m, c_acc, t) y el costo unitario
     instantáneo u = c_acc / m (Ec. 4 - Ec. 8).

2. Pasarela Unificada de Ingesta de Eventos (`/api/ingesta/evento_planta`):
   Desacopla la semántica formal del Orquestador AB-TPPN respecto al nivel tecnológico de piso de planta,
   permitiendo que coexistan en una misma PyME y dentro de una misma Orden de Producción:
   - Modo A (`A_OPERADOR`): Sin tecnología avanzada de piso (Human-in-the-Loop vía Tablet/Web).
   - Modo B (`B_SCADA`): Tecnología media con captura automática desde un SCADA/PLC existente.
   - Modo C (`C_EDGE`): Tecnología de borde de bajo coste (Arduino/ESP32 + sensores SCT-013/PZEM-004T
     y DS18B20 + Raspberry Pi).
"""

import json
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, current_app
from .auth import login_required
from .operador import recargar_instancias_desde_bd
from modelos.Taxonomia import FamiliaProducto, TipoDeOperacion, PatronDeRuta
from modelos.RedPetri import RedPetri, DuracionEstimadaLugar
from modelos.Encadenamiento import ConfiguracionEncadenamiento
from modelos.Recursos import (
    Recurso, RecursoEquipo, RecursoPersonal,
    UnidadFuncional, ConexionFisica, ServicioTecnicoOfrecido
)
from modelos.Producto import Producto, HolonRuta, Formula, AsignacionRecurso
from modelos.DocumentosNegocio import OrdenProduccion
from modelos.ProcesoOcurrente import InstanciaRed, EventoRed
from validadores.validador_integral import ValidadorIntegralPlanta

mes_bp = Blueprint('mes', __name__)


def _inferir_modo_captura_recurso(recurso: Recurso) -> dict:
    """
    Determina la modalidad tecnológica de captura de datos del Holón Recurso (A, B o C)
    a partir de su configuración física y telemetría energética.
    """
    if recurso.tipo == 'personal':
        return {
            'codigo': 'A_OPERADOR',
            'etiqueta': 'Modo A · Operador (Tablet)',
            'badge': 'primary',
            'icono': 'bi-person-workspace'
        }

    eq = recurso.equipo
    desc = (recurso.descripcion or '').lower()
    modelo = (eq.modelo or '').lower() if eq else ''

    # Si cuenta con medidor de energía holónico de bajo coste o referencia explícita a Edge/Arduino
    if eq and eq.medidor_energia:
        if 'scada' in desc or 'plc' in desc or 'scada' in modelo:
            return {
                'codigo': 'B_SCADA',
                'etiqueta': 'Modo B · SCADA / PLC',
                'badge': 'info',
                'icono': 'bi-hdd-network'
            }
        return {
            'codigo': 'C_EDGE',
            'etiqueta': 'Modo C · Edge IIoT (Arduino/RPi)',
            'badge': 'success',
            'icono': 'bi-cpu'
        }

    if 'scada' in desc or 'plc' in desc or 'scada' in modelo or (eq and (eq.consumo_energia_kw or 0) >= 12.0):
        return {
            'codigo': 'B_SCADA',
            'etiqueta': 'Modo B · SCADA / PLC',
            'badge': 'info',
            'icono': 'bi-hdd-network'
        }

    return {
        'codigo': 'A_OPERADOR',
        'etiqueta': 'Modo A · Operador (Human-in-the-Loop)',
        'badge': 'secondary',
        'icono': 'bi-hand-index-thumb'
    }


@mes_bp.route('/mes')
@login_required
def centro_control():
    """Renderiza el Centro de Control Ejecutivo MES y Simulador Híbrido A/B/C."""
    return render_template('mes/centro_control.html')


@mes_bp.route('/mes/api/resumen')
@login_required
def api_resumen_mes():
    """
    Retorna el estado integral del sistema MOM/MES en tiempo real:
    1. Progreso de la Ruta de Carga Canónica en 6 pasos.
    2. Estado operativo, energético (EDR) y tasas ABC de todos los Holones de Recurso.
    3. Órdenes activas/recientes con marcado vivo de Redes de Petri (N_E y N_S) y Token Coloreado.
    4. Bitácora reciente de eventos de planta con trazabilidad del modo de captura (A/B/C).
    """
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()
    try:
        recargar_instancias_desde_bd()
        orquestador = current_app.config.get('ORQUESTADOR')
        recursos_en_uso = dict(getattr(orquestador, 'recursos_en_uso', {}) or {})
        for inst_act in session.query(InstanciaRed).filter_by(activa=True, completada=False).all():
            oc = inst_act.recursos_ocupados or {}
            for rec_nom in (oc.get('recursos', []) if isinstance(oc, dict) else []):
                recursos_en_uso[str(rec_nom)] = inst_act.orden_id

        # 1. Progreso de la Ruta de Carga en 6 Pasos
        n_unidades = session.query(UnidadFuncional).count()
        n_familias = session.query(FamiliaProducto).count()
        n_operaciones = session.query(TipoDeOperacion).count()
        n_patrones = session.query(PatronDeRuta).count()
        n_redes = session.query(RedPetri).count()
        n_encad = session.query(ConfiguracionEncadenamiento).count()
        n_recursos = session.query(Recurso).count()
        n_conexiones = session.query(ConexionFisica).count()
        n_servicios = session.query(ServicioTecnicoOfrecido).count()
        n_productos = session.query(Producto).filter_by(es_fabricado=True).count()
        n_insumos = session.query(Producto).filter_by(es_insumo=True).count()
        n_rutas = session.query(HolonRuta).count()
        n_formulas = session.query(Formula).count()
        n_duraciones = session.query(DuracionEstimadaLugar).count()

        validador = ValidadorIntegralPlanta()
        validador.cargar_desde_bd(session)
        reporte_val = validador.ejecutar_diagnostico_completo()

        ruta_carga = [
            {
                'paso': 1,
                'titulo': 'Jerarquía Física (Unidades Funcionales)',
                'completado': n_unidades > 0,
                'detalle': f'{n_unidades} unidades funcionales registradas',
                'archivo_ref': 'recursos.yaml (unidades_funcionales)'
            },
            {
                'paso': 2,
                'titulo': 'Taxonomía Industrial (Familias y Operaciones)',
                'completado': n_familias > 0 and n_operaciones > 0,
                'detalle': f'{n_familias} familias · {n_operaciones} tipos de operación',
                'archivo_ref': 'taxonomia.yaml'
            },
            {
                'paso': 3,
                'titulo': 'Patrones de Ruta, Redes AB-TPPN y Encadenamiento',
                'completado': n_patrones > 0 and n_redes > 0,
                'detalle': f'{n_patrones} patrones · {n_redes} redes PNML · {n_encad} reglas de encadenamiento',
                'archivo_ref': 'patrones.yaml + *.pnml + encadenamiento'
            },
            {
                'paso': 4,
                'titulo': 'Holones de Recurso (ABC / EDR) y Grafo Físico K',
                'completado': n_recursos > 0 and n_servicios > 0,
                'detalle': f'{n_recursos} recursos · {n_servicios} servicios · {n_conexiones} enlaces físicos',
                'archivo_ref': 'recursos.yaml + conexiones'
            },
            {
                'paso': 5,
                'titulo': 'Holones de Producto, Rutas, BOM y Cinemática',
                'completado': n_productos > 0 and n_rutas > 0 and n_formulas > 0,
                'detalle': f'{n_productos} productos · {n_insumos} insumos · {n_rutas} rutas · {n_duraciones} duraciones',
                'archivo_ref': 'productos.yaml + duraciones_lugares.yaml'
            },
            {
                'paso': 6,
                'titulo': 'Semáforo Pre-Producción (Validador Integral)',
                'completado': reporte_val.estado_semaforo in ('VERDE', 'AMARILLO'),
                'semaforo': reporte_val.estado_semaforo,
                'detalle': f'Semáforo {reporte_val.estado_semaforo} ({reporte_val.total_errores} err / {reporte_val.total_advertencias} adv)',
                'archivo_ref': '/cargas/validar'
            }
        ]

        # 2. Holones de Recurso (Supply Side)
        costo_personal_default = 15.0
        personales = session.query(RecursoPersonal).filter_by(disponible=True).all()
        if personales:
            costo_personal_default = sum(p.costo_por_hora for p in personales) / len(personales)

        recursos_list = []
        for r in session.query(Recurso).all():
            modo = _inferir_modo_captura_recurso(r)
            ocupado_por = recursos_en_uso.get(r.nombre)
            if r.tipo == 'equipo' and r.equipo:
                eq = r.equipo
                edr = float(eq.edr_actual if eq.edr_actual is not None else 1.0)
                kappa_base = float((eq.consumo_energia_kw or 0.0) * (eq.costo_energia_por_kwh or 0.0))
                kappa_eff = kappa_base * edr
                omega = float(costo_personal_default)
                delta = float(eq.costo_depreciacion_hora or 0.0)
                mu = float(eq.costo_overhead_hora if eq.costo_overhead_hora is not None else 12.0)
                tasa_total_h = kappa_eff + omega + delta + mu
                gamma = float(eq.rendimiento_nominal if eq.rendimiento_nominal is not None else 0.98)

                if edr <= 1.10:
                    salud_energetica = 'OPTIMO'
                elif edr <= 1.20:
                    salud_energetica = 'ADVERTENCIA'
                else:
                    salud_energetica = 'DEGRADADO'

                recursos_list.append({
                    'id': r.id,
                    'codigo': r.codigo,
                    'nombre': r.nombre,
                    'tipo': r.tipo,
                    'modelo': eq.modelo or 'Estándar',
                    'disponible': bool(eq.disponible),
                    'ocupado_por_orden': ocupado_por,
                    'estado_operativo': f'OCUPADO (Ord #{ocupado_por})' if ocupado_por else ('DISPONIBLE' if eq.disponible else 'FUERA DE SERVICIO'),
                    'modo_captura': modo,
                    'medidor_energia': bool(eq.medidor_energia),
                    'edr_actual': round(edr, 3),
                    'salud_energetica': salud_energetica,
                    'gamma': round(gamma, 4),
                    'kappa_eff_h': round(kappa_eff, 2),
                    'omega_h': round(omega, 2),
                    'delta_h': round(delta, 2),
                    'mu_h': round(mu, 2),
                    'tasa_total_abc_h': round(tasa_total_h, 2),
                    'agenda': r.agenda or []
                })
            elif r.tipo == 'personal' and r.personal:
                per = r.personal
                recursos_list.append({
                    'id': r.id,
                    'codigo': r.codigo,
                    'nombre': r.nombre,
                    'tipo': r.tipo,
                    'modelo': per.especialidad or 'Operador',
                    'disponible': bool(per.disponible),
                    'ocupado_por_orden': ocupado_por,
                    'estado_operativo': 'DISPONIBLE' if per.disponible else 'NO DISPONIBLE',
                    'modo_captura': modo,
                    'medidor_energia': False,
                    'edr_actual': 1.0,
                    'salud_energetica': 'N/A',
                    'gamma': 1.0,
                    'kappa_eff_h': 0.0,
                    'omega_h': round(float(per.costo_por_hora or 0.0), 2),
                    'delta_h': 0.0,
                    'mu_h': 0.0,
                    'tasa_total_abc_h': round(float(per.costo_por_hora or 0.0), 2),
                    'agenda': r.agenda or []
                })

        # 3. Órdenes de Producción e Instancias de Red (N_E y N_S)
        ordenes_bd = session.query(OrdenProduccion).order_by(OrdenProduccion.id.desc()).limit(15).all()
        ordenes_list = []

        for ord_obj in ordenes_bd:
            instancias_info = []
            token_m_actual = float(ord_obj.cantidad or 0.0)
            token_c_actual = 0.0

            for inst in ord_obj.instancias:
                marcado = inst.marcado if isinstance(inst.marcado, dict) else (
                    json.loads(inst.marcado) if inst.marcado else {}
                )
                # Identificar lugares con tokens > 0
                lugares_activos = [k for k, v in marcado.items() if v and int(v) > 0]

                # Resolver nombres legibles de lugares desde RedPetri si está cargada
                red_bd = session.query(RedPetri).filter_by(nombre=inst.tipo).first()
                lugares_legibles = []
                if red_bd and isinstance(red_bd.lugares, dict):
                    for lid in lugares_activos:
                        l_info = red_bd.lugares.get(lid, {})
                        l_nom = l_info.get('nombre', lid) if isinstance(l_info, dict) else str(l_info)
                        lugares_legibles.append({'id': lid, 'nombre': l_nom})
                else:
                    lugares_legibles = [{'id': lid, 'nombre': lid} for lid in lugares_activos]

                if inst.token_m is not None and inst.token_m > 0:
                    token_m_actual = float(inst.token_m)
                if inst.token_c is not None and inst.token_c >= token_c_actual:
                    token_c_actual = float(inst.token_c)

                instancias_info.append({
                    'id': inst.id,
                    'red_nombre': inst.tipo,
                    'rol_red': 'N_S · Red de Seguimiento / ERP' if 'seguimiento' in (inst.tipo or '').lower() else 'N_E · Red de Ejecución Física',
                    'activa': bool(inst.activa),
                    'completada': bool(inst.completada),
                    'tipo_terminacion': inst.tipo_terminacion,
                    'lugares_activos': lugares_legibles,
                    'token_m': round(float(inst.token_m or 0.0), 3),
                    'token_c': round(float(inst.token_c or 0.0), 2)
                })

            costo_unitario = (token_c_actual / token_m_actual) if token_m_actual > 0 else 0.0

            ordenes_list.append({
                'id': ord_obj.id,
                'numero_orden': ord_obj.numero_orden,
                'producto_nombre': ord_obj.producto.nombre if ord_obj.producto else f'Prod #{ord_obj.producto_id}',
                'producto_codigo': ord_obj.producto.codigo if ord_obj.producto else '',
                'cantidad_solicitada': round(float(ord_obj.cantidad or 0.0), 2),
                'estado': ord_obj.estado,
                'prioridad': ord_obj.prioridad,
                'asignacion_recursos': ord_obj.asignacion_recursos or {},
                'token': {
                    'o': ord_obj.numero_orden,
                    'm': round(token_m_actual, 3),
                    'c_acc': round(token_c_actual, 2),
                    'u': round(costo_unitario, 4)
                },
                'instancias': instancias_info
            })

        # 4. Eventos Recientes de Planta (con trazabilidad A/B/C)
        eventos_bd = session.query(EventoRed).order_by(EventoRed.id.desc()).limit(20).all()
        eventos_list = []
        for ev in eventos_bd:
            inv = ev.invariantes if isinstance(ev.invariantes, dict) else (
                json.loads(ev.invariantes) if ev.invariantes else {}
            )
            med_ev = inv.get('mediciones', {}) if isinstance(inv.get('mediciones'), dict) else {}
            modo_ev = med_ev.get('modo_captura') or inv.get('modo_captura') or (
                'AUTO_SYNC' if inv.get('tipo') in ('auto', 'mensaje') else 'A_OPERADOR'
            )
            eventos_list.append({
                'id': ev.id,
                'orden_id': ev.orden_id,
                'instancia_id': ev.instancia_id,
                'transicion': ev.transicion_nombre,
                'timestamp': ev.timestamp.strftime('%H:%M:%S') if ev.timestamp else '',
                'modo_captura': modo_ev,
                'token_m': round(float(ev.token_m or 0.0), 2),
                'token_c': round(float(ev.token_c or 0.0), 2),
                'costo_paso': round(float(ev.costo_real_paso or 0.0), 2),
                'mediciones': med_ev if med_ev else inv
            })

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'ruta_carga': ruta_carga,
            'semaforo_global': reporte_val.estado_semaforo,
            'recursos': recursos_list,
            'ordenes': ordenes_list,
            'eventos_recientes': eventos_list
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@mes_bp.route('/mes/api/orden/<int:orden_id>/iniciar', methods=['POST'])
def api_iniciar_orden_mes(orden_id: int):
    """
    Inicializa en el Orquestador AB-TPPN una Orden de Producción que se encuentre en estado
    'pendiente' o 'planificada', instanciando sus Redes de Petri (N_E y N_S) y su Token Coloreado.
    """
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()
    orquestador = current_app.config['ORQUESTADOR']
    try:
        orquestador.session = session
        orquestador.motor.db_session = session
        exito = orquestador.inicializar_orden(orden_id)
        if not exito:
            return jsonify({'success': False, 'error': f'No fue posible iniciar la orden #{orden_id}'}), 400
        orquestador.estabilizar_red(orden_id)
        session.commit()
        recargar_instancias_desde_bd()
        return jsonify({
            'success': True,
            'orden_id': orden_id,
            'mensaje': f'Orden #{orden_id} iniciada y redes AB-TPPN estabilizadas.'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@mes_bp.route('/api/ingesta/evento_planta', methods=['POST'])
def api_ingesta_evento_planta():
    """
    Pasarela Unificada de Ingesta de Eventos y Telemetría de Piso de Planta (Modos A, B y C).

    Payload JSON esperado:
    {
        "orden_id": 1,
        "recurso": "Tanque de Mezcla 1",       # Opcional
        "red": "red_ejecucion_orden",          # Opcional
        "evento": "201",                       # Código o nombre de transición (ej. "201", "t_fin_mezcla")
        "modo_captura": "A_OPERADOR" | "B_SCADA" | "C_EDGE",
        "mediciones": {
            "kwh_consumidos": 14.8,            # Opcional (Telemetría energética Modo B/C)
            "temperatura_c": 65.2,             # Opcional (Verificación de invariantes físicos)
            "merma_kg": 1.2                    # Opcional (Absorción de mermas medida)
        },
        "forzar": false                        # Override de supervisor ante violación de invariantes
    }
    """
    data = request.get_json() or {}
    orden_id = data.get('orden_id')
    evento_nombre = data.get('evento') or data.get('transicion')
    recurso_nombre = data.get('recurso')
    red_nombre = data.get('red')
    modo_captura = data.get('modo_captura', 'A_OPERADOR')
    mediciones = dict(data.get('mediciones') or {})
    forzar = bool(data.get('forzar', False))

    if not orden_id or not evento_nombre:
        return jsonify({
            'success': False,
            'error': 'Parámetros incompletos: se requieren "orden_id" y "evento".'
        }), 400

    # Registrar explícitamente la fuente tecnológica en el diccionario de mediciones/invariantes
    mediciones['modo_captura'] = modo_captura
    mediciones['timestamp_ingesta'] = datetime.now().isoformat()

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()
    orquestador = current_app.config['ORQUESTADOR']

    try:
        recargar_instancias_desde_bd()
        orquestador.session = session
        orquestador.motor.db_session = session

        # Si la orden aún está en estado 'pendiente', iniciarla automáticamente al recibir el primer pulso
        orden = session.query(OrdenProduccion).get(int(orden_id))
        if not orden:
            return jsonify({'success': False, 'error': f'Orden #{orden_id} no existe.'}), 404

        if orden.estado in ('pendiente', 'planificada'):
            orden.estado = 'pendiente'
            session.flush()
            orquestador.inicializar_orden(int(orden_id))
            orquestador.estabilizar_red(int(orden_id))

        try:
            exito = orquestador.procesar_evento_planta(
                orden_id=int(orden_id),
                evento_nombre=str(evento_nombre),
                recurso_nombre=recurso_nombre,
                red_nombre=red_nombre,
                timestamp=datetime.now(),
                mediciones=mediciones,
                forzar=forzar
            )
        except ValueError as ve:
            session.rollback()
            return jsonify({
                'success': False,
                'bloqueo_invariante': True,
                'modo_captura': modo_captura,
                'error': str(ve),
                'mensaje': f'Bloqueo por Invariante Físico ({modo_captura}): {str(ve)}'
            }), 422

        if not exito:
            session.rollback()
            return jsonify({
                'success': False,
                'modo_captura': modo_captura,
                'error': f'La transición/evento "{evento_nombre}" no está habilitada en el marcado actual de la Orden #{orden_id}.'
            }), 409

        # Propagar transiciones automáticas encadenadas (serie 100 / sincronización N_E <-> N_S)
        orquestador.estabilizar_red(int(orden_id))
        orquestador._verificar_y_finalizar_orden(int(orden_id))
        session.commit()

        # Consultar el estado resultante del Token Coloreado y las instancias
        orden_refrescada = session.query(OrdenProduccion).get(int(orden_id))
        token_m = float(orden_refrescada.cantidad or 0.0)
        token_c = 0.0
        instancias_resumen = []

        for inst in orden_refrescada.instancias:
            marcado = inst.marcado if isinstance(inst.marcado, dict) else (
                json.loads(inst.marcado) if inst.marcado else {}
            )
            if inst.token_m is not None and inst.token_m > 0:
                token_m = float(inst.token_m)
            if inst.token_c is not None and inst.token_c >= token_c:
                token_c = float(inst.token_c)
            instancias_resumen.append({
                'instancia_id': inst.id,
                'red': inst.tipo,
                'activa': inst.activa,
                'completada': inst.completada,
                'marcado': marcado,
                'token_m': round(float(inst.token_m or 0.0), 3),
                'token_c': round(float(inst.token_c or 0.0), 2)
            })

        costo_unitario = (token_c / token_m) if token_m > 0 else 0.0

        return jsonify({
            'success': True,
            'modo_captura': modo_captura,
            'orden_id': int(orden_id),
            'estado_orden': orden_refrescada.estado,
            'evento_procesado': str(evento_nombre),
            'recurso': recurso_nombre,
            'token': {
                'm': round(token_m, 3),
                'c_acc': round(token_c, 2),
                'u': round(costo_unitario, 4)
            },
            'instancias': instancias_resumen,
            'mensaje': f'Evento "{evento_nombre}" procesado vía {modo_captura} con éxito.'
        })
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
