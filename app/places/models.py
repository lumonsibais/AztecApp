"""Place models"""
from app.extensions import db
from datetime import datetime
from app.shared.enums import PlaceType


class Place(db.Model):
    """Place model for Aztec sites and locations"""
    
    __tablename__ = 'places'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    place_type = db.Column(db.String(50), nullable=False)
    
    historical_significance = db.Column(db.Text, nullable=False)
    tenochtitlan_name = db.Column(db.String(255))
    era_description = db.Column(db.Text)
    archaeological = db.Column(db.Boolean, default=False)
    
    estimated_visit_duration = db.Column(db.Integer, nullable=False)  # minutes
    image_url = db.Column(db.String(500))
    
    # Content access
    is_locked = db.Column(db.Boolean, default=False)
    required_subscription = db.Column(db.String(50))  # free, premium, vip
    unlock_price = db.Column(db.Float)  # USD
    
    # Practical information
    opening_hours = db.Column(db.String(255))
    entry_fee = db.Column(db.Float)
    safety_recommendations = db.Column(db.Text)
    
    # Nearby services
    has_bathrooms = db.Column(db.Boolean, default=False)
    has_cafes = db.Column(db.Boolean, default=False)
    has_hotels = db.Column(db.Boolean, default=False)
    
    # Ratings
    average_rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    tours = db.relationship('Tour', secondary='tour_places', backref='places')
    
    def to_dict(self, include_full_details=False):
        """Convert model to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': {
                'latitude': self.latitude,
                'longitude': self.longitude,
            },
            'placeType': self.place_type,
            'historicalSignificance': self.historical_significance,
            'estimatedVisitDuration': self.estimated_visit_duration,
            'imageUrl': self.image_url,
            'contentAccess': {
                'isLocked': self.is_locked,
                'requiredSubscription': self.required_subscription,
                'unlockPrice': self.unlock_price,
            },
            'nearbyServices': {
                'bathrooms': self.has_bathrooms,
                'cafes': self.has_cafes,
                'hotels': self.has_hotels,
            },
            'ratings': {
                'average': self.average_rating,
                'count': self.rating_count,
            },
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_full_details:
            data.update({
                'openingHours': self.opening_hours,
                'entryFee': self.entry_fee,
                'safetyRecommendations': self.safety_recommendations,
                'historicalContext': {
                    'tenochtitlanName': self.tenochtitlan_name,
                    'eraDescription': self.era_description,
                    'archaeological': self.archaeological,
                },
            })
        
        return data
