from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.auth.forms import LoginForm, RegistroForm, RecuperarForm, SEMESTRES_VALORES
from app.extensions import db
from app.models.models import Usuario, Estudiante, Profesor, Seccion, Inscripcion

auth_bp = Blueprint('auth', __name__)


def _redir():
    if current_user.rol == 'Profesor':
        return redirect(url_for('profesor.panel'))
    return redirect(url_for('estudiante.panel'))


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redir()
    form = LoginForm()
    if form.validate_on_submit():
        cedula = form.cedula.data.strip()

        # Búsqueda tolerante: con o sin prefijo V- / E- / J-
        u = Usuario.query.filter_by(cedula=cedula).first()
        if u is None:
            # Intentar sin prefijo (ej: usuario escribió "20123456" pero guardado "V-20123456")
            for prefijo in ('V-', 'E-', 'J-', 'G-', 'P-'):
                u = Usuario.query.filter_by(cedula=prefijo + cedula).first()
                if u:
                    break
            # Intentar al revés (usuario escribió "V-20123456" pero guardado "20123456")
            if u is None and '-' in cedula:
                sin_prefijo = cedula.split('-', 1)[1]
                u = Usuario.query.filter_by(cedula=sin_prefijo).first()

        if u is None:
            flash('No existe ninguna cuenta con esa cédula.', 'danger')
            return render_template('auth/login.html', form=form)

        if not u.check_password(form.contrasena.data):
            flash('La contraseña es incorrecta. Intente de nuevo.', 'danger')
            return render_template('auth/login.html', form=form)

        if not u.is_active:
            flash('Su cuenta está desactivada. Contacte a la administración.', 'warning')
            return render_template('auth/login.html', form=form)

        login_user(u, remember=True)
        return _redir()

    # Errores de validación del formulario
    if request.method == 'POST':
        for campo, errores in form.errors.items():
            if campo != 'csrf_token':
                for e in errores:
                    flash(e, 'danger')

    return render_template('auth/login.html', form=form)


# ── LOGOUT ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


# ── REGISTRO ──────────────────────────────────────────────────────────────────
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return _redir()

    form = RegistroForm()

    if request.method == 'POST':
        if not form.validate_on_submit():
            for campo, errores in form.errors.items():
                for err in errores:
                    if campo == 'csrf_token':
                        flash('Error de seguridad. Recargue la página e intente de nuevo.', 'danger')
                    else:
                        flash(err, 'danger')
            return render_template('auth/registro.html', form=form)

        cedula   = form.cedula.data.strip()
        nombre   = form.nombre.data.strip()
        apellido = form.apellido.data.strip()
        correo   = form.correo.data.strip().lower()
        rol      = form.rol.data

        # Verificar duplicados
        if Usuario.query.filter_by(cedula=cedula).first():
            flash('Ya existe una cuenta con esa cédula.', 'danger')
            return render_template('auth/registro.html', form=form)
        if Usuario.query.filter_by(correo=correo).first():
            flash('Ya existe una cuenta con ese correo electrónico.', 'danger')
            return render_template('auth/registro.html', form=form)

        # Validaciones extra para estudiantes
        carrera        = (form.carrera.data or '').strip()
        semestre       = (form.semestre.data or '').strip()
        nombre_seccion = (form.nombre_seccion.data or '').strip().upper()

        if rol == 'Estudiante':
            errores_est = []
            if not carrera:
                errores_est.append('Debe seleccionar una carrera.')
            if not semestre or semestre not in SEMESTRES_VALORES:
                errores_est.append('Debe seleccionar un semestre.')
            if not nombre_seccion:
                errores_est.append('Debe ingresar la sección (ej: D1 o D2).')
            if errores_est:
                for e in errores_est:
                    flash(e, 'danger')
                return render_template('auth/registro.html', form=form)

        try:
            # Crear usuario
            u = Usuario(
                cedula=cedula,
                nombre=nombre,
                apellido=apellido,
                correo=correo,
                rol=rol,
                is_active=True,
                email_confirmed=True,
            )
            u.set_password(form.contrasena.data)
            db.session.add(u)
            db.session.flush()

            if rol == 'Estudiante':
                est = Estudiante(
                    usuario_id=u.id,
                    carrera=carrera,
                    semestre=semestre,
                    nombre_seccion=nombre_seccion,
                )
                db.session.add(est)
                db.session.flush()

                secciones = Seccion.query.filter_by(nombre_seccion=nombre_seccion).all()
                inscritas = []
                for sec in secciones:
                    ya = Inscripcion.query.filter_by(
                        estudiante_id=est.id, seccion_id=sec.id).first()
                    if not ya:
                        db.session.add(Inscripcion(
                            estudiante_id=est.id, seccion_id=sec.id))
                        inscritas.append(sec.nombre_materia)

                db.session.commit()
                if inscritas:
                    flash(
                        f'Cuenta creada. Inscrito en: {", ".join(inscritas)}.',
                        'success')
                else:
                    flash(
                        f'Cuenta creada. No hay materias activas para la sección '
                        f'"{nombre_seccion}". Contacte a la administración.',
                        'warning')

            else:  # Profesor
                db.session.add(Profesor(usuario_id=u.id, especialidad='Sin asignar'))
                db.session.commit()
                flash('Cuenta de docente creada exitosamente. Puede iniciar sesión.', 'success')

            return redirect(url_for('auth.login'))

        except Exception:
            db.session.rollback()
            import traceback; traceback.print_exc()
            flash('Error al guardar el registro. Intente de nuevo.', 'danger')
            return render_template('auth/registro.html', form=form)

    return render_template('auth/registro.html', form=form)


# ── RECUPERAR ─────────────────────────────────────────────────────────────────
@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if current_user.is_authenticated:
        return _redir()
    form = RecuperarForm()
    if form.validate_on_submit():
        flash('Si su cédula está registrada, recibirá instrucciones por correo.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/recuperar.html', form=form)
