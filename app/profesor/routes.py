"""
Panel del Docente — SYNCA
==========================
Flujo corregido según las Fases I y II:

1. El estudiante se registra en el sistema con su carrera, semestre y sección
   (D1 o D2). Queda inscrito automáticamente en el sistema.

2. El profesor abre "Mis secciones" y registra la materia que dicta
   (escrita libremente), selecciona D1 o D2, y opcionalmente aula/horario.
   SYNCA crea una nueva Seccion y copia dentro de ella a todos los
   estudiantes que se registraron con ese nombre de sección.

3. El profesor registra asistencia y calificaciones sobre esa lista.
   El estudiante ve los datos al instante en su propio panel (RF-4, RF-5).
"""
from datetime import date, time as dtime
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.decorators import role_required
from app.extensions import db
from app.models.models import (Seccion, Inscripcion, Asistencia,
                               Usuario, Estudiante, HorarioPersonal)

profesor_bp = Blueprint('profesor', __name__)

DIAS            = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
SECCIONES_VALID = ['D1', 'D2']


# ─────────────────── helpers ──────────────────────────────────────────────────
def _prof():
    if not current_user.profesor:
        abort(404)
    return current_user.profesor


def _sec_propia(seccion_id, prof):
    s = db.get_or_404(Seccion, seccion_id)
    if s.profesor_id != prof.id:
        abort(403)
    return s


# ─────────────────── PANEL ────────────────────────────────────────────────────
@profesor_bp.route('/panel')
@login_required
@role_required('Profesor')
def panel():
    prof = _prof()
    ids_est = {insc.estudiante_id
               for sec in prof.secciones
               for insc in sec.inscripciones}
    return render_template('profesor/panel.html',
                           profesor=prof,
                           secciones=prof.secciones,
                           total_estudiantes=len(ids_est))


# ─────────────────── MIS SECCIONES ────────────────────────────────────────────
@profesor_bp.route('/mis-secciones')
@login_required
@role_required('Profesor')
def mis_secciones():
    prof = _prof()
    return render_template('profesor/mis_secciones.html',
                           profesor=prof,
                           secciones=prof.secciones,
                           dias=DIAS,
                           secciones_validas=SECCIONES_VALID)


