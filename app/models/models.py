from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id              = db.Column(db.Integer, primary_key=True)
    cedula          = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre          = db.Column(db.String(100), nullable=False)
    apellido        = db.Column(db.String(100), nullable=False)
    correo          = db.Column(db.String(150), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    rol             = db.Column(db.String(15), nullable=False)
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    email_confirmed = db.Column(db.Boolean, default=True, nullable=False)
    foto_perfil     = db.Column(db.String(256), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    estudiante = db.relationship('Estudiante', backref='usuario', uselist=False,
                                 cascade='all, delete-orphan')
    profesor   = db.relationship('Profesor',   backref='usuario', uselist=False,
                                 cascade='all, delete-orphan')

    def set_password(self, pw):
        self.contrasena_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.contrasena_hash, pw)

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class Estudiante(db.Model):
    __tablename__ = 'estudiantes'
    id             = db.Column(db.Integer, primary_key=True)
    usuario_id     = db.Column(db.Integer, db.ForeignKey('usuarios.id'),
                               nullable=False, unique=True)
    carrera        = db.Column(db.String(100), nullable=False)
    semestre       = db.Column(db.String(20),  nullable=False)
    nombre_seccion = db.Column(db.String(20),  nullable=False, default='')

    inscripciones = db.relationship('Inscripcion', backref='estudiante',
                                    lazy=True, cascade='all, delete-orphan')
    agenda        = db.relationship('AgendaPersonal', backref='estudiante',
                                    lazy=True, cascade='all, delete-orphan')


class Profesor(db.Model):
    __tablename__ = 'profesores'
    id           = db.Column(db.Integer, primary_key=True)
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'),
                             nullable=False, unique=True)
    especialidad = db.Column(db.String(100), nullable=False)

    secciones = db.relationship('Seccion', backref='profesor', lazy=True)


class Materia(db.Model):
    __tablename__ = 'materias'
    id     = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20),  unique=True, nullable=False)

    secciones = db.relationship('Seccion', backref='materia', lazy=True)


class Seccion(db.Model):
    """
    Representa una sección académica (ej: D1 o D2).
    El campo materia_nombre_libre permite al profesor escribir su materia
    libremente, sin depender de una lista fija.
    materia_id es opcional (puede ser NULL cuando el profesor define la materia).
    """
    __tablename__ = 'secciones'
    id                  = db.Column(db.Integer, primary_key=True)
    materia_id          = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=True)
    # Nombre de la materia escrito libremente por el profesor:
    materia_nombre_libre = db.Column(db.String(150), nullable=True)
    profesor_id         = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=True)
    nombre_seccion      = db.Column(db.String(20), nullable=False)   # D1 / D2
    aula                = db.Column(db.String(50), nullable=False, default='')
    dia_semana          = db.Column(db.String(15), nullable=False, default='')
    hora_inicio         = db.Column(db.Time,       nullable=True)
    hora_fin            = db.Column(db.Time,       nullable=True)

    inscripciones = db.relationship('Inscripcion', backref='seccion', lazy=True)

    @property
    def nombre_materia(self):
        """Devuelve el nombre de la materia sin importar de dónde viene."""
        if self.materia_nombre_libre:
            return self.materia_nombre_libre
        if self.materia:
            return self.materia.nombre
        return '(Sin materia)'

    @property
    def hora_inicio_fmt(self):
        return self.hora_inicio.strftime('%I:%M %p') if self.hora_inicio else '—'

    @property
    def hora_fin_fmt(self):
        return self.hora_fin.strftime('%I:%M %p') if self.hora_fin else '—'


class Inscripcion(db.Model):
    """
    Relación Estudiante ↔ Seccion.
    Conexión directa: lo que el profesor escribe, el estudiante lee al instante.
    """
    __tablename__ = 'inscripciones'
    id            = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    seccion_id    = db.Column(db.Integer, db.ForeignKey('secciones.id'),   nullable=False)

    asistencias = db.relationship('Asistencia', backref='inscripcion',
                                  lazy=True, cascade='all, delete-orphan')
    nota        = db.relationship('Nota', backref='inscripcion',
                                  uselist=False, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('estudiante_id', 'seccion_id', name='uq_est_sec'),
    )

    @property
    def total_clases_registradas(self):
        return len(self.asistencias)

    @property
    def total_ausentes(self):
        return sum(1 for a in self.asistencias if a.estado == 'Ausente')

    @property
    def total_presentes(self):
        return sum(1 for a in self.asistencias if a.estado == 'Presente')

    @property
    def total_justificados(self):
        return sum(1 for a in self.asistencias if a.estado == 'Justificado')

    @property
    def porcentaje_inasistencia(self):
        t = self.total_clases_registradas
        return 0.0 if t == 0 else round((self.total_ausentes / t) * 100, 1)

    @property
    def pierde_materia(self):
        from flask import current_app
        limite = current_app.config.get('LIMITE_INASISTENCIAS_PORCENTAJE', 25)
        return self.porcentaje_inasistencia >= limite


