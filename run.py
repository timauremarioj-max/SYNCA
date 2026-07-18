"""
SYNCA - Sistema Académico UNEFA Núcleo Falcón
----------------------------------------------
Ejecución:   python run.py
La aplicación crea y migra la base de datos automáticamente.

IMPORTANTE: este archivo debe ejecutarse desde la carpeta donde
está guardado. Si VS Code muestra "no se encontró la ruta" o
"can't open file 'run.py'", significa que la terminal NO está
ubicada dentro de la carpeta del proyecto (la que contiene este
mismo archivo run.py, la carpeta app/, etc).

Solución rápida en VS Code:
  1. Menú Archivo → Abrir carpeta... → seleccionar la carpeta
     que contiene este run.py (NO una carpeta superior).
  2. Abrir una terminal NUEVA (Terminal → Nueva terminal).
     VS Code la ubicará automáticamente en la carpeta correcta.
  3. Ejecutar:  python run.py
"""
import os
import sys

# ── Verificación de directorio de trabajo ─────────────────────────────────
# Si el usuario ejecuta "python run.py" desde una carpeta distinta a la
# que contiene este archivo, mostramos un mensaje claro en español en
# lugar de un traceback confuso.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.abspath(os.getcwd()) != _THIS_DIR:
    # No es un error fatal: cambiamos el directorio de trabajo nosotros
    # mismos para que el programa funcione igual, pero avisamos al usuario.
    print()
    print("  ⚠  Aviso: la terminal no estaba ubicada en la carpeta del proyecto.")
    print(f"     Carpeta detectada de run.py:  {_THIS_DIR}")
    print(f"     Carpeta actual de la terminal: {os.getcwd()}")
    print("     SYNCA se ajustará automáticamente para continuar.")
    print()
    os.chdir(_THIS_DIR)
    sys.path.insert(0, _THIS_DIR)

from dotenv import load_dotenv
load_dotenv(override=True)

try:
    from app import create_app
    from app.extensions import db
except ModuleNotFoundError as e:
    print()
    print("  ✘  ERROR: no se pudo importar la aplicación Flask.")
    print(f"     Detalle: {e}")
    print()
    print("  Posibles causas:")
    print("    1. Faltan las dependencias. Ejecute primero:")
    print("         pip install -r requirements.txt")
    print("    2. La carpeta 'app/' no está junto a este run.py.")
    print(f"       Carpeta donde se buscó 'app/': {_THIS_DIR}")
    print()
    sys.exit(1)

app = create_app(os.getenv('FLASK_ENV', 'development'))


def _auto_setup():
    """Crea tablas y aplica migraciones. Seguro de ejecutar múltiples veces."""
    with app.app_context():
        db.create_all()          # crea tablas que faltan, no borra las existentes

        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if not db_url.startswith('sqlite:///'):
            return               # PostgreSQL usa Flask-Migrate

        import sqlite3
        db_path = db_url.replace('sqlite:///', '')
        if not os.path.isfile(db_path):
            return

        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()

        # ── tabla usuarios ────────────────────────────────────────────────
        cur.execute("PRAGMA table_info(usuarios)")
        cols = [r[1] for r in cur.fetchall()]
        for col, defn in [
            ('foto_perfil',     'VARCHAR(256)'),
            ('email_confirmed', 'INTEGER DEFAULT 1'),
        ]:
            if col not in cols:
                cur.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {defn}")
        conn.commit()

        # ── tabla estudiantes ────────────────────────────────────────────
        cur.execute("PRAGMA table_info(estudiantes)")
        cols = [r[1] for r in cur.fetchall()]
        if 'nombre_seccion' not in cols:
            cur.execute("ALTER TABLE estudiantes ADD COLUMN nombre_seccion VARCHAR(20) DEFAULT ''")
            conn.commit()

        # ── tabla secciones ──────────────────────────────────────────────
        cur.execute("PRAGMA table_info(secciones)")
        cols = [r[1] for r in cur.fetchall()]
        for col, defn in [
            ('materia_nombre_libre', 'VARCHAR(150)'),
            ('aula',                'VARCHAR(50) DEFAULT ""'),
            ('dia_semana',          'VARCHAR(15) DEFAULT ""'),
        ]:
            if col not in cols:
                cur.execute(f"ALTER TABLE secciones ADD COLUMN {col} {defn}")
        conn.commit()

        # ── tabla agenda_personal ────────────────────────────────────────
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agenda_personal'")
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE agenda_personal (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id),
                    titulo        VARCHAR(200) NOT NULL,
                    descripcion   TEXT,
                    fecha         DATE,
                    tipo          VARCHAR(30) DEFAULT 'recordatorio',
                    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        # ── tabla horario_personal ───────────────────────────────────────
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='horario_personal'")
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE horario_personal (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
                    materia     VARCHAR(150) NOT NULL,
                    dia_semana  VARCHAR(15) NOT NULL,
                    hora_inicio VARCHAR(5) NOT NULL,
                    hora_fin    VARCHAR(5) NOT NULL,
                    seccion     VARCHAR(20) DEFAULT '',
                    aula        VARCHAR(50) DEFAULT '',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()


        # ── tabla evaluaciones (módulo de calificaciones v2) ─────────────────
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evaluaciones'")
        if not cur.fetchone():
            cur.execute("""
                CREATE TABLE evaluaciones (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    inscripcion_id INTEGER NOT NULL REFERENCES inscripciones(id),
                    corte          INTEGER NOT NULL CHECK(corte BETWEEN 1 AND 4),
                    nombre         VARCHAR(150) NOT NULL,
                    porcentaje     NUMERIC(5,2) NOT NULL,
                    nota_obtenida  NUMERIC(4,2) NOT NULL,
                    aporte         NUMERIC(5,4) NOT NULL DEFAULT 0,
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        conn.close()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   SYNCA · UNEFA Núcleo Falcón            ║")
    print("  ║   Sistema Académico — Ingeniería         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  📁 Carpeta del proyecto: {_THIS_DIR}")
    print("  ▶  Inicializando base de datos...")
    try:
        _auto_setup()
        print("  ✔  Base de datos lista.")
    except Exception as e:
        print(f"  ✘  Error al inicializar la BD: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    print(f"  ✔  Servidor en http://localhost:{port}")
    print("  ✔  Presiona Ctrl+C para detener.")
    print()
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False),
        use_reloader=False
    )
