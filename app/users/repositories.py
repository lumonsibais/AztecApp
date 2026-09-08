"""Users repository"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.extensions import db
from app.shared.utils import utc_ahora
from app.users.models import (
    ContentRead,
    LocationPermissionLog,
    SavedPlace,
    TokenBlocklist,
    User,
)

# Campos que un usuario puede modificar de su propio perfil. Duplica a
# propósito la whitelist del schema marshmallow: si mañana un controller nuevo
# llama al repositorio con el JSON crudo, la escalada de privilegios sigue
# cerrada aquí abajo.
PROFILE_EDITABLE_FIELDS = frozenset(
    {"first_name", "last_name", "avatar_url", "preferred_locale"}
)


class UserRepository:
    """Repository for User operations"""

    @staticmethod
    def find_by_id(user_id: str) -> Optional[User]:
        """Find user by ID"""
        return User.query.filter_by(id=user_id).first()
    
    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        """Find user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def save(user: User) -> User:
        """Save a new user"""
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def update(user_id: str, data: dict) -> Optional[User]:
        """Update user"""
        user = UserRepository.find_by_id(user_id)
        if not user:
            return None
        
        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.session.commit()
        return user
    
    @staticmethod
    def update_profile_fields(user_id: str, data: dict) -> Optional[User]:
        """Actualiza SOLO los campos de perfil editables por el propio usuario.

        Cualquier otra clave se descarta en silencio aquí: la validación que
        informa al cliente vive en el schema, esto es la última barrera.
        """
        safe = {k: v for k, v in data.items() if k in PROFILE_EDITABLE_FIELDS}
        return UserRepository.update(user_id, safe)

    @staticmethod
    def delete(user_id: str) -> bool:
        """Delete user"""
        user = UserRepository.find_by_id(user_id)
        if not user:
            return False
        
        db.session.delete(user)
        db.session.commit()
        return True


class LocationPermissionLogRepository:
    """Repository for location permission logs"""
    
    @staticmethod
    def save(log: LocationPermissionLog) -> LocationPermissionLog:
        """Save a permission log entry"""
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_user_logs(user_id: str) -> List[LocationPermissionLog]:
        """Get all permission logs for a user"""
        return LocationPermissionLog.query.filter_by(user_id=user_id).all()


class TokenBlocklistRepository:
    """Repository for revoked JWTs"""

    @staticmethod
    def is_revoked(jti: str) -> bool:
        """¿Está este jti revocado? Lo consulta el loader de flask-jwt-extended."""
        return db.session.query(
            TokenBlocklist.query.filter_by(jti=jti).exists()
        ).scalar()

    @staticmethod
    def revoke(entry: TokenBlocklist) -> TokenBlocklist:
        """Revoca un token. Idempotente: revocar dos veces no es un error."""
        if TokenBlocklistRepository.is_revoked(entry.jti):
            return entry
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def purge_expired() -> int:
        """Borra las revocaciones ya caducadas. Devuelve cuántas eliminó."""
        deleted = TokenBlocklist.query.filter(
            TokenBlocklist.expires_at < utc_ahora()
        ).delete(synchronize_session=False)
        db.session.commit()
        return deleted


class SavedPlaceRepository:
    """Sitios guardados por un usuario (pestaña Saved)."""

    @staticmethod
    def saved_ids(user_id: str, place_ids: List[str]) -> set:
        """Cuáles de estos sitios tiene guardados, en UNA consulta.

        Existe para que un listado no pregunte "¿está guardado?" sitio por
        sitio: eso sería un N+1 en la pantalla principal.
        """
        if not place_ids:
            return set()

        filas = db.session.query(SavedPlace.place_id).filter(
            SavedPlace.user_id == user_id,
            SavedPlace.place_id.in_(place_ids),
        ).all()
        return {f[0] for f in filas}

    @staticmethod
    def list_places(user_id: str) -> List["Place"]:
        """Los sitios guardados, del más reciente al más antiguo."""
        from app.places.models import Place

        return (
            db.session.query(Place)
            .join(SavedPlace, SavedPlace.place_id == Place.id)
            .filter(SavedPlace.user_id == user_id)
            .order_by(SavedPlace.created_at.desc())
            .all()
        )

    @staticmethod
    def save(user_id: str, place_id: str) -> SavedPlace:
        """Guarda un sitio. Si ya estaba, devuelve la fila existente."""
        existente = SavedPlace.query.filter_by(
            user_id=user_id, place_id=place_id
        ).first()
        if existente:
            return existente

        fila = SavedPlace(id=str(uuid.uuid4()), user_id=user_id, place_id=place_id)
        db.session.add(fila)
        db.session.commit()
        return fila

    @staticmethod
    def remove(user_id: str, place_id: str) -> bool:
        """Quita un sitio de guardados. True si había algo que quitar."""
        borradas = SavedPlace.query.filter_by(
            user_id=user_id, place_id=place_id
        ).delete(synchronize_session=False)
        db.session.commit()
        return borradas > 0


class ContentReadRepository:
    """Artículos de la guía histórica marcados como leídos."""

    @staticmethod
    def read_ids(user_id: str, content_ids: List[str]) -> set:
        """Cuáles de estos artículos ya leyó, en UNA consulta."""
        if not content_ids:
            return set()

        filas = db.session.query(ContentRead.content_id).filter(
            ContentRead.user_id == user_id,
            ContentRead.content_id.in_(content_ids),
        ).all()
        return {f[0] for f in filas}

    @staticmethod
    def mark(user_id: str, content_id: str) -> ContentRead:
        """Marca como leído. Idempotente."""
        existente = ContentRead.query.filter_by(
            user_id=user_id, content_id=content_id
        ).first()
        if existente:
            return existente

        fila = ContentRead(
            id=str(uuid.uuid4()), user_id=user_id, content_id=content_id
        )
        db.session.add(fila)
        db.session.commit()
        return fila

    @staticmethod
    def unmark(user_id: str, content_id: str) -> bool:
        borradas = ContentRead.query.filter_by(
            user_id=user_id, content_id=content_id
        ).delete(synchronize_session=False)
        db.session.commit()
        return borradas > 0
