import os
from flask import Flask, render_template

from app.config import config_by_name, BASE_DIR
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Crear carpeta instance si no existe
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    # Crear carpeta de uploads si no existe
    os.makedirs(app.config.get('UPLOAD_FOLDER', ''), exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debe iniciar sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # Importar TODOS los modelos para que db.create_all() los registre
    from app.models.models import (
        Usuario, Estudiante, Profesor, Materia,
        Seccion, Inscripcion, Asistencia, Nota, AgendaPersonal, HorarioPersonal, Evaluacion
    )

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # Registrar blueprints
    from app.main.routes      import main_bp
    from app.auth.routes      import auth_bp
    from app.estudiante.routes import estudiante_bp
    from app.profesor.routes   import profesor_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,        url_prefix='/auth')
    app.register_blueprint(estudiante_bp,  url_prefix='/estudiante')
    app.register_blueprint(profesor_bp,    url_prefix='/profesor')

    # Manejadores de error globales
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Manejador de error CSRF - muestra mensaje claro en lugar de página en blanco
    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def csrf_error(e):
        from flask import flash, redirect, request as req
        flash('Error de seguridad (token expirado). Por favor recargue la página e intente de nuevo.', 'danger')
        return redirect(req.referrer or '/')

    return app
