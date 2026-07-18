from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'Profesor':
            return redirect(url_for('profesor.panel'))
        return redirect(url_for('estudiante.panel'))
    return render_template('index.html')
