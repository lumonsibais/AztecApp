"""Users repository"""
from app.extensions import db
from app.users.models import User, LocationPermissionLog
from typing import Optional, List


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
