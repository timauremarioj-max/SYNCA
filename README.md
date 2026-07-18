# SYNCA — Sistema Académico UNEFA

**Universidad Nacional Experimental Politécnica de la Fuerza Armada Nacional**  
**UNEFA Núcleo Falcón — Ingeniería de Sistemas — 5to Semestre — 2026**

Autores: Mario Timaure · Enmanuel Chirino · Jesús Robertiz

---

## Descripción

SYNCA es una plataforma web que centraliza la gestión académica de la UNEFA Núcleo Falcón. Permite a los **docentes** registrar asistencia y calificaciones, y a los **estudiantes** consultar su expediente académico en tiempo real.

---

## Tecnologías

- **Backend:** Python 3 · Flask · SQLAlchemy · Flask-Login · Flask-WTF
- **Frontend:** HTML5 · CSS3 · Jinja2
- **Base de datos:** SQLite (desarrollo)

---

## Ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Cargar datos de demostración (solo la primera vez)
python seed_db.py

# 3. Iniciar la aplicación
python run.py
```

Luego abrir: **http://localhost:5000**

---

## Estructura

```
synca/
├── app/
│   ├── __init__.py          # Fábrica de la aplicación
│   ├── config.py            # Configuración
│   ├── extensions.py        # SQLAlchemy, LoginManager, CSRF
│   ├── decorators.py        # @role_required
│   ├── models/models.py     # Modelos de BD
│   ├── auth/                # Login, logout, registro
│   ├── estudiante/          # Panel del estudiante
│   ├── profesor/            # Panel del docente
│   ├── main/                # Landing page
│   ├── static/css/          # Estilos
│   └── templates/           # Plantillas HTML
├── instance/                # Base de datos SQLite (generada al ejecutar)
├── run.py                   # Punto de entrada
├── seed_db.py               # Datos de demostración
└── requirements.txt
```

---

## Reglas de Negocio implementadas

| # | Regla |
|---|-------|
| RN-1 | ≥ 25% de inasistencias → alerta de riesgo académico |
| RN-2 | Notas en escala 0–20; promedio calculado automáticamente |
| RN-3 | Solo el docente de una sección puede registrar asistencia y notas |
| RN-4 | El estudiante solo puede consultar su propio expediente |
