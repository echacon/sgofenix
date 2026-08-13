# routes/carga_recursos.py

from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from validadores.validador_recursos import ValidadorRecursosExcel
from importadores.importador_recursos import ImportadorRecursosExcel
from modelos.declarative_base import SessionLocal
import os

carga_recursos_bp = Blueprint('carga_recursos', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@carga_recursos_bp.route('/cargar/recursos', methods=['GET', 'POST'])
def cargar_recursos():
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            flash('Archivo vacío', 'error')
            return redirect(request.url)
        
        if not allowed_file(archivo.filename):
            flash('Formato no permitido. Use .xlsx o .xls', 'error')
            return redirect(request.url)
        
        filename = secure_filename(archivo.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        archivo.save(path)
        
        # Validar
        validador = ValidadorRecursosExcel()
        es_valido, errores, advertencias = validador.validar(path)
        
        if not es_valido:
            return render_template('carga_errores.html',
                                 errores=errores,
                                 advertencias=advertencias,
                                 tipo='Recursos Organizacionales')
        
        # Importar
        session = SessionLocal()
        importador = ImportadorRecursosExcel(session)
        exito, stats = importador.importar(validador.datos_validados)
        session.close()
        
        if exito:
            flash(f'✅ Carga exitosa: {stats}', 'success')
            return redirect(url_for('index'))
        else:
            return render_template('carga_errores.html',
                                 errores=stats['errores'],
                                 advertencias=[],
                                 tipo='Recursos Organizacionales (importación)')
    
    return render_template('carga_recursos.html')