@profesor_bp.route('/mis-secciones/crear', methods=['POST'])
@login_required
@role_required('Profesor')
def crear_seccion():
    """
    El profesor escribe la materia libremente y elige la sección (D1/D2).
    El sistema crea la Seccion y auto-inscribe a todos los estudiantes
    que ya se registraron en esa sección.
    """
    prof           = _prof()
    nombre_materia = request.form.get('nombre_materia', '').strip()
    nombre_seccion = request.form.get('nombre_seccion', '').strip().upper()
    aula           = request.form.get('aula', '').strip()
    dia_semana     = request.form.get('dia_semana', '').strip()
    hora_inicio_s  = request.form.get('hora_inicio', '').strip()
    hora_fin_s     = request.form.get('hora_fin', '').strip()

    # ── Validaciones ──────────────────────────────────────────────────────────
    errores = []
    if not nombre_materia:
        errores.append('Escriba el nombre de la materia.')
    if nombre_seccion not in SECCIONES_VALID:
        errores.append('La sección debe ser D1 o D2.')
    if not aula:
        errores.append('Ingrese el aula.')
    if not dia_semana or dia_semana not in DIAS:
        errores.append('Seleccione un día de clase válido.')

    hi = hf = None
    if hora_inicio_s and hora_fin_s:
        try:
            hi = dtime.fromisoformat(hora_inicio_s)
            hf = dtime.fromisoformat(hora_fin_s)
            if hf <= hi:
                errores.append('La hora de fin debe ser posterior a la hora de inicio.')
        except ValueError:
            errores.append('Horas inválidas.')
    else:
        errores.append('Ingrese la hora de inicio y de fin de la clase.')

    if errores:
        for e in errores:
            flash(e, 'danger')
        return redirect(url_for('profesor.mis_secciones'))

    # ── ¿Ya existe esta combinación para este profesor? ───────────────────────
    duplicado = Seccion.query.filter_by(
        profesor_id=prof.id,
        nombre_seccion=nombre_seccion,
        materia_nombre_libre=nombre_materia
    ).first()
    if duplicado:
        flash(f'Ya tiene una sección {nombre_seccion} para "{nombre_materia}".', 'warning')
        return redirect(url_for('profesor.seccion_detalle', seccion_id=duplicado.id))

    # ── Crear la sección ──────────────────────────────────────────────────────
    sec = Seccion(
        materia_id=None,
        materia_nombre_libre=nombre_materia,
        profesor_id=prof.id,
        nombre_seccion=nombre_seccion,
        aula=aula,
        dia_semana=dia_semana,
        hora_inicio=hi,
        hora_fin=hf,
    )
    db.session.add(sec)
    db.session.flush()   # obtener sec.id

    # ── Auto-inscribir estudiantes que ya se registraron en esa sección ───────
    estudiantes_de_seccion = (Estudiante.query
                              .filter_by(nombre_seccion=nombre_seccion)
                              .all())
    inscritos = 0
    for est in estudiantes_de_seccion:
        ya = Inscripcion.query.filter_by(
            estudiante_id=est.id, seccion_id=sec.id).first()
        if not ya:
            db.session.add(Inscripcion(estudiante_id=est.id, seccion_id=sec.id))
            inscritos += 1

    db.session.commit()

    if inscritos:
        flash(
            f'Sección {nombre_seccion} creada para "{nombre_materia}". '
            f'{inscritos} estudiante(s) de esa sección fueron inscritos automáticamente.',
            'success'
        )
    else:
        flash(
            f'Sección {nombre_seccion} creada para "{nombre_materia}". '
            f'Aún no hay estudiantes registrados con la sección {nombre_seccion}. '
            f'Cuando se registren, aparecerán aquí.',
            'warning'
        )
    return redirect(url_for('profesor.seccion_detalle', seccion_id=sec.id))


@profesor_bp.route('/mis-secciones/<int:seccion_id>/eliminar', methods=['POST'])
@login_required
@role_required('Profesor')
def eliminar_seccion(seccion_id):
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)
    nombre  = f'{seccion.nombre_materia} — {seccion.nombre_seccion}'
    db.session.delete(seccion)
    db.session.commit()
    flash(f'Sección "{nombre}" eliminada.', 'info')
    return redirect(url_for('profesor.mis_secciones'))


# ─────────────────── DETALLE DE SECCIÓN ───────────────────────────────────────
@profesor_bp.route('/secciones/<int:seccion_id>')
@login_required
@role_required('Profesor')
def seccion_detalle(seccion_id):
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)
    inscs   = (Inscripcion.query
               .filter_by(seccion_id=seccion.id)
               .join(Estudiante)
               .join(Usuario, Estudiante.usuario_id == Usuario.id)
               .order_by(Usuario.apellido, Usuario.nombre)
               .all())

    # Búsqueda por cédula para confirmar si un estudiante está en la sección
    cedula_buscar      = request.args.get('cedula', '').strip()
    estudiante_buscado = None
    en_esta_seccion    = False

    if cedula_buscar:
        # Búsqueda tolerante: con o sin prefijo
        u = Usuario.query.filter_by(cedula=cedula_buscar, rol='Estudiante').first()
        if u is None:
            for pfx in ('V-', 'E-', 'J-'):
                u = Usuario.query.filter_by(cedula=pfx + cedula_buscar, rol='Estudiante').first()
                if u:
                    break
        if u and u.estudiante:
            estudiante_buscado = u
            en_esta_seccion = any(i.estudiante_id == u.estudiante.id for i in inscs)
        else:
            flash(f'No se encontró ningún estudiante con la cédula "{cedula_buscar}".', 'danger')

    return render_template('profesor/seccion_detalle.html',
                           seccion=seccion,
                           inscripciones=inscs,
                           cedula_buscar=cedula_buscar,
                           estudiante_buscado=estudiante_buscado,
                           en_esta_seccion=en_esta_seccion)


