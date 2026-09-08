"""Historical content repository"""
from typing import Any, Dict, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import cast, func

from app.extensions import db
from app.historical.models import HistoricalContent, LakeGeometry, Timeline


class HistoricalContentRepository:
    """Acceso a los artículos de la guía histórica."""

    @staticmethod
    def find_by_id(content_id: str) -> Optional[HistoricalContent]:
        return HistoricalContent.query.filter_by(id=content_id).first()

    @staticmethod
    def find_by_place(place_id: str) -> List[HistoricalContent]:
        return HistoricalContent.query.filter_by(place_id=place_id).order_by(
            HistoricalContent.sort_order
        ).all()

    @staticmethod
    def find_by_era(era: str) -> List[HistoricalContent]:
        return HistoricalContent.query.filter_by(era=era).order_by(
            HistoricalContent.sort_order
        ).all()

    @staticmethod
    def find_by_topic(topic: str) -> List[HistoricalContent]:
        """Artículos de un tema — la pestaña Topics."""
        return HistoricalContent.query.filter_by(topic=topic).order_by(
            HistoricalContent.sort_order
        ).all()

    @staticmethod
    def find_by_type(content_type: str) -> List[HistoricalContent]:
        return HistoricalContent.query.filter_by(content_type=content_type).all()

    @staticmethod
    def find_all() -> List[HistoricalContent]:
        return HistoricalContent.query.order_by(HistoricalContent.sort_order).all()

    @staticmethod
    def find_chronology(timeline_id: Optional[str] = None) -> List[HistoricalContent]:
        """Artículos en orden cronológico.

        Es lo que alimenta la pestaña Chronology y lo que hace que el botón
        "Next" pueda saber cuál es el siguiente.
        """
        query = HistoricalContent.query
        if timeline_id:
            query = query.filter(HistoricalContent.timeline_id == timeline_id)
        else:
            query = query.filter(HistoricalContent.timeline_id.isnot(None))

        return query.order_by(
            HistoricalContent.sort_order, HistoricalContent.created_at
        ).all()

    @staticmethod
    def find_next(content: HistoricalContent) -> Optional[HistoricalContent]:
        """El artículo siguiente dentro de la misma cronología."""
        if content.timeline_id is None:
            return None

        return HistoricalContent.query.filter(
            HistoricalContent.timeline_id == content.timeline_id,
            HistoricalContent.sort_order > (content.sort_order or 0),
        ).order_by(HistoricalContent.sort_order).first()

    @staticmethod
    def list_topics() -> List[Dict[str, Any]]:
        """Temas con cuántos artículos tiene cada uno, en UNA consulta."""
        filas = db.session.query(
            HistoricalContent.topic,
            func.count(HistoricalContent.id).label("total"),
        ).filter(
            HistoricalContent.topic.isnot(None)
        ).group_by(
            HistoricalContent.topic
        ).order_by(HistoricalContent.topic).all()

        return [{"topic": t, "count": n} for t, n in filas]

    @staticmethod
    def save(content: HistoricalContent) -> HistoricalContent:
        db.session.add(content)
        db.session.commit()
        return content

    @staticmethod
    def update(content_id: str, data: dict) -> Optional[HistoricalContent]:
        content = HistoricalContentRepository.find_by_id(content_id)
        if not content:
            return None

        for key, value in data.items():
            if hasattr(content, key):
                setattr(content, key, value)

        db.session.commit()
        return content


class TimelineRepository:
    """Repository for Timeline operations"""

    @staticmethod
    def find_all() -> List[Timeline]:
        return Timeline.query.order_by(Timeline.sort_order, Timeline.title).all()

    @staticmethod
    def find_by_id(timeline_id: str) -> Optional[Timeline]:
        return Timeline.query.filter_by(id=timeline_id).first()

    @staticmethod
    def save(timeline: Timeline) -> Timeline:
        db.session.add(timeline)
        db.session.commit()
        return timeline


class LakeGeometryRepository:
    """Consulta de los polígonos del lago."""

    @staticmethod
    def _query(year: Optional[int] = None):
        query = db.session.query(
            LakeGeometry.id,
            LakeGeometry.name,
            LakeGeometry.surface_type,
            LakeGeometry.year_estimate,
            LakeGeometry.tenochtitlan_name,
            LakeGeometry.description,
            # Convertir a GeoJSON en la base de datos evita traerse el WKB a
            # Python y volver a parsearlo.
            func.ST_AsGeoJSON(LakeGeometry.geom).label("geojson"),
        )
        if year is not None:
            query = query.filter(LakeGeometry.year_estimate == year)
        return query

    @staticmethod
    def find_in_bbox(
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        year: Optional[int] = None,
    ) -> List[Any]:
        """Polígonos que tocan el recuadro visible del mapa.

        Se recorta con ST_Intersects y no con "contenido en": un polígono que
        entra por una esquina del encuadre también hay que pintarlo.
        """
        caja = cast(
            func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326),
            Geography,
        )

        return LakeGeometryRepository._query(year).filter(
            func.ST_Intersects(LakeGeometry.geom, caja)
        ).all()

    @staticmethod
    def find_all(year: Optional[int] = None) -> List[Any]:
        """Todos los polígonos de una época, sin recorte de encuadre."""
        return LakeGeometryRepository._query(year).all()

    @staticmethod
    def available_years() -> List[int]:
        """Épocas con datos. Es lo que puede ofrecer el conmutador del mapa."""
        filas = db.session.query(LakeGeometry.year_estimate).filter(
            LakeGeometry.year_estimate.isnot(None)
        ).distinct().order_by(LakeGeometry.year_estimate).all()
        return [f[0] for f in filas]

    @staticmethod
    def save(lake_geometry: LakeGeometry) -> LakeGeometry:
        db.session.add(lake_geometry)
        db.session.commit()
        return lake_geometry
