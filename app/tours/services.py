"""Tours service"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.tours.repositories import TourRepository, TourProgressRepository
from app.users.services import UserService
from app.tours.models import Tour, TourProgress
from app.shared.access import can_access_resource
from app.shared.constants import MAX_FREE_TOURS
from app.shared.i18n import DEFAULT_LOCALE, apply_translation, apply_translations
from app.shared.translations import ENTITY_TOUR
from app.shared.utils import utc_ahora

CAMPOS_TRADUCIBLES = {
    "title": "title",
    "description": "description",
    "content_description": "contentDescription",
    "duration_text": "durationText",
}


def serialize(
    tour: Tour, has_access: bool, include_stops: bool = False
) -> Dict[str, Any]:
    """Serializa un tour según lo que esta cuenta puede ver."""
    return tour.to_dict(
        include_stops=include_stops,
        unlocked=can_access_resource(has_access, tour),
    )


class TourService:
    """Service for tour-related business logic"""

    @staticmethod
    def get_free_tours() -> List[Dict[str, Any]]:
        """Get free tours available to all users (max 3)"""
        tours = TourRepository.find_free_tours(MAX_FREE_TOURS)
        return [t.to_dict() for t in tours]

    @staticmethod
    def get_all_tours(
        page: int = 1,
        limit: int = 10,
        has_access: bool = False,
        locale: str = DEFAULT_LOCALE,
    ) -> Dict[str, Any]:
        """Listado de tours publicados.

        Los bloqueados aparecen como teaser en vez de desaparecer: si no, un
        usuario free no llega nunca a ver qué le ofrece pagar.
        """
        tours, total = TourRepository.find_all((page - 1) * limit, limit)

        items = [serialize(t, has_access) for t in tours]

        return {
            "tours": apply_translations(items, ENTITY_TOUR, locale, CAMPOS_TRADUCIBLES),
            "page": page,
            "limit": limit,
            "total": total,
        }

    @staticmethod
    def get_tour_details(
        tour_id: str, has_access: bool = False, locale: str = DEFAULT_LOCALE
    ) -> Optional[Dict[str, Any]]:
        """Ficha de un tour, con su ruta solo si la cuenta tiene el desbloqueo."""
        tour = TourRepository.find_by_id(tour_id)
        if not tour:
            return None

        data = serialize(tour, has_access, include_stops=True)
        return apply_translation(data, ENTITY_TOUR, locale, CAMPOS_TRADUCIBLES)

    @staticmethod
    def can_start(tour: Tour, has_access: bool) -> bool:
        """¿Puede esta cuenta iniciar el tour?

        Antes no se comprobaba: cualquiera con token podía arrancar un tour de
        pago llamando directamente a POST /<tour_id>/start.
        """
        return can_access_resource(has_access, tour)

    @staticmethod
    def start_tour(
        tour_id: str, user_id: str, has_access: bool = False
    ) -> Optional[TourProgress]:
        """Inicia un tour para un usuario.

        Devuelve None si el tour no existe. Lanza PermissionError si existe
        pero la cuenta no tiene acceso, para que el controller distinga un 404 de un
        403 — decirle "no existe" a quien no ha pagado es peor producto.
        """
        import uuid

        tour = TourRepository.find_by_id(tour_id)
        if not tour:
            return None

        if not TourService.can_start(tour, has_access):
            raise PermissionError(tour_id)

        existing = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if existing:
            return existing

        progress = TourProgress(
            id=str(uuid.uuid4()),
            tour_id=tour_id,
            user_id=user_id,
        )

        return TourProgressRepository.save(progress)

    @staticmethod
    def update_tour_progress(
        tour_id: str,
        user_id: str,
        data: Dict[str, Any],
    ) -> Optional[TourProgress]:
        """Actualiza el avance del usuario en un tour.

        `data` llega validado por TourProgressUpdateSchema. Pasar el JSON crudo
        al repositorio dejaba que el cliente escribiera is_completed,
        completed_at o incluso user_id.
        """
        progress = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if not progress:
            return None

        return TourProgressRepository.update(progress.id, data)

    @staticmethod
    def complete_tour(
        tour_id: str,
        user_id: str,
        rating: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[TourProgress]:
        """Mark tour as completed"""
        progress = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if not progress:
            return None

        if progress.is_completed:
            return progress

        data = {
            "is_completed": True,
            "completed_at": utc_ahora(),
        }
        if rating:
            data["rating"] = rating
        if notes:
            data["notes"] = notes

        cerrado = TourProgressRepository.update(progress.id, data)

        # Contadores que el diseño enseña y que hasta ahora nadie incrementaba:
        # "🎧 Tours" en el perfil y las estadísticas del propio tour.
        UserService.record_tour_completion(user_id)
        TourRepository.increment_completions(tour_id)

        return cerrado

    @staticmethod
    def get_user_tours(
        user_id: str, has_access: bool = False, locale: str = DEFAULT_LOCALE
    ) -> List[Dict[str, Any]]:
        """Tours que el usuario ha empezado, con su progreso."""
        progresses = TourProgressRepository.find_user_tours(user_id)

        result = []
        for progress in progresses:
            tour = TourRepository.find_by_id(progress.tour_id)
            if not tour:
                continue

            tour_data = serialize(tour, has_access)
            tour_data["progress"] = {
                "isCompleted": progress.is_completed,
                "currentStopIndex": progress.current_stop_index,
                "rating": progress.rating,
                "startedAt": (
                    progress.started_at.isoformat() if progress.started_at else None
                ),
                "completedAt": (
                    progress.completed_at.isoformat() if progress.completed_at else None
                ),
            }
            result.append(tour_data)

        return apply_translations(result, ENTITY_TOUR, locale, CAMPOS_TRADUCIBLES)