# ─────────────────── EDITAR HORARIO ───────────────────────────────────────────
@profesor_bp.route('/secciones/<int:seccion_id>/editar-horario', methods=['GET', 'POST'])
@login_required
@role_required('Profesor')
def editar_horario(seccion_id):
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)
    if request.method == 'POST':
        dia  = request.form.get('dia_semana', '').strip()
        aula = request.form.get('aula', '').strip()
        hi_s = request.form.get('hora_inicio', '')
        hf_s = request.form.get('hora_fin', '')
        errores = []
        if dia not in DIAS:
            errores.append('Seleccione un día válido.')
        if not aula:
            errores.append('El aula no puede estar vacía.')
        try:
            hi = dtime.fromisoformat(hi_s)
            hf = dtime.fromisoformat(hf_s)
            if hf <= hi:
                errores.append('La hora de fin debe ser posterior a la de inicio.')
        except Exception:
            errores.append('Horas inválidas.')
        if errores:
            for e in errores:
                flash(e, 'danger')
            return redirect(url_for('profesor.editar_horario', seccion_id=seccion.id))
        seccion.dia_semana  = dia
        seccion.aula        = aula
        seccion.hora_inicio = hi
        seccion.hora_fin    = hf
        db.session.commit()
        flash('Horario actualizado. Los estudiantes ya ven el cambio.', 'success')
        return redirect(url_for('profesor.seccion_detalle', seccion_id=seccion.id))
    return render_template('profesor/editar_horario.html', seccion=seccion, dias=DIAS)


# ─────────────────── ASISTENCIA ───────────────────────────────────────────────
@profesor_bp.route('/secciones/<int:seccion_id>/asistencia', methods=['GET', 'POST'])
@login_required
@role_required('Profesor')
def asistencia(seccion_id):
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)
    hoy     = date.today()
    inscs   = (Inscripcion.query
               .filter_by(seccion_id=seccion.id)
               .join(Estudiante)
               .join(Usuario, Estudiante.usuario_id == Usuario.id)
               .order_by(Usuario.apellido, Usuario.nombre)
               .all())

    ya = bool(inscs) and any(
        Asistencia.query.filter_by(inscripcion_id=i.id, fecha=hoy).first()
        for i in inscs
    )

    if request.method == 'POST':
        if ya:
            flash('La asistencia de hoy ya fue registrada para esta sección.', 'warning')
            return redirect(url_for('profesor.asistencia', seccion_id=seccion.id))
        for i in inscs:
            estado = request.form.get(f'estado_{i.id}', 'Ausente')
            if estado not in ('Presente', 'Ausente', 'Justificado'):
                estado = 'Ausente'
            if not Asistencia.query.filter_by(inscripcion_id=i.id, fecha=hoy).first():
                db.session.add(Asistencia(
                    inscripcion_id=i.id, fecha=hoy, estado=estado))
        db.session.commit()
        flash('Asistencia registrada. Los estudiantes pueden consultarla ahora.', 'success')
        return redirect(url_for('profesor.asistencia', seccion_id=seccion.id))

    asistencias_hoy = {}
    if ya:
        for i in inscs:
            r = Asistencia.query.filter_by(inscripcion_id=i.id, fecha=hoy).first()
            asistencias_hoy[i.id] = r.estado if r else None

    return render_template('profesor/asistencia.html',
                           seccion=seccion, inscripciones=inscs,
                           ya_registrada=ya, asistencias_hoy=asistencias_hoy, hoy=hoy)


