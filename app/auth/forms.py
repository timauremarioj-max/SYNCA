from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
import re

MSG_REQ     = 'Este campo es obligatorio.'
MSG_MIN6    = 'Debe tener al menos 6 caracteres.'
MSG_CED_LEN = 'La cédula debe tener entre 6 y 20 caracteres.'
MSG_PASS_EQ = 'Las contraseñas no coinciden.'
MSG_EMAIL   = 'Ingrese un correo válido (ejemplo: nombre@correo.com).'
MSG_MAX100  = 'No puede superar 100 caracteres.'

# ── Carreras ofrecidas en UNEFA Núcleo Falcón - Sede Coro ────────────────────
CARRERAS = [
    ('', '— Seleccione —'),
    ('Ingeniería de Sistemas',           'Ingeniería de Sistemas'),
    ('Ingeniería de Telecomunicaciones', 'Ingeniería de Telecomunicaciones'),
    ('Ingeniería Petroquímica',          'Ingeniería Petroquímica'),
    ('Lic. en Administración de Desastres', 'Lic. en Administración de Desastres'),
    ('Lic. en Economía Social',          'Lic. en Economía Social'),
    ('TSU en Turismo',                   'TSU en Turismo'),
]

# Semestres máximos por carrera
SEMESTRES_POR_CARRERA = {
    'Ingeniería de Sistemas':              8,
    'Ingeniería de Telecomunicaciones':    8,
    'Ingeniería Petroquímica':             8,
    'Lic. en Administración de Desastres': 8,
    'Lic. en Economía Social':             8,
    'TSU en Turismo':                      4,
}

# Lista base de semestres (el JS la filtra según la carrera)
SEMESTRES = [
    ('', '— Seleccione —'),
    ('1er Semestre', '1er Semestre'),
    ('2do Semestre', '2do Semestre'),
    ('3er Semestre', '3er Semestre'),
    ('4to Semestre', '4to Semestre'),
    ('5to Semestre', '5to Semestre'),
    ('6to Semestre', '6to Semestre'),
    ('7mo Semestre', '7mo Semestre'),
    ('8vo Semestre', '8vo Semestre'),
]

SEMESTRES_VALORES = [v for v, _ in SEMESTRES]


def validar_correo(form, field):
    patron = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron, (field.data or '').strip()):
        raise ValidationError(MSG_EMAIL)


class LoginForm(FlaskForm):
    cedula     = StringField('Cédula de identidad',
                             validators=[DataRequired(MSG_REQ), Length(6, 20, MSG_CED_LEN)])
    contrasena = PasswordField('Contraseña',
                               validators=[DataRequired(MSG_REQ)])
    submit     = SubmitField('Ingresar')


class RegistroForm(FlaskForm):
    cedula      = StringField('Cédula de identidad *',
                              validators=[DataRequired(MSG_REQ), Length(6, 20, MSG_CED_LEN)])
    nombre      = StringField('Nombre *',
                              validators=[DataRequired(MSG_REQ), Length(max=100, message=MSG_MAX100)])
    apellido    = StringField('Apellido *',
                              validators=[DataRequired(MSG_REQ), Length(max=100, message=MSG_MAX100)])
    correo      = StringField('Correo electrónico *',
                              validators=[DataRequired(MSG_REQ), validar_correo])
    contrasena  = PasswordField('Contraseña * (mín. 6 caracteres)',
                                validators=[DataRequired(MSG_REQ), Length(min=6, message=MSG_MIN6)])
    contrasena2 = PasswordField('Confirmar contraseña *',
                                validators=[DataRequired(MSG_REQ),
                                            EqualTo('contrasena', MSG_PASS_EQ)])
    rol = SelectField('Tipo de usuario *',
                      choices=[('Estudiante', 'Estudiante'), ('Profesor', 'Profesor')])
    # Campos de estudiante — sin validadores WTF (se validan manualmente en el route)
    carrera        = SelectField('Carrera', choices=CARRERAS, default='',
                                 validators=[])
    semestre       = SelectField('Semestre', choices=SEMESTRES, default='',
                                 validators=[])
    nombre_seccion = StringField('Sección (ej: D-51)')
    submit = SubmitField('Crear cuenta')


class RecuperarForm(FlaskForm):
    cedula = StringField('Cédula de identidad',
                         validators=[DataRequired(MSG_REQ)])
    submit = SubmitField('Enviar solicitud')
