from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(rol):
    """Restringe el acceso a un panel según el rol del usuario (Reglas de Negocio 3 y 4,
    Requerimiento No Funcional 3: Seguridad)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.rol != rol:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
