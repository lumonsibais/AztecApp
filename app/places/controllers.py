"""Places API controllers.

Endpoints públicos: se pueden consultar sin token. Lo que cambia con la sesión
es CUÁNTO se ve —eso lo decide `current_has_access()` sobre el usuario
autenticado, nunca un parámetro del cliente— y si viaja el estado del corazón.
"""
from flask import current_app, jsonify, request

from app.middleware import (
    current_has_access,
    current_user_id,
    optional_token,
    token_required,
)
from app.places.services import PlaceService
from app.shared.constants import CURATIONS, DEFAULT_LIMIT, ERROR_MESSAGES, MAX_LIMIT
from app.shared.i18n import current_locale
from app.shared.utils import format_response


def _server_error(exc: Exception):
    current_app.logger.exception("Unhandled error in places controller: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


def _missing_coords():
    return jsonify(
        format_response(success=False, error="Missing latitude or longitude")
    ), 400


def _curation():
    """Filtro Must See / Quick Stops. Un valor desconocido se ignora."""
    valor = request.args.get("curation", type=str)
    return valor if valor in CURATIONS else None


class PlaceController:
    """Controller for place endpoints"""

    @staticmethod
    @optional_token
    def get_nearby_places():
        """Sitios cercanos, con distancia y ordenados por cercanía."""
        try:
            latitude = request.args.get("latitude", type=float)
            longitude = request.args.get("longitude", type=float)
            radius = request.args.get("radius", default=5, type=float)

            if latitude is None or longitude is None:
                return _missing_coords()

            places = PlaceService.get_nearby_places(
                latitude, longitude, radius,
                has_access=current_has_access(),
                locale=current_locale(),
                user_id=current_user_id(),
                curation=_curation(),
            )

            return jsonify(
                format_response(
                    success=True,
                    data={"places": places, "count": len(places)},
                )
            ), 200

        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_all_places():
        """Listado con paginación y filtro editorial."""
        try:
            page = max(request.args.get("page", default=1, type=int), 1)
            limit = min(
                request.args.get("limit", default=DEFAULT_LIMIT, type=int), MAX_LIMIT
            )

            result = PlaceService.get_all_places(
                page, limit,
                curation=_curation(),
                has_access=current_has_access(),
                locale=current_locale(),
                user_id=current_user_id(),
            )

            return jsonify(format_response(success=True, data=result)), 200

        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def get_saved_places(current_user):
        """La pestaña Saved."""
        try:
            places = PlaceService.get_saved_places(
                current_user,
                has_access=current_has_access(),
                locale=current_locale(),
            )
            return jsonify(
                format_response(
                    success=True,
                    data={"places": places, "count": len(places)},
                )
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_place_detail(place_id: str):
        """Ficha de un sitio. Acepta coordenadas para incluir la distancia."""
        try:
            place = PlaceService.get_place_details(
                place_id,
                has_access=current_has_access(),
                locale=current_locale(),
                user_id=current_user_id(),
                latitude=request.args.get("latitude", type=float),
                longitude=request.args.get("longitude", type=float),
            )

            if not place:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404

            return jsonify(format_response(success=True, data=place)), 200

        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def save_place(current_user, place_id: str):
        """Guarda un sitio (el corazón de la tarjeta)."""
        try:
            if not PlaceService.save_place(current_user, place_id):
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404

            return jsonify(format_response(success=True, message="Place saved")), 201
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def unsave_place(current_user, place_id: str):
        """Quita un sitio de guardados. Quitar algo que no estaba no es error."""
        try:
            PlaceService.unsave_place(current_user, place_id)
            return jsonify(
                format_response(success=True, message="Place removed from saved")
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_recommended_places():
        """Recomendaciones para la ubicación actual."""
        try:
            latitude = request.args.get("latitude", type=float)
            longitude = request.args.get("longitude", type=float)
            limit = min(
                request.args.get("limit", default=DEFAULT_LIMIT, type=int), MAX_LIMIT
            )

            if latitude is None or longitude is None:
                return _missing_coords()

            places = PlaceService.get_nearby_places(
                latitude, longitude, 10,
                has_access=current_has_access(),
                locale=current_locale(),
                user_id=current_user_id(),
                curation=_curation(),
            )[:limit]

            return jsonify(
                format_response(
                    success=True,
                    data={"places": places, "count": len(places)},
                )
            ), 200

        except Exception as e:
            return _server_error(e)
