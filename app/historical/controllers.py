"""Historical content controllers — la pestaña History."""
from flask import current_app, jsonify, request

from app.historical.services import (
    HistoricalContentService,
    LakeViewService,
    TimelineService,
)
from app.middleware import (
    current_has_access,
    current_user_id,
    optional_token,
    token_required,
)
from app.shared.constants import ERROR_MESSAGES
from app.shared.i18n import current_locale
from app.shared.utils import format_response


def _server_error(exc: Exception):
    current_app.logger.exception("Unhandled error in historical controller: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


def _contexto():
    """Los tres datos que necesita cualquier lectura de contenido."""
    return {
        "has_access": current_has_access(),
        "locale": current_locale(),
        "user_id": current_user_id(),
    }


class HistoricalContentController:
    """Controller for historical content"""

    @staticmethod
    @optional_token
    def get_all_content():
        try:
            contenido = HistoricalContentService.get_all_content(
                request.args.get("type", default=None, type=str), **_contexto()
            )
            return jsonify(
                format_response(success=True, data={"content": contenido})
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_chronology():
        """Pestaña Chronology: los artículos en orden."""
        try:
            contenido = HistoricalContentService.get_chronology(
                request.args.get("timelineId", default=None, type=str), **_contexto()
            )
            return jsonify(
                format_response(success=True, data={"content": contenido})
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    def get_topics():
        """Pestaña Topics: los temas con su número de artículos."""
        try:
            return jsonify(
                format_response(
                    success=True,
                    data={"topics": HistoricalContentService.get_topics()},
                )
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_content_by_topic():
        try:
            topic = request.args.get("topic", type=str)
            if not topic:
                return jsonify(
                    format_response(success=False, error="Topic parameter required")
                ), 400

            contenido = HistoricalContentService.get_content_by_topic(
                topic, **_contexto()
            )
            return jsonify(
                format_response(success=True, data={"content": contenido})
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_content_by_place(place_id: str):
        try:
            contenido = HistoricalContentService.get_content_by_place(
                place_id, **_contexto()
            )
            return jsonify(
                format_response(success=True, data={"content": contenido})
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_content_by_era():
        try:
            era = request.args.get("era", type=str)
            if not era:
                return jsonify(
                    format_response(success=False, error="Era parameter required")
                ), 400

            contenido = HistoricalContentService.get_content_by_era(era, **_contexto())
            return jsonify(
                format_response(success=True, data={"content": contenido})
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @optional_token
    def get_content_detail(content_id: str):
        try:
            contenido = HistoricalContentService.get_content_detail(
                content_id, **_contexto()
            )
            if not contenido:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404

            return jsonify(format_response(success=True, data=contenido)), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def mark_read(current_user, content_id: str):
        """El botón "Mark read" de la guía."""
        try:
            if not HistoricalContentService.mark_read(current_user, content_id):
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404

            return jsonify(format_response(success=True, message="Marked as read")), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def unmark_read(current_user, content_id: str):
        try:
            HistoricalContentService.unmark_read(current_user, content_id)
            return jsonify(
                format_response(success=True, message="Marked as unread")
            ), 200
        except Exception as e:
            return _server_error(e)


class TimelineController:
    """Controller for timelines"""

    @staticmethod
    def get_all_timelines():
        try:
            return jsonify(
                format_response(
                    success=True,
                    data={"timelines": TimelineService.get_all_timelines()},
                )
            ), 200
        except Exception as e:
            return _server_error(e)


class LakeViewController:
    """Overlay del lago."""

    @staticmethod
    def _parse_bbox(crudo: str):
        """'minLon,minLat,maxLon,maxLat' -> tupla de cuatro floats.

        Devuelve None si el formato no cuadra, para que el controller conteste
        400 en vez de reventar.
        """
        partes = [p.strip() for p in crudo.split(",")]
        if len(partes) != 4:
            return None
        try:
            min_lon, min_lat, max_lon, max_lat = (float(p) for p in partes)
        except ValueError:
            return None
        if min_lon > max_lon or min_lat > max_lat:
            return None
        return (min_lon, min_lat, max_lon, max_lat)

    @staticmethod
    def get_lake_data():
        """Overlay del lago como GeoJSON.

        `bbox` recorta al encuadre visible; sin él va el overlay completo.
        `year` es la época del conmutador del mapa: con 1500 se pinta el lago,
        con 2026 no hay nada que superponer porque la ciudad ya la pinta el
        mapa base. `availableYears` en la respuesta dice qué épocas hay.
        """
        try:
            crudo = request.args.get("bbox", type=str)
            year = request.args.get("year", type=int)

            bbox = None
            if crudo:
                bbox = LakeViewController._parse_bbox(crudo)
                if bbox is None:
                    return jsonify(
                        format_response(
                            success=False,
                            error="bbox must be minLon,minLat,maxLon,maxLat",
                        )
                    ), 400

            overlay = LakeViewService.get_lake_overlay(bbox, year)
            return jsonify(format_response(success=True, data=overlay)), 200
        except Exception as e:
            return _server_error(e)
