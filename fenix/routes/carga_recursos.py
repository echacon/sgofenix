# routes/carga_recursos.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file
from werkzeug.utils import secure_filename
from modelos.declarative_base import SessionLocal
from scripts.cargar_recursos import cargar_recursos as importar_recursos_yaml
import os
import yaml

carga_recursos_bp = Blueprint('carga_recursos', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'yaml', 'yml'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@carga_recursos_bp.route('/cargar/recursos/plantilla')
def descargar_plantilla():
    """Descarga el archivo 04_recursos.yaml como plantilla"""
    path = os.path.join(current_app.root_path, 'ontologia', 'empresa', '04_recursos.yaml')
    if not os.path.exists(path):
        flash('La plantilla de recursos no se encuentra en el servidor.', 'error')
        return redirect(url_for('carga_recursos.cargar_recursos'))
    return send_file(path, as_attachment=True, download_name='recursos.yaml')

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
            flash('Formato no permitido. Use .yaml o .yml', 'error')
            return redirect(request.url)
        
        filename = secure_filename(archivo.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Asegurarse de que el directorio de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        archivo.save(path)
        
        # Validar y cargar YAML
        session = SessionLocal()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                datos = yaml.safe_load(f)
                
            if not datos or 'recursos' not in datos:
                raise ValueError("El archivo YAML debe contener una clave raíz llamada 'recursos'.")
                
            # Importar recursos a la BD
            importar_recursos_yaml(session, datos)
            session.commit()
            flash('✅ Recursos cargados exitosamente desde el archivo YAML', 'success')
            session.close()
            return redirect(url_for('operador.dashboard'))
            
        except Exception as e:
            session.rollback()
            session.close()
            return render_template('carga_errores.html',
                                 errores=[str(e)],
                                 advertencias=[],
                                 tipo='Recursos Organizacionales (YAML)')
    
    return render_template('carga_recursos.html')