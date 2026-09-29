"""Escritura del catálogo.

Un detalle que recorre todo el archivo: el idioma base (inglés) vive en las
columnas del modelo y los demás en la tabla `translations`. Quien carga
contenido no debería tener que saber eso, así que estos servicios reciben un
único diccionario con `translations` dentro y reparten ellos.
"""
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from app.extensions import db
from app.historical.models import HistoricalContent, LakeGeometry
from app.places.models import Place
from app.places.repositories import PlaceRepository
from app.shared.translations import (
    ENTITY_HISTORICAL,
    ENTITY_PLACE,
    ENTITY_TOUR,
)
from app.shared.translations_repository import TranslationRepository
from app.tours.models import Tour, TourStop
from app.tours.repositories import TourRepository


class YaExiste(Exception):
    """El id propuesto ya está en uso."""


class NoExiste(Exception):
    """No hay nada con ese id."""


class ReferenciaRota(Exception):
    """Apunta a algo que no existe: un tour a un sitio, un artículo a un tour."""


def _repartir(datos: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Dict]]:
    """Separa las columnas del modelo de las traducciones."""
    copia = dict(datos)
    traducciones = copia.pop("translations", {}) or {}
    return copia, traducciones


def _guardar_traducciones(entidad: str, entidad_id: str, traducciones: Dict[str, Dict]):
    for locale, campos in traducciones.items():
        for campo, valor in campos.items():
            TranslationRepository.upsert(entidad, entidad_id, locale, campo, valor)


class AdminPlaceService:

    @staticmethod
    def crear(datos: Dict[str, Any]) -> Place:
        campos, traducciones = _repartir(datos)

        if Place.query.filter_by(id=campos["id"]).first():
            raise YaExiste(campos["id"])

        place = Place(**campos)
        db.session.add(place)
        db.session.commit()

        _guardar_traducciones(ENTITY_PLACE, place.id, traducciones)
        return place

    @staticmethod
    def actualizar(place_id: str, datos: Dict[str, Any]) -> Place:
        # incluir_borradores: editar algo que todavía no está publicado es el
        # caso normal mientras se carga el catálogo, no la excepción.
        place = PlaceRepository.find_by_id(place_id, incluir_borradores=True)
        if place is None:
            raise NoExiste(place_id)

        campos, traducciones = _repartir(datos)
        campos.pop("id", None)

        for campo, valor in campos.items():
            setattr(place, campo, valor)

        db.session.commit()
        _guardar_traducciones(ENTITY_PLACE, place.id, traducciones)
        return place

    @staticmethod
    def listar(incluir_borradores: bool = True) -> List[Place]:
        """Para la administración: por defecto SÍ trae los borradores.

        Es la vista contraria a la de la app, y con intención: lo primero que
        necesita quien carga contenido es ver lo que tiene a medias.
        """
        consulta = Place.query if incluir_borradores else PlaceRepository.publicos()
        return consulta.order_by(Place.is_published, Place.name).all()


class AdminTourService:

    @staticmethod
    def _validar_paradas(paradas: List[Dict[str, Any]]):
        """Que los sitios existan antes de montar el recorrido.

        Sin esto la base lanzaría un error de clave foránea, que llega al
        editor como un 500 sin explicación.
        """
        for parada in paradas:
            if not Place.query.filter_by(id=parada["place_id"]).first():
                raise ReferenciaRota(
                    f"El sitio '{parada['place_id']}' no existe")

    @staticmethod
    def _reemplazar_paradas(tour: Tour, paradas: List[Dict[str, Any]]):
        """Las paradas se mandan enteras y sustituyen a las anteriores.

        Es más simple y más predecible que un parcheo por parada: quien edita
        un recorrido lo tiene delante completo, y así no existen los estados
        intermedios en los que el tour queda con dos paradas en la posición 3.
        """
        import uuid

        AdminTourService._validar_paradas(paradas)

        # Se borran dentro de la misma transacción que las nuevas: si algo
        # falla al insertar, el tour no se queda sin recorrido.
        TourStop.query.filter_by(tour_id=tour.id).delete()
        db.session.flush()

        for parada in paradas:
            db.session.add(TourStop(id=str(uuid.uuid4()), tour_id=tour.id, **parada))

    @staticmethod
    def crear(datos: Dict[str, Any]) -> Tour:
        campos, traducciones = _repartir(datos)
        paradas = campos.pop("stops", None)

        if Tour.query.filter_by(id=campos["id"]).first():
            raise YaExiste(campos["id"])

        tour = Tour(**campos)
        db.session.add(tour)
        db.session.flush()

        if paradas:
            AdminTourService._reemplazar_paradas(tour, paradas)

        db.session.commit()
        _guardar_traducciones(ENTITY_TOUR, tour.id, traducciones)
        return tour

    @staticmethod
    def actualizar(tour_id: str, datos: Dict[str, Any]) -> Tour:
        tour = TourRepository.find_by_id(tour_id)
        if tour is None:
            raise NoExiste(tour_id)

        campos, traducciones = _repartir(datos)
        campos.pop("id", None)
        paradas = campos.pop("stops", None)

        for campo, valor in campos.items():
            setattr(tour, campo, valor)

        # `is not None` y no un simple `if`: mandar una lista vacía es pedir
        # que el tour se quede sin paradas, y eso es distinto de no mencionarlas.
        if paradas is not None:
            AdminTourService._reemplazar_paradas(tour, paradas)

        db.session.commit()
        _guardar_traducciones(ENTITY_TOUR, tour.id, traducciones)
        return tour

    @staticmethod
    def listar() -> List[Tour]:
        return Tour.query.order_by(Tour.status, Tour.title).all()


