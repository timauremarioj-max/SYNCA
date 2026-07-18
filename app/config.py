import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'synca-dev-key-unefa-falcon-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE    = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB

    # CSRF — sin límite de tiempo para evitar expiración en localhost
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False

    # Reglas de negocio
    LIMITE_INASISTENCIAS_PORCENTAJE = 25
    NOTA_MINIMA = 0
    NOTA_MAXIMA = 20

    @staticmethod
    def _database_url():
        url = os.getenv('DATABASE_URL', '').strip()
        if not url:
            sqlite_path = os.path.join(BASE_DIR, 'instance', 'synca_dev.db')
            return f'sqlite:///{sqlite_path}'
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = Config._database_url()


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = Config._database_url()


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
}
