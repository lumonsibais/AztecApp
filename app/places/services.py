"""Places service for business logic"""
from typing import Any, Dict, List, Optional, Set

from app.places.models import Place
from app.places.repositories import PlaceRepository
from app.shared.access import can_access_resource
from app.shared.constants import LOCATION_PROXIMITY_RADIUS
from app.shared.i18n import DEFAULT_LOCALE, apply_translation, apply_translations
from app.shared.translations import ENTITY_PLACE
from app.users.repositories import SavedPlaceRepository

# Columnas traducibles -> clave en la respuesta serializada.
# Solo claves de primer nivel: lo anidado se traducirá cuando aplanemos esa
# parte del contrato.
CAMPOS_TRADUCIBLES = {
    "name": "name",
    "tagline": "tagline",
    "description": "description",
    "historical_significance": "historicalSignificance",
    "why_visit": "whyVisit",
    "how_to_get_there": "howToGetThere",
    "visit_duration_text": "visitDurationText",
}


def serialize(
    place: Place,
    has_access: bool,
    full: bool = False,
    distance_km: float = None,
    guardados: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Serializa un sitio según lo que esta cuenta puede ver.

    Único punto donde se decide qué campos viajan: si un módulo nuevo serializa
    places por su cuenta, el paywall se le escapa.

    `guardados` es el conjunto de ids que el usuario tiene guardados. Llega ya
    resuelto para no consultar uno por uno dentro de un listado.
    """
    return place.to_dict(
        include_full_details=full,
        unlocked=can_access_resource(has_access, place),
        distance_km=distance_km,
        is_saved=(place.id in guardados) if guardados is not None else None,
    )


def _guardados_de(user_id: Optional[str], place_ids: List[str]) -> Optional[Set[str]]:
    """Ids guardados por el usuario, en UNA consulta. None si es anónimo."""
    if not user_id:
        return None
    if not place_ids:
        return set()
    return SavedPlaceRepository.saved_ids(user_id, place_ids)


class PlaceService:
    """Service for place-related business logic"""

    @staticmethod
    def get_nearby_places(
        latitude: float,
        longitude: float,
        radius_km: float = LOCATION_PROXIMITY_RADIUS,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
        curation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Sitios cercanos, con su distancia y ordenados por cercanía.

        Los bloqueados siguen apareciendo como teaser: son el gancho del
        freemium, y en el mapa un candado vale más que un hueco.
        """
        filas = PlaceRepository.find_nearby_with_distance(
            latitude, longitude, radius_km, curation=curation
        )
        guardados = _guardados_de(user_id, [p.id for p, _ in filas])

        items = [
            serialize(p, has_access, distance_km=km, guardados=guardados)
            for p, km in filas
        ]
        return apply_translations(items, ENTITY_PLACE, locale, CAMPOS_TRADUCIBLES)

    @staticmethod
    def get_all_places(
        page: int = 1,
        limit: int = 10,
        curation: Optional[str] = None,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Listado paginado, con filtro opcional por lista editorial."""
        places, total = PlaceRepository.find_all(
            skip=(page - 1) * limit, limit=limit, curation=curation
        )
        guardados = _guardados_de(user_id, [p.id for p in places])

        items = [serialize(p, has_access, guardados=guardados) for p in places]

        return {
            "places": apply_translations(
                items, ENTITY_PLACE, locale, CAMPOS_TRADUCIBLES
            ),
            "page": page,
            "limit": limit,
            "total": total,
        }

    @staticmethod
    def get_place_details(
        place_id: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
        user_id: Optional[str] = None,
        latitude: float = None,
        longitude: float = None,
    ) -> Optional[Dict[str, Any]]:
        """Ficha completa, recortada si la cuenta no tiene el desbloqueo."""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return None

        distancia = None
        if latitude is not None and longitude is not None:
            distancia = PlaceRepository.distance_km(place, latitude, longitude)

        guardados = _guardados_de(user_id, [place.id])
        data = serialize(
            place, has_access, full=True, distance_km=distancia, guardados=guardados
        )
        return apply_translation(data, ENTITY_PLACE, locale, CAMPOS_TRADUCIBLES)

    @staticmethod
    def get_saved_places(
        user_id: str,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
    ) -> List[Dict[str, Any]]:
        """La pestaña Saved: lo que el usuario marcó con el corazón."""
        places = SavedPlaceRepository.list_places(user_id)
        guardados = {p.id for p in places}

        items = [serialize(p, has_access, guardados=guardados) for p in places]
        return apply_translations(items, ENTITY_PLACE, locale, CAMPOS_TRADUCIBLES)

    @staticmethod
    def save_place(user_id: str, place_id: str) -> bool:
        """Guarda un sitio. Idempotente: dos toques no crean dos filas."""
        if PlaceRepository.find_by_id(place_id) is None:
            return False
        SavedPlaceRepository.save(user_id, place_id)
        return True

    @staticmethod
    def unsave_place(user_id: str, place_id: str) -> bool:
        """Quita un sitio de guardados."""
        return SavedPlaceRepository.remove(user_id, place_id)

    @staticmethod
    def create_place(data: Dict[str, Any]) -> Place:
        """Create a new place (admin only)"""
        import uuid

        place = Place(
            id=str(uuid.uuid4()),
            name=data.get("name"),
            tagline=data.get("tagline"),
            description=data.get("description"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            neighborhood=data.get("neighborhood"),
            place_type=data.get("place_type"),
            curation=data.get("curation"),
            editorial_rating=data.get("editorial_rating"),
            historical_significance=data.get("historical_significance"),
            why_visit=data.get("why_visit"),
            how_to_get_there=data.get("how_to_get_there"),
            estimated_visit_duration=data.get("estimated_visit_duration", 60),
            visit_duration_text=data.get("visit_duration_text"),
            image_url=data.get("image_url"),
            is_locked=data.get("is_locked", False),
        )

        return PlaceRepository.save(place)

    @staticmethod
    def update_place(place_id: str, data: Dict[str, Any]) -> Optional[Place]:
        """Update a place"""
        return PlaceRepository.update(place_id, data)

    @staticmethod
    def delete_place(place_id: str) -> bool:
        """Delete a place"""
        return PlaceRepository.delete(place_id)
