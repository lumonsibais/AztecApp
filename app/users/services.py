"""Users service"""
from typing import Optional, Dict, Any
from app.users.repositories import (
    UserRepository,
    LocationPermissionLogRepository,
    TokenBlocklistRepository,
)
from app.users.models import User, LocationPermissionLog, TokenBlocklist
from app.shared.utils import utc_ahora, utc_desde_timestamp
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid


class UserService:
    """Service for user-related business logic"""
    
    @staticmethod
    def register_user(email: str, password: str, first_name: str = None, last_name: str = None) -> Optional[User]:
        """Register a new user"""
        # Check if user exists
        existing = UserRepository.find_by_email(email)
        if existing:
            return None
        
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
        )
        
        return UserRepository.save(user)
    
    @staticmethod
    def verify_credentials(email: str, password: str) -> Optional[User]:
        """Verify user credentials.

        Una cuenta desactivada no autentica: si no, seguiría recibiendo tokens
        nuevos y solo la rechazaría el middleware en cada petición.
        """
        user = UserRepository.find_by_email(email)
        if not user:
            return None

        if not check_password_hash(user.password_hash, password):
            return None

        if not user.is_active:
            return None

        UserRepository.update(user.id, {"last_login": utc_ahora()})
        return user
    
    @staticmethod
    def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        user = UserRepository.find_by_id(user_id)
        if not user:
            return None
        
        return user.to_dict()
    
    @staticmethod
    def update_user_profile(user_id: str, data: Dict[str, Any]) -> Optional[User]:
        """Update user profile.

        `data` llega ya validado por UserProfileUpdateSchema; el repositorio
        vuelve a filtrar. Antes se descartaban claves de una en una
        (password, password_hash) y pasaba todo lo que nadie recordó listar:
        así es como subscription_tier llegaba hasta el modelo.
        """
        return UserRepository.update_profile_fields(user_id, data)

    @staticmethod
    def revoke_token(jwt_payload: Dict[str, Any]) -> None:
        """Revoca el token cuyo payload se recibe (logout)."""
        TokenBlocklistRepository.revoke(
            TokenBlocklist(
                id=str(uuid.uuid4()),
                jti=jwt_payload["jti"],
                token_type=jwt_payload.get("type", "access"),
                user_id=jwt_payload["sub"],
                expires_at=utc_desde_timestamp(jwt_payload["exp"]),
            )
        )

    @staticmethod
    def is_token_revoked(jti: str) -> bool:
        """Consulta que usa el loader de flask-jwt-extended."""
        return TokenBlocklistRepository.is_revoked(jti)
    
    @staticmethod
    def handle_location_permission(
        user_id: str,
        response: str,  # granted or denied
        context: str = None
    ) -> bool:
        """
        Handle location permission request/response.
        
        Args:
            user_id: User ID
            response: "granted" or "denied"
            context: Where the request came from
        """
        user = UserRepository.find_by_id(user_id)
        if not user:
            return False
        
        # Log the permission request
        log = LocationPermissionLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            response=response,
            context=context or "unknown",
        )
        LocationPermissionLogRepository.save(log)
        
        # Update user's location permission status
        status = "granted" if response == "granted" else "denied"
        return UserRepository.update(
            user_id,
            {
                "location_permission_status": status,
                "location_permission_last_prompted": utc_ahora(),
            }
        ) is not None
    
    @staticmethod
    def record_tour_completion(user_id: str) -> Optional[User]:
        """Suma uno al contador de tours que muestra el perfil."""
        user = UserRepository.find_by_id(user_id)
        if not user:
            return None

        return UserRepository.update(
            user_id,
            {"total_tours_completed": (user.total_tours_completed or 0) + 1}
        )

    @staticmethod
    def delete_account(user_id: str) -> bool:
        """Borra la cuenta.

        El diseño tiene pantalla "Delete Account" y no había ruta que la
        atendiera. Las traducciones no cuelgan del usuario, pero guardados,
        lecturas, progreso de tours y compras sí, y se van con él.
        """
        from app.payments.models import Purchase
        from app.tours.models import TourProgress
        from app.users.models import ContentRead, LocationPermissionLog, SavedPlace

        for modelo in (SavedPlace, ContentRead, TourProgress,
                       LocationPermissionLog, Purchase):
            modelo.query.filter_by(user_id=user_id).delete(synchronize_session=False)

        return UserRepository.delete(user_id)
