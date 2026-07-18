from datetime import date
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.decorators import role_required
from app.extensions import db
from app.models.models import AgendaPersonal, HorarioPersonal

estudiante_bp = Blueprint('estudiante', __name__)
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
TIPOS_AGENDA = [('recordatorio', 'Recordatorio'),
                ('materia_electiva', 'Materia electiva'),
                ('actividad', 'Actividad académica')]


def _est():
    if not current_user.estudiante:
        abort(404)
    return current_user.estudiante


# ── Panel / Dashboard ─────────────────────────────────────────────────────────
@estudiante_bp.route('/panel')
@login_required
@role_required('Estudiante')
def panel():
    est   = _est()
    inscs = est.inscripciones
    promedios  = [float(i.nota.promedio) for i in inscs if i.nota]
    prom_gral  = round(sum(promedios) / len(promedios), 2) if promedios else 0.0
    total_aus  = sum(i.total_ausentes for i in inscs)
    en_riesgo  = [i for i in inscs if i.pierde_materia]
    return render_template('estudiante/panel.html',
                           estudiante=est,
                           inscripciones=inscs,
                           promedio_general=prom_gral,
                           total_materias=len(inscs),
                           total_ausencias=total_aus,
                           materias_en_riesgo=en_riesgo)


# ── Calificaciones ────────────────────────────────────────────────────────────
@estudiante_bp.route('/notas')
@login_required
@role_required('Estudiante')
def notas():
    from app.models.models import CORTES
    est   = _est()
    inscs = est.inscripciones

    # Build per-corte summary: {insc_id: {corte: {evaluaciones, usado, restante, acumulado}}}
    resumen = {}
    total_acum = []
    for i in inscs:
        resumen[i.id] = {}
        for c in range(1, 5):
            evs       = [ev for ev in i.evaluaciones if ev.corte == c]
            usado     = round(sum(float(ev.porcentaje) for ev in evs), 2)
            acumulado = round(sum(float(ev.aporte)     for ev in evs), 4)
            resumen[i.id][c] = {
                'evaluaciones': evs,
                'porcentaje_max': CORTES[c],
                'usado':     usado,
                'restante':  round(CORTES[c] - usado, 2),
                'acumulado': acumulado,
            }
        total_acum.append(round(sum(resumen[i.id][c]['acumulado'] for c in range(1,5)), 2))

    prom_gral = round(sum(total_acum) / len(total_acum), 2) if total_acum else 0.0

    return render_template('estudiante/notas.html',
                           estudiante=est,
                           inscripciones=inscs,
                           resumen=resumen,
                           total_acum=total_acum,
                           promedio_general=prom_gral,
                           cortes=CORTES)


# ── Asistencias ───────────────────────────────────────────────────────────────
@estudiante_bp.route('/asistencias')
@login_required
@role_required('Estudiante')
def asistencias():
    est = _est()
    return render_template('estudiante/asistencias.html',
                           estudiante=est,
                           inscripciones=est.inscripciones)


# ── Horario (oficial + personal editable) ────────────────────────────────────
@estudiante_bp.route('/horario')
@login_required
@role_required('Estudiante')
def horario():
    est    = _est()
    grilla = {dia: [] for dia in DIAS}
    for i in est.inscripciones:
        s = i.seccion
        if s.dia_semana in grilla:
            grilla[s.dia_semana].append(s)
    for dia in grilla:
        grilla[dia].sort(key=lambda s: s.hora_inicio or __import__("datetime").time.min)
    entradas_personales = (HorarioPersonal.query
                           .filter_by(usuario_id=current_user.id)
                           .order_by(HorarioPersonal.dia_semana, HorarioPersonal.hora_inicio)
                           .all())
    return render_template('estudiante/horario.html',
                           estudiante=est, grilla=grilla, dias=DIAS,
                           entradas_personales=entradas_personales)