# ─────────────────── CALIFICACIONES (módulo v2: evaluaciones por corte) ────────
@profesor_bp.route('/secciones/<int:seccion_id>/notas')
@login_required
@role_required('Profesor')
def notas(seccion_id):
    from app.models.models import Evaluacion, CORTES
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)
    inscs   = (Inscripcion.query
               .filter_by(seccion_id=seccion.id)
               .join(Estudiante)
               .join(Usuario, Estudiante.usuario_id == Usuario.id)
               .order_by(Usuario.apellido, Usuario.nombre)
               .all())

    # Pre-build evaluaciones por inscripcion y corte para el template
    # {inscripcion_id: {corte: {evaluaciones, usado, restante, acumulado}}}
    evals_map = {}
    for i in inscs:
        evals_map[i.id] = {}
        for c in range(1, 5):
            evs       = [ev for ev in i.evaluaciones if ev.corte == c]
            usado     = round(sum(float(ev.porcentaje) for ev in evs), 2)
            acumulado = round(sum(float(ev.aporte)     for ev in evs), 4)
            evals_map[i.id][c] = {
                'evaluaciones': evs,
                'usado':        usado,
                'restante':     round(CORTES[c] - usado, 2),
                'acumulado':    acumulado,
            }

    return render_template('profesor/notas.html',
                           seccion=seccion,
                           inscripciones=inscs,
                           evals_map=evals_map,
                           cortes=CORTES)


@profesor_bp.route('/secciones/<int:seccion_id>/evaluacion/agregar', methods=['POST'])
@login_required
@role_required('Profesor')
def agregar_evaluacion(seccion_id):
    from app.models.models import Evaluacion, CORTES
    prof    = _prof()
    seccion = _sec_propia(seccion_id, prof)

    insc_id   = request.form.get('inscripcion_id', '').strip()
    corte_raw = request.form.get('corte', '').strip()
    nombre    = request.form.get('nombre', '').strip()
    porc_raw  = request.form.get('porcentaje', '').strip().replace(',', '.')
    nota_raw  = request.form.get('nota_obtenida', '').strip().replace(',', '.')

    # ── Validar campos obligatorios ──────────────────────────────────────────
    errores = []
    if not nombre:
        errores.append('El nombre de la evaluación es obligatorio.')
    try:
        corte = int(corte_raw)
        if corte not in CORTES:
            raise ValueError
    except (ValueError, TypeError):
        errores.append('Seleccione un corte válido (1 al 4).')
        corte = None
    try:
        porcentaje = int(porc_raw)
        if porcentaje <= 0 or porcentaje > 100:
            raise ValueError
    except (ValueError, TypeError):
        errores.append('El porcentaje debe ser un número entero mayor que 0.')
        porcentaje = None
    try:
        nota = int(nota_raw)
        if not (0 <= nota <= 20):
            raise ValueError
    except (ValueError, TypeError):
        errores.append('La nota debe ser un número entero entre 0 y 20.')
        nota = None
    try:
        insc_id = int(insc_id)
        insc = Inscripcion.query.filter_by(id=insc_id, seccion_id=seccion.id).first()
        if not insc:
            raise ValueError
    except (ValueError, TypeError):
        errores.append('Inscripción no válida.')
        insc = None

    if errores:
        for e in errores:
            flash(e, 'danger')
        return redirect(url_for('profesor.notas', seccion_id=seccion_id))

    # ── Validar que no se supere el porcentaje máximo del corte ─────────────
    max_corte = CORTES[corte]
    ya_usado  = sum(
        float(ev.porcentaje)
        for ev in insc.evaluaciones
        if ev.corte == corte
    )
    disponible = round(max_corte - ya_usado, 2)

    if porcentaje > disponible:
        nombres_corte = {1: 'Primer', 2: 'Segundo', 3: 'Tercer', 4: 'Cuarto'}
        flash(
            f'El {nombres_corte[corte]} Corte tiene un máximo de {max_corte}%. '
            f'Ya existen evaluaciones que suman {ya_usado}%. '
            f'Solo quedan disponibles {disponible}%.',
            'danger'
        )
        return redirect(url_for('profesor.notas', seccion_id=seccion_id))

    # ── Crear y guardar la evaluación ────────────────────────────────────────
    ev = Evaluacion(
        inscripcion_id=insc.id,
        corte=corte,
        nombre=nombre,
        porcentaje=porcentaje,
        nota_obtenida=nota,
    )
    ev.calcular_aporte()
    db.session.add(ev)
    db.session.commit()
    flash(f'Evaluación "{nombre}" guardada. Puntos obtenidos: {round(float(ev.aporte), 2)} pts', 'success')
    return redirect(url_for('profesor.notas', seccion_id=seccion_id))


