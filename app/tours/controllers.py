"""Tours controllers"""
from flask import current_app, jsonify, request
from marshmallow import ValidationError

from app.middleware import current_has_access, optional_token, token_required
from app.shared.i18n import current_locale
from app.shared.constants import DEFAULT_LIMIT, ERROR_MESSAGES, MAX_LIMIT
from app.shared.schemas import tour_complete_schema, tour_progress_update_schema
from app.shared.utils import format_response
from app.tours.services import TourService


def _validation_error(err: ValidationError):
    return jsonify(
        format_response(
            success=False,
            error=ERROR_MESSAGES["VALIDATION_ERROR"],
            details=err.messages,
        )
    ), 400


def _server_error(exc: Exception):
    current_app.logger.exception("Unhandled error in tours controller: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


def _not_found():
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
    ), 404


class TourController:
    """Controller for tour endpoints"""

    @staticmethod
    def get_free_tours():
        """Get free tours available to all users"""
        try:
            return jsonify(
                format_response(
                    success=True, data={"tours": TourService.get_free_tours()}
                )
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_all_tours():
        """Get all available tours"""
        try:
            page = max(request.args.get("page", default=1, type=int), 1)
            limit = min(
                request.args.get("limit", default=DEFAULT_LIMIT, type=int), MAX_LIMIT
            )

            result = TourService.get_all_tours(
                page, limit, current_has_access(), current_locale()
            )
            return jsonify(format_response(success=True, data=result)), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_tour_details(tour_id: str):
        """Get detailed information about a tour"""
        try:
            tour = TourService.get_tour_details(
                tour_id, current_has_access(), current_locale()
            )
            if not tour:
                return _not_found()

            return jsonify(format_response(success=True, data=tour)), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def start_tour(current_user, tour_id: str):
        """Start a tour"""
        try:
            progress = TourService.start_tour(tour_id, current_user, current_has_access())
            if not progress:
                return _not_found()

            return jsonify(
                format_response(
                    success=True,
                    message="Tour started successfully",
                    data=progress.to_dict(),
                )
            ), 201

        except PermissionError:
            return jsonify(
                format_response(
                    success=False, error=ERROR_MESSAGES["ACCESS_REQUIRED"]
                )
            ), 403
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def update_tour_progress(current_user, tour_id: str):
        """Update progress in a tour.

        El schema deja pasar solo el avance que reporta el cliente. Cerrar un
        tour pasa por /complete, no por un PUT con is_completed.
        """
        try:
            data = tour_progress_update_schema.load(request.get_json(silent=True) or {})

            progress = TourService.update_tour_progress(tour_id, current_user, data)
            if not progress:
                return _not_found()

            return jsonify(
                format_response(success=True, data=progress.to_dict())
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def complete_tour(current_user, tour_id: str):
        """Mark tour as completed"""
        try:
            data = tour_complete_schema.load(request.get_json(silent=True) or {})

            progress = TourService.complete_tour(
                tour_id, current_user, data.get("rating"), data.get("notes")
            )
            if not progress:
                return _not_found()

            return jsonify(
                format_response(
                    success=True,
                    message="Tour completed!",
                    data=progress.to_dict(),
                )
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def get_user_tours(current_user):
        """Get all tours started by user"""
        try:
            tours = TourService.get_user_tours(
                current_user, current_has_access(), current_locale()
            )
            return jsonify(format_response(success=True, data={"tours": tours})), 200
        except Exception as e:
            return _server_error(e)
