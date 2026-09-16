# web/routes/cargas_validadas.py
import os
import shutil
import tempfile
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, current_app
from .auth import login_required
from validadores.validador_integral import ValidadorIntegralPlanta

cargas_validadas_bp = Blueprint('cargas_validadas', __name__)

@cargas_validadas_bp.route('/cargas/validar')
@login_required
def vista_semaforo():
    """Vista del Semáforo Pre-Producción y Diagnóstico de Planta"""
    return render_template('cargas/semaforo_diagnostico.html')


@cargas_validadas_bp.route('/cargas/api/diagnostico_actual')
@login_required
def api_diagnostico_actual():
    """Ejecuta el diagnóstico integral sobre la base de datos viva (fenix.db)"""
    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()
    
    try:
        validador = ValidadorIntegralPlanta()
        validador.cargar_desde_bd(session)
        reporte = validador.ejecutar_diagnostico_completo()
        
        items_json = [{
            'nivel': item.nivel,
            'categoria': item.categoria,
            'mensaje': item.mensaje,
            'detalles': item.detalles
        } for item in reporte.items]
        
        return jsonify({
            'success': True,
            'semaforo': reporte.estado_semaforo,
            'total_errores': reporte.total_errores,
            'total_advertencias': reporte.total_advertencias,
            'total_info': reporte.total_info,
            'resumen_recursos': reporte.resumen_recursos,
            'resumen_productos': reporte.resumen_productos,
            'items': items_json
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@cargas_validadas_bp.route('/cargas/api/validar_paquete_yaml', methods=['POST'])
@login_required
def api_validar_paquete_yaml():
    """Valida un conjunto de archivos YAML subidos sin persistir en BD"""
    archivos = request.files.getlist('archivos')
    if not archivos or len(archivos) == 0:
        return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400

    temp_dir = tempfile.mkdtemp(prefix='fenix_val_')
    try:
        for f in archivos:
            if f.filename:
                dest = Path(temp_dir) / f.filename
                f.save(str(dest))

        validador = ValidadorIntegralPlanta()
        validador.cargar_desde_yaml(Path(temp_dir))
        reporte = validador.ejecutar_diagnostico_completo()

        items_json = [{
            'nivel': item.nivel,
            'categoria': item.categoria,
            'mensaje': item.mensaje,
            'detalles': item.detalles
        } for item in reporte.items]

        return jsonify({
            'success': True,
            'semaforo': reporte.estado_semaforo,
            'total_errores': reporte.total_errores,
            'total_advertencias': reporte.total_advertencias,
            'total_info': reporte.total_info,
            'items': items_json,
            'temp_dir': temp_dir
        })
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@cargas_validadas_bp.route('/cargas/api/aplicar_paquete_yaml', methods=['POST'])
@login_required
def api_aplicar_paquete_yaml():
    """Persiste en BD los archivos YAML previamente validados con Semáforo VERDE o AMARILLO"""
    data = request.get_json() or {}
    temp_dir = data.get('temp_dir')
    forzar = data.get('forzar', False)

    if not temp_dir or not Path(temp_dir).exists():
        return jsonify({'success': False, 'error': 'Directorio temporal expirado o no encontrado'}), 400

    SessionLocal = current_app.config['SESSION_MAKER']
    session = SessionLocal()

    try:
        # Re-validar antes de escribir
        validador = ValidadorIntegralPlanta()
        validador.cargar_desde_yaml(Path(temp_dir))
        reporte = validador.ejecutar_diagnostico_completo()

        if reporte.estado_semaforo == 'ROJO':
            return jsonify({'success': False, 'error': 'Bloqueo: No se puede aplicar una configuración con Semáforo ROJO.'}), 400

        if reporte.estado_semaforo == 'AMARILLO' and not forzar:
            return jsonify({'success': False, 'error': 'Advertencia: Requiere confirmación para aplicar con Semáforo AMARILLO.'}), 400

        # Importar a base de datos usando importadores
        from importadores.cargador_yaml import CargadorYAML
        cargador = CargadorYAML(session)
        exito = cargador.cargar_directorio(Path(temp_dir))
        
        if exito:
            session.commit()
            return jsonify({'success': True, 'mensaje': 'Configuración de planta aplicada y persistida exitosamente en base de datos.'})
        else:
            session.rollback()
            return jsonify({'success': False, 'error': 'Fallo durante la inserción en base de datos.'}), 500

    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
