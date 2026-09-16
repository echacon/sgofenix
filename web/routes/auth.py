# routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from modelos.declarative_base import SessionLocal
from modelos.Usuario import Usuario
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor inicie sesión', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor inicie sesión', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('usuario_rol') != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('operador.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        db.close()
        
        if usuario and usuario.check_password(password) and usuario.activo:
            session['usuario_id'] = usuario.id
            session['usuario_nombre'] = usuario.nombre
            session['usuario_rol'] = usuario.rol
            
            if usuario.es_admin:
                return redirect(url_for('carga_recursos.cargar_recursos'))
            else:
                return redirect(url_for('operador.dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))