class Asistencia(db.Model):
    __tablename__ = 'asistencias'
    id             = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    fecha          = db.Column(db.Date, nullable=False, default=date.today)
    estado         = db.Column(db.String(15), nullable=False)   # Presente|Ausente|Justificado

    __table_args__ = (
        db.UniqueConstraint('inscripcion_id', 'fecha', name='uq_insc_fecha'),
    )


class Nota(db.Model):
    __tablename__ = 'notas'
    id             = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'),
                               nullable=False, unique=True)
    nota_1   = db.Column(db.Numeric(4, 2), default=0)
    nota_2   = db.Column(db.Numeric(4, 2), default=0)
    nota_3   = db.Column(db.Numeric(4, 2), default=0)
    nota_4   = db.Column(db.Numeric(4, 2), default=0)
    promedio = db.Column(db.Numeric(4, 2), default=0)

    def recalcular_promedio(self):
        vs = [float(self.nota_1 or 0), float(self.nota_2 or 0),
              float(self.nota_3 or 0), float(self.nota_4 or 0)]
        self.promedio = round(sum(vs) / 4, 2)
        return float(self.promedio)


class AgendaPersonal(db.Model):
    __tablename__ = 'agenda_personal'
    id            = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    titulo        = db.Column(db.String(200), nullable=False)
    descripcion   = db.Column(db.Text, nullable=True)
    fecha         = db.Column(db.Date, nullable=True)
    tipo          = db.Column(db.String(30), default='recordatorio')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class HorarioPersonal(db.Model):
    __tablename__ = 'horario_personal'
    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    materia     = db.Column(db.String(150), nullable=False)
    dia_semana  = db.Column(db.String(15),  nullable=False)
    hora_inicio = db.Column(db.String(5),   nullable=False)
    hora_fin    = db.Column(db.String(5),   nullable=False)
    seccion     = db.Column(db.String(20),  nullable=False, default='')
    aula        = db.Column(db.String(50),  nullable=False, default='')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario',
                              backref=db.backref('horario_personal', lazy=True))


# ── NUEVO MÓDULO DE CALIFICACIONES ────────────────────────────────────────────
CORTES = {1: 25.0, 2: 25.0, 3: 25.0, 4: 25.0}   # Porcentaje máximo por corte


class Evaluacion(db.Model):
    """
    Evaluación individual dentro de un corte académico.
    El profesor crea tantas como necesite; el sistema calcula el aporte automáticamente.
    Aporte (pts) = (nota_obtenida × porcentaje) / 100
    Ejemplo: nota=15, porcentaje=5 → (15×5)/100 = 0.75 pts sobre 20 posibles
    """
    __tablename__ = 'evaluaciones'
    id             = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'),
                               nullable=False, index=True)
    corte          = db.Column(db.Integer, nullable=False)       # 1, 2, 3 ó 4
    nombre         = db.Column(db.String(150), nullable=False)   # texto libre
    porcentaje     = db.Column(db.Numeric(5, 2), nullable=False) # peso dentro del corte
    nota_obtenida  = db.Column(db.Numeric(4, 2), nullable=False) # 0-20
    aporte         = db.Column(db.Numeric(5, 4), nullable=False, default=0)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    inscripcion = db.relationship('Inscripcion',
                                  backref=db.backref('evaluaciones', lazy=True,
                                                     cascade='all, delete-orphan'))

    def calcular_aporte(self):
        """Acumulado = (nota_obtenida * porcentaje) / 100
        Ejemplo: nota=15, porcentaje=5% → (15 × 5) / 100 = 0.75 puntos"""
        self.aporte = round((float(self.nota_obtenida) * float(self.porcentaje)) / 100.0, 4)
        return float(self.aporte)

    __table_args__ = (
        db.CheckConstraint('corte BETWEEN 1 AND 4', name='ck_corte_rango'),
    )
