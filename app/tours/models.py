"""Tours models"""
from app.extensions import db
from datetime import datetime

# Association table for many-to-many relationship between tours and places
tour_places = db.Table(
    'tour_places',
    db.Column('tour_id', db.String(36), db.ForeignKey('tours.id'), primary_key=True),
    db.Column('place_id', db.String(36), db.ForeignKey('places.id'), primary_key=True),
    db.Column('order', db.Integer, default=0)
)


class Tour(db.Model):
    """Tour model for self-paced guided tours"""
    
    __tablename__ = 'tours'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Status
    status = db.Column(db.String(50), nullable=False, default='draft')  # draft, published, archived
    
    # Pricing and access
    is_free = db.Column(db.Boolean, default=False)
    price = db.Column(db.Float, default=0)  # USD
    is_locked = db.Column(db.Boolean, default=False)
    
    # Details
    estimated_duration = db.Column(db.Integer, nullable=False)  # minutes
    difficulty_level = db.Column(db.String(50))  # easy, medium, hard
    image_url = db.Column(db.String(500))
    
    # Route info
    total_distance = db.Column(db.Float)  # km
    
    # Content
    content_description = db.Column(db.Text)
    includes_audio = db.Column(db.Boolean, default=False)
    
    # Statistics
    views_count = db.Column(db.Integer, default=0)
    completion_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0)
    
    # Relations
    places = db.relationship(
        'Place',
        secondary=tour_places,
        backref=db.backref('tours', lazy='dynamic')
    )
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_places=False):
        """Convert model to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'isFree': self.is_free,
            'price': self.price,
            'isLocked': self.is_locked,
            'estimatedDuration': self.estimated_duration,
            'difficultyLevel': self.difficulty_level,
            'imageUrl': self.image_url,
            'totalDistance': self.total_distance,
            'statistics': {
                'views': self.views_count,
                'completions': self.completion_count,
                'averageRating': self.average_rating,
            },
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_places:
            data['places'] = [p.to_dict() for p in self.places]
        
        return data


class TourProgress(db.Model):
    """Track user's progress through a tour"""
    
    __tablename__ = 'tour_progress'
    
    id = db.Column(db.String(36), primary_key=True)
    tour_id = db.Column(db.String(36), db.ForeignKey('tours.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Progress tracking
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Location tracking
    current_place_index = db.Column(db.Integer, default=0)
    last_location_lat = db.Column(db.Float)
    last_location_lon = db.Column(db.Float)
    
    # Feedback
    rating = db.Column(db.Integer)  # 1-5
    notes = db.Column(db.Text)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
