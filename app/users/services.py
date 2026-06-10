"""Users service"""
from typing import Optional, Dict, Any
from app.users.repositories import UserRepository, LocationPermissionLogRepository
from app.users.models import User, LocationPermissionLog
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
        """Verify user credentials"""
        user = UserRepository.find_by_email(email)
        if not user:
            return None
        
        if not check_password_hash(user.password_hash, password):
            return None
        
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
        """Update user profile"""
        # Don't allow direct password changes here
        data.pop("password_hash", None)
        data.pop("password", None)
        
        return UserRepository.update(user_id, data)
    
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
                "location_permission_last_prompted": datetime.utcnow(),
            }
        ) is not None
    
    @staticmethod
    def upgrade_subscription(user_id: str, tier: str, months: int = 1) -> Optional[User]:
        """Upgrade user's subscription tier"""
        from datetime import timedelta
        
        end_date = datetime.utcnow() + timedelta(days=30 * months)
        
        return UserRepository.update(
            user_id,
            {
                "subscription_tier": tier,
                "subscription_start_date": datetime.utcnow(),
                "subscription_end_date": end_date,
            }
        )
    
    @staticmethod
    def record_tour_completion(user_id: str) -> Optional[User]:
        """Record that user completed a tour"""
        user = UserRepository.find_by_id(user_id)
        if not user:
            return None
        
        return UserRepository.update(
            user_id,
            {"total_tours_completed": user.total_tours_completed + 1}
        )
