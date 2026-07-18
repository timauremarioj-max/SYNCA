"""
Carga datos de demostración para SYNCA.
Ejecutar una sola vez: python seed_db.py
"""
import os, random
from datetime import date, time, timedelta
from dotenv import load_dotenv
load_dotenv(override=True)

from app import create_app
from app.extensions import db
from app.models.models import (Usuario, Estudiante, Materia,
                               Seccion, Inscripcion, Asistencia, Nota)

app = create_app(os.getenv('FLASK_ENV', 'development'))


def get_or_create_usuario(cedula, nombre, apellido, correo, rol, pw='unefa123'):
    u = Usuario.query.filter_by(cedula=cedula).first()
    if u:
        return u
    u = Usuario(cedula=cedula, nombre=nombre, apellido=apellido,
                correo=correo, rol=rol, is_active=True, email_confirmed=True)
    u.set_password(pw)
    db.session.add(u)
    db.session.flush()
    return u


def main():
    with app.app_context():
        db.create_all()

        if Usuario.query.first():
            print('Ya hay datos. Ejecute con BD vacía si quiere reiniciar.')
            return

        # ── Profesores ─────────────────────────────────────────────────────
        u_p1 = get_or_create_usuario('31091513','Jesús','Robertiz','jrobertiz@unefa.edu.ve','Profesor')
        u_p2 = get_or_create_usuario('33509133','Enmanuel','Chirino','echirino@unefa.edu.ve','Profesor')
        u_p3 = get_or_create_usuario('31150410','Mario','Timaure','mtimaure@unefa.edu.ve','Profesor')

        from app.models.models import Profesor as Prof
        p1 = Prof(usuario_id=u_p1.id, especialidad='Ingeniería de Software')
        p2 = Prof(usuario_id=u_p2.id, especialidad='Ciencias Básicas')
        p3 = Prof(usuario_id=u_p3.id, especialidad='Bases de Datos')
        db.session.add_all([p1, p2, p3])
        db.session.flush()

        # ── Materias ───────────────────────────────────────────────────────
        m1 = Materia(nombre='Programación',               codigo='ISO-501')
        m2 = Materia(nombre='Física',                     codigo='ISO-502')
        m3 = Materia(nombre='Química',                    codigo='ISO-503')
        m4 = Materia(nombre='Lenguaje de Programación',   codigo='ISO-504')
        db.session.add_all([m1, m2, m3, m4])
        db.session.flush()

        # ── Secciones (todas con nombre_seccion='D1') ────────────────────
        # Esto permite que un estudiante que se registre con sección D-51
        # quede auto-inscrito en las 4 materias.
        # ── Secciones de demostración ─────────────────────────────────────────
        # Los profesores de demostración ya tienen secciones cargadas.
        # En producción: el profesor crea su sección desde "Mis secciones",
        # escribe la materia libremente y elige D1 o D2.
        secciones = [
            Seccion(materia_id=None,
                    materia_nombre_libre=m1.nombre,
                    profesor_id=p1.id, nombre_seccion='D1',
                    aula='Lab-1', dia_semana='Lunes',
                    hora_inicio=time(7,0), hora_fin=time(9,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m1.nombre,
                    profesor_id=None, nombre_seccion='D2',
                    aula='Lab-2', dia_semana='Lunes',
                    hora_inicio=time(9,0), hora_fin=time(11,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m2.nombre,
                    profesor_id=p2.id, nombre_seccion='D1',
                    aula='Aula-3', dia_semana='Martes',
                    hora_inicio=time(9,0), hora_fin=time(11,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m2.nombre,
                    profesor_id=None, nombre_seccion='D2',
                    aula='Aula-4', dia_semana='Martes',
                    hora_inicio=time(11,0), hora_fin=time(13,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m3.nombre,
                    profesor_id=p2.id, nombre_seccion='D1',
                    aula='Lab-2', dia_semana='Miércoles',
                    hora_inicio=time(7,0), hora_fin=time(9,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m3.nombre,
                    profesor_id=None, nombre_seccion='D2',
                    aula='Lab-3', dia_semana='Miércoles',
                    hora_inicio=time(9,0), hora_fin=time(11,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m4.nombre,
                    profesor_id=p3.id, nombre_seccion='D1',
                    aula='Lab-1', dia_semana='Jueves',
                    hora_inicio=time(11,0), hora_fin=time(13,0)),
            Seccion(materia_id=None,
                    materia_nombre_libre=m4.nombre,
                    profesor_id=None, nombre_seccion='D2',
                    aula='Lab-4', dia_semana='Jueves',
                    hora_inicio=time(13,0), hora_fin=time(15,0)),
        ]
        db.session.add_all(secciones)
        db.session.flush()

        # ── Estudiantes ────────────────────────────────────────────────────
        datos_est = [
            ('20123456','Ana','Pérez',   'ana.perez@unefa.edu.ve'),
            ('20123457','Luis','Gómez',  'luis.gomez@unefa.edu.ve'),
            ('20123458','María','Rodríguez','maria.rodriguez@unefa.edu.ve'),
            ('20123459','Carlos','Fernández','carlos.fernandez@unefa.edu.ve'),
        ]
        estudiantes = []
        for cedula, nom, ape, correo in datos_est:
            u  = get_or_create_usuario(cedula, nom, ape, correo, 'Estudiante')
            est = Estudiante(usuario_id=u.id,
                             carrera='Ingeniería de Sistemas',
                             semestre='5to Semestre',
                             nombre_seccion='D1')
            db.session.add(est)
            estudiantes.append(est)
        db.session.flush()

        # ── Inscripciones automáticas — solo secciones D1 para estudiantes D1
        secciones_d1 = [s for s in secciones if s.nombre_seccion == 'D1']
        inscripciones = []
        for est in estudiantes:
            for sec in secciones_d1:
                insc = Inscripcion(estudiante_id=est.id, seccion_id=sec.id)
                db.session.add(insc)
                inscripciones.append(insc)
        db.session.flush()

        # ── Notas de ejemplo ───────────────────────────────────────────────
        for insc in inscripciones:
            n1,n2,n3,n4 = (round(random.uniform(11,19),2) for _ in range(4))
            nota = Nota(inscripcion_id=insc.id,
                        nota_1=n1, nota_2=n2, nota_3=n3, nota_4=n4)
            nota.promedio = round((n1+n2+n3+n4)/4, 2)
            db.session.add(nota)

        # ── Asistencias (Ana tiene una materia en riesgo) ──────────────────
        hoy = date.today()
        for idx, insc in enumerate(inscripciones):
            caso_riesgo = (insc.estudiante_id == estudiantes[0].id
                           and insc.seccion_id == secciones_d1[0].id)
            for sem in range(1, 9):
                fecha = hoy - timedelta(days=7*sem)
                estado = 'Ausente' if (caso_riesgo and sem <= 3) else (
                    'Ausente' if random.random() < 0.08 else 'Presente')
                db.session.add(Asistencia(
                    inscripcion_id=insc.id, fecha=fecha, estado=estado))

        db.session.commit()
        print('\n✓ Datos de demostración cargados.\n')
        print('Credenciales (contraseña: unefa123)')
        print('  Estudiante : 20123456 (Ana Pérez — tiene materia en riesgo)')
        print('  Estudiante : 20123457 (Luis Gómez)')
        print('  Estudiante : 20123458 (María Rodríguez)')
        print('  Estudiante : 20123459 (Carlos Fernández)')
        print('  Docente    : 31091513 (Jesús Robertiz — Programación)')
        print('  Docente    : 33509133 (Enmanuel Chirino — Física y Química)')
        print('  Docente    : 31150410 (Mario Timaure — Lenguaje de Programación)')


if __name__ == '__main__':
    main()
