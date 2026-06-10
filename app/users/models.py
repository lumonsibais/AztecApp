"""Users models"""
from app.extensions import db
from datetime import datetime
from app.shared.enums import SubscriptionTier, LocationPermissionStatus


class User(db.Model):
    """User model"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(500))
    
    # Subscription
    subscription_tier = db.Column(db.String(50), default="free")  # free, premium, vip
    subscription_start_date = db.Column(db.DateTime)
    subscription_end_date = db.Column(db.DateTime)
    
    # Location permissions
    location_permission_status = db.Column(
        db.String(50),
        default="not_asked"
    )  # not_asked, granted, denied, revoked
    location_permission_last_prompted = db.Column(db.DateTime)
    
    # Stats
    total_tours_completed = db.Column(db.Integer, default=0)
    last_location_update = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    
    # Account
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "avatarUrl": self.avatar_url,
            "subscriptionTier": self.subscription_tier,
            "locationPermissionStatus": self.location_permission_status,
            "totalToursCompleted": self.total_tours_completed,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class LocationPermissionLog(db.Model):
    """Track location permission requests and responses"""
    
    __tablename__ = 'location_permission_logs'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.String(50))  # granted, denied
    context = db.Column(db.String(255))  # where was it requested from
