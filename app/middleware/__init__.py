"""Middleware for authentication and error handling"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.shared.constants import ERROR_MESSAGES
from app.shared.utils import format_response


def token_required(fn):
    """Decorator to require JWT token for endpoints"""
    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user = get_jwt_identity()
            kwargs['current_user'] = current_user
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify(
                format_response(
                    success=False,
                    error=ERROR_MESSAGES["UNAUTHORIZED"]
                )
            ), 401
    return decorated


def location_permission_required(fn):
    """Decorator to require location permission grant"""
    @wraps(fn)
    def decorated(*args, **kwargs):
        # This would typically check user's location permission status
        # from the database
        return fn(*args, **kwargs)
    return decorated
