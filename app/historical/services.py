"""Historical content service — la guía histórica (pestaña History)."""
import json
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func

from app.historical.models import HistoricalContent, LakeGeometry
from app.historical.repositories import (
    HistoricalContentRepository,
    LakeGeometryRepository,
    TimelineRepository,
)
from app.shared.access import can_access_resource
from app.shared.constants import SURFACE_WATER, SURFACES
from app.shared.i18n import DEFAULT_LOCALE, apply_translation, apply_translations
from app.shared.translations import ENTITY_HISTORICAL
from app.users.repositories import ContentReadRepository

CAMPOS_TRADUCIBLES = {
    "title": "title",
    "description": "description",
    "topic": "topic",
    "era": "era",
    "date_description": "dateDescription",
}


def _leidos(user_id: Optional[str], content_ids: List[str]) -> Optional[Set[str]]:
    """Qué artículos ya leyó, en UNA consulta. None si es anónimo."""
    if not user_id:
        return None
    if not content_ids:
        return set()
    return ContentReadRepository.read_ids(user_id, content_ids)


def serialize(
    content: HistoricalContent,
    has_access: bool,
    leidos: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    return content.to_dict(
        unlocked=can_access_resource(has_access, content),
        is_read=(content.id in leidos) if leidos is not None else None,
    )


def _serializar_lista(
    contenidos: List[HistoricalContent],
    has_access: bool,
    locale: str,
    user_id: Optional[str],
) -> List[Dict[str, Any]]:
    leidos = _leidos(user_id, [c.id for c in contenidos])
    items = [serialize(c, has_access, leidos) for c in contenidos]
    return apply_translations(items, ENTITY_HISTORICAL, locale, CAMPOS_TRADUCIBLES)


class HistoricalContentService:
    """Artículos de la guía histórica."""

    @staticmethod
    def get_content_by_place(
        place_id: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _serializar_lista(
            HistoricalContentRepository.find_by_place(place_id),
            has_access, locale, user_id,
        )

    @staticmethod
    def get_content_by_era(
        era: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _serializar_lista(
            HistoricalContentRepository.find_by_era(era),
            has_access, locale, user_id,
        )

    @staticmethod
    def get_all_content(
        content_type: Optional[str] = None,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if content_type:
            contenidos = HistoricalContentRepository.find_by_type(content_type)
        else:
            contenidos = HistoricalContentRepository.find_all()

        return _serializar_lista(contenidos, has_access, locale, user_id)

    @staticmethod
    def get_chronology(
        timeline_id: Optional[str] = None,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """La pestaña Chronology: artículos en orden."""
        return _serializar_lista(
            HistoricalContentRepository.find_chronology(timeline_id),
            has_access, locale, user_id,
        )

    @staticmethod
    def get_topics() -> List[Dict[str, Any]]:
        """La pestaña Topics: temas con su número de artículos."""
        return HistoricalContentRepository.list_topics()

    @staticmethod
    def get_content_by_topic(
        topic: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _serializar_lista(
            HistoricalContentRepository.find_by_topic(topic),
            has_access, locale, user_id,
        )

    @staticmethod
    def get_content_detail(
        content_id: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Artículo completo.

        Si la cuenta no tiene el desbloqueo se devuelve la ficha sin cuerpo: el
        cliente sabe que existe, de qué va y cuánto se tarda en leerlo, pero no
        recibe el texto ni el audio.
        """
        content = HistoricalContentRepository.find_by_id(content_id)
        if not content:
            return None

        unlocked = can_access_resource(has_access, content)
        leidos = _leidos(user_id, [content.id])
        data = serialize(content, has_access, leidos)

        siguiente = HistoricalContentRepository.find_next(content)
        data["nextContentId"] = siguiente.id if siguiente else None

        campos = dict(CAMPOS_TRADUCIBLES)

        if unlocked:
            if content.content_type == "text":
                data["content"] = content.text_content
                campos["text_content"] = "content"
            elif content.content_type == "audio":
                data["audioUrl"] = content.audio_url
            elif content.content_type == "video":
                data["videoUrl"] = content.video_url

            if content.sources:
                data["sources"] = content.sources

        return apply_translation(data, ENTITY_HISTORICAL, locale, campos)

    @staticmethod
    def mark_read(user_id: str, content_id: str) -> bool:
        """Marca un artículo como leído. Idempotente."""
        if HistoricalContentRepository.find_by_id(content_id) is None:
            return False
        ContentReadRepository.mark(user_id, content_id)
        return True

    @staticmethod
    def unmark_read(user_id: str, content_id: str) -> bool:
        return ContentReadRepository.unmark(user_id, content_id)


class TimelineService:
    """Cronologías."""

    @staticmethod
    def get_all_timelines() -> List[Dict[str, Any]]:
        return [t.to_dict() for t in TimelineRepository.find_all()]


class LakeViewService:
    """Overlay histórico del lago de Tenochtitlan.

    Devuelve GeoJSON estándar (FeatureCollection) para que el cliente lo pinte
    sin transformarlo: es lo que esperan flutter_map y google_maps_flutter.
    """

    @staticmethod
    def _feature(fila) -> Dict[str, Any]:
        return {
            "type": "Feature",
            "id": fila.id,
            # ST_AsGeoJSON devuelve la geometría como texto; se parsea aquí
            # para que viaje como objeto y no como cadena escapada.
            "geometry": json.loads(fila.geojson),
            "properties": {
                "name": fila.name,
                # Con qué color se pinta. Sin esto la app tendría que deducirlo
                # del nombre del polígono.
                "surfaceType": fila.surface_type,
                "yearEstimate": fila.year_estimate,
                "tenochtitlanName": fila.tenochtitlan_name,
                "description": fila.description,
            },
        }

    @staticmethod
    def get_lake_overlay(
        bbox: Optional[tuple] = None, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """FeatureCollection del lago, por época y recortada al encuadre.

        `bbox` es (min_lon, min_lat, max_lon, max_lat).
        `year` es la época del conmutador del mapa: 1500 pinta el lago, 2026 no
        devuelve nada porque la ciudad actual ya la pinta el mapa base.
        """
        if bbox:
            filas = LakeGeometryRepository.find_in_bbox(*bbox, year=year)
        else:
            filas = LakeGeometryRepository.find_all(year=year)

        return {
            "type": "FeatureCollection",
            "features": [LakeViewService._feature(f) for f in filas],
            "availableYears": LakeGeometryRepository.available_years(),
        }

    @staticmethod
    def create_lake_geometry(
        name: str,
        geojson_polygon: Dict[str, Any],
        year_estimate: int = None,
        surface_type: str = SURFACE_WATER,
        tenochtitlan_name: str = None,
        description: str = None,
    ) -> LakeGeometry:
        """Crea un polígono a partir de una geometría GeoJSON."""
        import uuid

        if surface_type not in SURFACES:
            raise ValueError(f"surface_type inválido: {surface_type!r}")

        geometria = LakeGeometry(
            id=str(uuid.uuid4()),
            name=name,
            geom=func.ST_GeomFromGeoJSON(json.dumps(geojson_polygon)),
            year_estimate=year_estimate,
            surface_type=surface_type,
            tenochtitlan_name=tenochtitlan_name,
            description=description,
        )

        return LakeGeometryRepository.save(geometria)