@profesor_bp.route('/evaluacion/<int:ev_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('Profesor')
def editar_evaluacion(ev_id):
    from app.models.models import Evaluacion, CORTES
    prof = _prof()
    ev   = Evaluacion.query.get_or_404(ev_id)
    # Verify ownership
    if ev.inscripcion.seccion.profesor_id != prof.id:
        abort(403)

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        porc_raw = request.form.get('porcentaje', '').strip().replace(',', '.')
        nota_raw = request.form.get('nota_obtenida', '').strip().replace(',', '.')
        errores  = []
        if not nombre:
            errores.append('El nombre no puede estar vacío.')
        try:
            porcentaje = int(porc_raw)
            if porcentaje <= 0 or porcentaje > 100:
                raise ValueError
        except (ValueError, TypeError):
            errores.append('El porcentaje debe ser un número entero mayor que 0.')
            porcentaje = None
        try:
            nota = int(nota_raw)
            if not (0 <= nota <= 20):
                raise ValueError
        except (ValueError, TypeError):
            errores.append('La nota debe ser un número entero entre 0 y 20.')
            nota = None

        if not errores:
            # Check porcentaje: sum of others in same corte + new porcentaje
            ya_usado = sum(
                float(e.porcentaje)
                for e in ev.inscripcion.evaluaciones
                if e.corte == ev.corte and e.id != ev.id
            )
            disponible = round(CORTES[ev.corte] - ya_usado, 2)
            if porcentaje > disponible:
                errores.append(
                    f'Porcentaje excede lo disponible en este corte. '
                    f'Máximo disponible: {disponible}%.'
                )

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template('profesor/editar_evaluacion.html', ev=ev, cortes=CORTES)

        ev.nombre        = nombre
        ev.porcentaje    = porcentaje
        ev.nota_obtenida = nota
        ev.calcular_aporte()
        db.session.commit()
        flash(f'Evaluación "{nombre}" actualizada.', 'success')
        return redirect(url_for('profesor.notas', seccion_id=ev.inscripcion.seccion_id))

    return render_template('profesor/editar_evaluacion.html', ev=ev, cortes=CORTES)


@profesor_bp.route('/evaluacion/<int:ev_id>/eliminar', methods=['POST'])
@login_required
@role_required('Profesor')
def eliminar_evaluacion(ev_id):
    from app.models.models import Evaluacion
    prof = _prof()
    ev   = Evaluacion.query.get_or_404(ev_id)
    if ev.inscripcion.seccion.profesor_id != prof.id:
        abort(403)
    seccion_id = ev.inscripcion.seccion_id
    nombre     = ev.nombre
    db.session.delete(ev)
    db.session.commit()
    flash(f'Evaluación "{nombre}" eliminada.', 'success')
    return redirect(url_for('profesor.notas', seccion_id=seccion_id))


# ─────────────────── MI HORARIO PERSONAL ──────────────────────────────────────
@profesor_bp.route('/mi-horario')
@login_required
@role_required('Profesor')
def mi_horario():
    prof   = _prof()
    grilla = {dia: [] for dia in DIAS}
    for sec in prof.secciones:
        if sec.dia_semana and sec.dia_semana in grilla:
            grilla[sec.dia_semana].append(sec)
    entradas = (HorarioPersonal.query
                .filter_by(usuario_id=current_user.id)
                .order_by(HorarioPersonal.dia_semana, HorarioPersonal.hora_inicio)
                .all())
    return render_template('profesor/mi_horario.html',
                           profesor=prof, grilla=grilla,
                           dias=DIAS, entradas=entradas)


@profesor_bp.route('/mi-horario/agregar', methods=['POST'])
@login_required
@role_required('Profesor')
def mi_horario_agregar():
    materia    = request.form.get('materia', '').strip()
    dia_semana = request.form.get('dia_semana', '').strip()
    hi         = request.form.get('hora_inicio', '').strip()
    hf         = request.form.get('hora_fin', '').strip()
    seccion    = request.form.get('seccion', '').strip().upper()
    aula       = request.form.get('aula', '').strip()
    if not materia or not dia_semana or not hi or not hf:
        flash('Materia, día y horario son obligatorios.', 'danger')
        return redirect(url_for('profesor.mi_horario'))
    db.session.add(HorarioPersonal(
        usuario_id=current_user.id, materia=materia,
        dia_semana=dia_semana, hora_inicio=hi, hora_fin=hf,
        seccion=seccion, aula=aula))
    db.session.commit()
    flash(f'Clase "{materia}" agregada al horario.', 'success')
    return redirect(url_for('profesor.mi_horario'))


@profesor_bp.route('/mi-horario/<int:eid>/eliminar', methods=['POST'])
@login_required
@role_required('Profesor')
def mi_horario_eliminar(eid):
    e = HorarioPersonal.query.filter_by(
        id=eid, usuario_id=current_user.id).first_or_404()
    db.session.delete(e)
    db.session.commit()
    flash('Clase eliminada.', 'success')
    return redirect(url_for('profesor.mi_horario'))


# ─────────────────── PERFIL ───────────────────────────────────────────────────
@profesor_bp.route('/perfil')
@login_required
@role_required('Profesor')
def perfil():
    return render_template('profesor/perfil.html', profesor=_prof())


# ─────────────────── BÚSQUEDA DE ESTUDIANTES (RF-5) ───────────────────────────
@profesor_bp.route('/estudiantes')
@login_required
@role_required('Profesor')
def estudiantes():
    """
    El profesor puede buscar cualquier estudiante por cédula o nombre
    para verificar su existencia en el sistema.
    """
    prof   = _prof()
    cedula = request.args.get('cedula', '').strip()
    nombre = request.args.get('nombre', '').strip()
    busco  = bool(cedula or nombre)

    resultados = []
    if busco:
        from app.models.models import Usuario
        q = Usuario.query.filter_by(rol='Estudiante')
        if cedula:
            q = q.filter(Usuario.cedula.ilike(f'%{cedula}%'))
        if nombre:
            q = q.filter(db.or_(
                Usuario.nombre.ilike(f'%{nombre}%'),
                Usuario.apellido.ilike(f'%{nombre}%')
            ))
        resultados = q.order_by(Usuario.apellido).limit(50).all()

    return render_template('profesor/estudiantes.html',
                           profesor=prof,
                           resultados=resultados,
                           cedula=cedula, nombre=nombre, busco=busco)


@profesor_bp.route('/estudiantes/<cedula_est>')
@login_required
@role_required('Profesor')
def estudiante_detalle(cedula_est):
    from app.models.models import Usuario
    prof = _prof()
    u    = Usuario.query.filter_by(cedula=cedula_est, rol='Estudiante').first_or_404()
    est  = u.estudiante
    mis_ids       = [s.id for s in prof.secciones]
    inscs_propias = [i for i in est.inscripciones if i.seccion_id in mis_ids] if est else []
    return render_template('profesor/estudiante_detalle.html',
                           profesor=prof, estudiante_u=u,
                           estudiante=est, inscripciones=inscs_propias)
