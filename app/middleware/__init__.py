"""Middleware de autenticación y autorización.

Reglas que fija este módulo:

1. El acceso al contenido de pago sale SIEMPRE del usuario autenticado, nunca
   de un parámetro que mande el cliente. Antes, `?subscription=vip` en places y
   tours abría el contenido de pago sin token.
2. La verificación del token va dentro del try; la llamada al handler, fuera.
   Envolver el handler hacía que cualquier 500 se reportara como 401.
3. El usuario se carga una vez por petición y queda en `flask.g`, de modo que
   un token revocado o una cuenta desactivada se detectan al momento y no
   dependen de lo que dijera el token cuando se emitió.
"""
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.shared.constants import ERROR_MESSAGES
from app.shared.utils import format_response


def _error(key: str, status: int):
    return jsonify(format_response(success=False, error=ERROR_MESSAGES[key])), status


def _load_user():
    """Carga el usuario del token en g.current_user. Devuelve el usuario o None."""
    from app.users.repositories import UserRepository

    identity = get_jwt_identity()
    user = UserRepository.find_by_id(identity) if identity else None
    g.current_user = user
    return user


def current_user():
    """Usuario autenticado de esta petición, o None si es anónima."""
    return getattr(g, "current_user", None)


def current_user_id():
    """Id del usuario autenticado, o None si la petición es anónima."""
    usuario = current_user()
    return usuario.id if usuario else None


def current_has_access() -> bool:
    """¿Tiene desbloqueado el contenido de pago quien hace la petición?

    Anónimo => no. Es un permiso de la cuenta, no un nivel: el producto vende
    un único desbloqueo y no caduca.
    """
    user = current_user()
    return bool(user.has_full_access) if user else False


def token_required(fn):
    """Exige un access token válido de un usuario activo.

    Inyecta `current_user` (el id, por compatibilidad con los services) y deja
    el objeto User completo en `g.current_user`.
    """

    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return _error("UNAUTHORIZED", 401)

        user = _load_user()
        if user is None:
            return _error("USER_NOT_FOUND", 404)
        if not user.is_active:
            return _error("ACCOUNT_DISABLED", 403)

        kwargs["current_user"] = user.id
        return fn(*args, **kwargs)

    return decorated


def refresh_token_required(fn):
    """Igual que token_required pero exigiendo un refresh token."""

    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request(refresh=True)
        except Exception:
            return _error("UNAUTHORIZED", 401)

        user = _load_user()
        if user is None:
            return _error("USER_NOT_FOUND", 404)
        if not user.is_active:
            return _error("ACCOUNT_DISABLED", 403)

        kwargs["current_user"] = user.id
        return fn(*args, **kwargs)

    return decorated


def any_token_required(fn):
    """Acepta access o refresh. Lo usa /logout, que revoca el que reciba."""

    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request(verify_type=False)
        except Exception:
            return _error("UNAUTHORIZED", 401)

        _load_user()
        kwargs["jwt_payload"] = get_jwt()
        return fn(*args, **kwargs)

    return decorated


def optional_token(fn):
    """Para endpoints públicos que muestran más contenido si hay sesión.

    Sin token, o con un token inválido, la petición sigue como anónima y
    `current_has_access()` devuelve False. Nunca responde 401.
    """

    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
            user = _load_user()
            if user is not None and not user.is_active:
                g.current_user = None
        except Exception:
            g.current_user = None

        return fn(*args, **kwargs)

    return decorated


def requires_full_access(fn):
    """Exige el desbloqueo completo sobre un endpoint entero.

    Para contenido que se filtra pieza a pieza está `can_access` en el service;
    esto es para endpoints que son de pago enteros.
    """

    @wraps(fn)
    @token_required
    def decorated(*args, **kwargs):
        if not current_has_access():
            return _error("ACCESS_REQUIRED", 403)
        return fn(*args, **kwargs)

    return decorated


def location_permission_required(fn):
    """Exige que el usuario haya concedido permiso de ubicación."""

    @wraps(fn)
    @token_required
    def decorated(*args, **kwargs):
        user = current_user()
        if user is None or user.location_permission_status != "granted":
            return _error("LOCATION_PERMISSION_DENIED", 403)
        return fn(*args, **kwargs)

    return decorated
