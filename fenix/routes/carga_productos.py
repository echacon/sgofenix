# routes/carga_productos.py

from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os

carga_productos_bp = Blueprint('carga_productos', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@carga_productos_bp.route('/cargar/productos', methods=['GET', 'POST'])
def cargar_productos():
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
        
        # TODO: Validar e importar productos
        flash('⚠️ Importador de productos en desarrollo', 'warning')
        return redirect(url_for('carga_productos.cargar_productos'))
    
    return render_template('carga_productos.html')