class AdminContenidoService:

    @staticmethod
    def _validar_referencias(campos: Dict[str, Any]):
        place_id = campos.get("place_id")
        if place_id and not Place.query.filter_by(id=place_id).first():
            raise ReferenciaRota(f"El sitio '{place_id}' no existe")

        timeline_id = campos.get("timeline_id")
        if timeline_id:
            from app.historical.models import Timeline
            if not Timeline.query.filter_by(id=timeline_id).first():
                raise ReferenciaRota(f"La cronología '{timeline_id}' no existe")

    @staticmethod
    def crear(datos: Dict[str, Any]) -> HistoricalContent:
        campos, traducciones = _repartir(datos)

        if HistoricalContent.query.filter_by(id=campos["id"]).first():
            raise YaExiste(campos["id"])

        AdminContenidoService._validar_referencias(campos)

        contenido = HistoricalContent(**campos)
        db.session.add(contenido)
        db.session.commit()

        _guardar_traducciones(ENTITY_HISTORICAL, contenido.id, traducciones)
        return contenido

    @staticmethod
    def actualizar(content_id: str, datos: Dict[str, Any]) -> HistoricalContent:
        contenido = HistoricalContent.query.filter_by(id=content_id).first()
        if contenido is None:
            raise NoExiste(content_id)

        campos, traducciones = _repartir(datos)
        campos.pop("id", None)

        AdminContenidoService._validar_referencias(campos)

        for campo, valor in campos.items():
            setattr(contenido, campo, valor)

        db.session.commit()
        _guardar_traducciones(ENTITY_HISTORICAL, contenido.id, traducciones)
        return contenido

    @staticmethod
    def listar() -> List[HistoricalContent]:
        return HistoricalContent.query.order_by(
            HistoricalContent.timeline_id, HistoricalContent.sort_order
        ).all()


class AdminLagoService:

    @staticmethod
    def crear(datos: Dict[str, Any]) -> LakeGeometry:
        import json
        import uuid

        campos = dict(datos)
        geometria = campos.pop("geometry")

        fila = LakeGeometry(
            id=str(uuid.uuid4()),
            geom=func.ST_GeomFromGeoJSON(json.dumps(geometria)),
            **campos,
        )
        db.session.add(fila)
        db.session.commit()
        return fila

    @staticmethod
    def borrar(geometria_id: str) -> bool:
        """El único borrado de verdad de toda la API de administración.

        Aquí sí y en el resto no, porque un polígono mal trazado no tiene nada
        colgando: nadie lo ha guardado en favoritos ni aparece en el recorrido
        de un tour. Un sitio o un artículo se retiran con `is_published` o
        `status`, que conserva lo que apunta a ellos.
        """
        fila = LakeGeometry.query.filter_by(id=geometria_id).first()
        if fila is None:
            return False
        db.session.delete(fila)
        db.session.commit()
        return True

    @staticmethod
    def listar(year: Optional[int] = None) -> List[LakeGeometry]:
        consulta = LakeGeometry.query
        if year is not None:
            consulta = consulta.filter(LakeGeometry.year_estimate == year)
        return consulta.order_by(
            LakeGeometry.year_estimate, LakeGeometry.surface_type.desc()
        ).all()
