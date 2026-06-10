"""Historical content models"""
from app.extensions import db
from datetime import datetime


class HistoricalContent(db.Model):
    """Historical content and narratives"""
    
    __tablename__ = 'historical_content'
    
    id = db.Column(db.String(36), primary_key=True)
    
    # Content
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # text, audio, video, article
    
    # Details
    text_content = db.Column(db.Text)
    audio_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    
    # Timeline
    era = db.Column(db.String(255))  # e.g., "Aztec Empire (1345-1521)"
    date_description = db.Column(db.String(255))
    
    # Related to
    place_id = db.Column(db.String(36), db.ForeignKey('places.id'))
    
    # Access control
    is_locked = db.Column(db.Boolean, default=False)
    required_subscription = db.Column(db.String(50))
    
    # Metadata
    author = db.Column(db.String(255))
    sources = db.Column(db.Text)  # JSON array of sources
    verified = db.Column(db.Boolean, default=False)
    
    # Statistics
    views_count = db.Column(db.Integer, default=0)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "contentType": self.content_type,
            "era": self.era,
            "dateDescription": self.date_description,
            "placeId": self.place_id,
            "isLocked": self.is_locked,
            "author": self.author,
            "verified": self.verified,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Timeline(db.Model):
    """Historical timeline"""
    
    __tablename__ = 'timelines'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Timeline items will be stored as HistoricalContent with timeline reference
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LakeView(db.Model):
    """Lake view overlay data for historical context"""
    
    __tablename__ = 'lake_views'
    
    id = db.Column(db.String(36), primary_key=True)
    
    # Coordinates
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # Lake data
    was_water = db.Column(db.Boolean, nullable=False)
    year_estimate = db.Column(db.Integer)  # approximate year for context
    
    # Description
    description = db.Column(db.Text)
    tenochtitlan_name = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
