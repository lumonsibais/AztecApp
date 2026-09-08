"""Users controllers"""
from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token
from marshmallow import ValidationError

from app.middleware import any_token_required, refresh_token_required, token_required
from app.shared.constants import ERROR_MESSAGES
from app.shared.schemas import (
    location_permission_schema,
    user_login_schema,
    user_profile_update_schema,
    user_register_schema,
)
from app.shared.utils import format_response
from app.users.services import UserService


def _validation_error(err: ValidationError):
    """400 que dice QUÉ campo sobra o falta, en vez de un error genérico."""
    return jsonify(
        format_response(
            success=False,
            error=ERROR_MESSAGES["VALIDATION_ERROR"],
            details=err.messages,
        )
    ), 400


def _server_error(exc: Exception):
    """500 sin filtrar el mensaje interno al cliente. La traza va al log."""
    current_app.logger.exception("Unhandled error in users controller: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


def _issue_tokens(user):
    return {
        "user": user.to_dict(),
        "accessToken": create_access_token(identity=user.id),
        "refreshToken": create_refresh_token(identity=user.id),
    }


class UserController:
    """Controller for user endpoints"""

    @staticmethod
    def register():
        """Register a new user"""
        try:
            data = user_register_schema.load(request.get_json(silent=True) or {})

            user = UserService.register_user(
                data["email"],
                data["password"],
                data.get("first_name"),
                data.get("last_name"),
            )
            if not user:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["EMAIL_EXISTS"])
                ), 409

            return jsonify(
                format_response(
                    success=True,
                    message="User registered successfully",
                    data=_issue_tokens(user),
                )
            ), 201

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    def login():
        """Login user"""
        try:
            data = user_login_schema.load(request.get_json(silent=True) or {})

            user = UserService.verify_credentials(data["email"], data["password"])
            if not user:
                # Mismo 401 para credenciales malas y para cuenta desactivada:
                # distinguirlos revela qué correos existen en la base.
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["INVALID_CREDENTIALS"]
                    )
                ), 401

            return jsonify(
                format_response(
                    success=True, message="Login successful", data=_issue_tokens(user)
                )
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @refresh_token_required
    def refresh(current_user):
        """Canjear un refresh token por un access token nuevo."""
        try:
            return jsonify(
                format_response(
                    success=True,
                    data={"accessToken": create_access_token(identity=current_user)},
                )
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @any_token_required
    def logout(jwt_payload):
        """Revoca el token recibido (access o refresh)."""
        try:
            UserService.revoke_token(jwt_payload)
            return jsonify(format_response(success=True, message="Token revoked")), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def get_profile(current_user):
        """Get user profile"""
        try:
            profile = UserService.get_user_profile(current_user)
            if not profile:
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"]
                    )
                ), 404

            return jsonify(format_response(success=True, data=profile)), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def update_profile(current_user):
        """Update user profile.

        El schema es una whitelist estricta: mandar subscription_tier,
        is_verified o cualquier otro campo no editable responde 400 nombrándolo
        en vez de escribirlo en el modelo.
        """
        try:
            data = user_profile_update_schema.load(request.get_json(silent=True) or {})

            user = UserService.update_user_profile(current_user, data)
            if not user:
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"]
                    )
                ), 404

            return jsonify(
                format_response(
                    success=True, message="Profile updated", data=user.to_dict()
                )
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def handle_location_permission(current_user):
        """Handle location permission request"""
        try:
            data = location_permission_schema.load(request.get_json(silent=True) or {})

            ok = UserService.handle_location_permission(
                current_user, data["response"], data.get("context")
            )
            if not ok:
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"]
                    )
                ), 404

            return jsonify(
                format_response(success=True, message="Location permission recorded")
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)