@estudiante_bp.route('/horario/agregar', methods=['POST'])
@login_required
@role_required('Estudiante')
def horario_agregar():
    materia     = request.form.get('materia', '').strip()
    dia_semana  = request.form.get('dia_semana', '').strip()
    hora_inicio = request.form.get('hora_inicio', '').strip()
    hora_fin    = request.form.get('hora_fin', '').strip()
    seccion     = request.form.get('seccion', '').strip().upper()
    aula        = request.form.get('aula', '').strip()

    if not materia or not dia_semana or not hora_inicio or not hora_fin:
        flash('Materia, día, hora de inicio y hora de fin son obligatorios.', 'danger')
        return redirect(url_for('estudiante.horario'))
    if dia_semana not in DIAS:
        flash('Día de la semana inválido.', 'danger')
        return redirect(url_for('estudiante.horario'))

    db.session.add(HorarioPersonal(
        usuario_id=current_user.id,
        materia=materia,
        dia_semana=dia_semana,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        seccion=seccion,
        aula=aula,
    ))
    db.session.commit()
    flash(f'Clase "{materia}" agregada al horario.', 'success')
    return redirect(url_for('estudiante.horario'))


@estudiante_bp.route('/horario/<int:entrada_id>/eliminar', methods=['POST'])
@login_required
@role_required('Estudiante')
def horario_eliminar(entrada_id):
    entrada = HorarioPersonal.query.filter_by(
        id=entrada_id, usuario_id=current_user.id).first_or_404()
    db.session.delete(entrada)
    db.session.commit()
    flash('Clase eliminada del horario.', 'success')
    return redirect(url_for('estudiante.horario'))


# ── Agenda Personal ───────────────────────────────────────────────────────────
@estudiante_bp.route('/agenda')
@login_required
@role_required('Estudiante')
def agenda():
    est   = _est()
    # Ordenar: sin fecha al final, luego por fecha asc, luego por fecha creación desc
    # Sintaxis compatible con SQLite (nullslast no está disponible en SQLite)
    from sqlalchemy import case
    items = (AgendaPersonal.query
             .filter_by(estudiante_id=est.id)
             .order_by(
                 case((AgendaPersonal.fecha.is_(None), 1), else_=0).asc(),
                 AgendaPersonal.fecha.asc(),
                 AgendaPersonal.created_at.desc()
             )
             .all())
    return render_template('estudiante/agenda.html',
                           estudiante=est,
                           items=items,
                           tipos=TIPOS_AGENDA)


@estudiante_bp.route('/agenda/nueva', methods=['POST'])
@login_required
@role_required('Estudiante')
def agenda_nueva():
    est   = _est()
    titulo = request.form.get('titulo', '').strip()
    if not titulo:
        flash('El título es obligatorio.', 'danger')
        return redirect(url_for('estudiante.agenda'))

    fecha_str = request.form.get('fecha', '').strip()
    fecha_val = None
    if fecha_str:
        try:
            fecha_val = date.fromisoformat(fecha_str)
        except ValueError:
            flash('Formato de fecha inválido. Use AAAA-MM-DD.', 'danger')
            return redirect(url_for('estudiante.agenda'))

    tipo = request.form.get('tipo', 'recordatorio')
    if tipo not in [t[0] for t in TIPOS_AGENDA]:
        tipo = 'recordatorio'

    db.session.add(AgendaPersonal(
        estudiante_id=est.id,
        titulo=titulo,
        descripcion=request.form.get('descripcion', '').strip() or None,
        fecha=fecha_val,
        tipo=tipo,
    ))
    db.session.commit()
    flash('Elemento agregado a su agenda personal.', 'success')
    return redirect(url_for('estudiante.agenda'))


@estudiante_bp.route('/agenda/<int:item_id>/eliminar', methods=['POST'])
@login_required
@role_required('Estudiante')
def agenda_eliminar(item_id):
    est  = _est()
    item = AgendaPersonal.query.filter_by(id=item_id, estudiante_id=est.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Elemento eliminado de su agenda.', 'success')
    return redirect(url_for('estudiante.agenda'))


# ── Perfil ────────────────────────────────────────────────────────────────────
@estudiante_bp.route('/perfil')
@login_required
@role_required('Estudiante')
def perfil():
    return render_template('estudiante/perfil.html', estudiante=_est())
