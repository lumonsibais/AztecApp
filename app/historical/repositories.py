"""Historical content repository"""
from app.extensions import db
from app.historical.models import HistoricalContent, Timeline, LakeView
from typing import Optional, List


class HistoricalContentRepository:
    """Repository for HistoricalContent operations"""
    
    @staticmethod
    def find_by_id(content_id: str) -> Optional[HistoricalContent]:
        """Find content by ID"""
        return HistoricalContent.query.filter_by(id=content_id).first()
    
    @staticmethod
    def find_by_place(place_id: str) -> List[HistoricalContent]:
        """Find content related to a specific place"""
        return HistoricalContent.query.filter_by(place_id=place_id).all()
    
    @staticmethod
    def find_by_era(era: str) -> List[HistoricalContent]:
        """Find content by historical era"""
        return HistoricalContent.query.filter_by(era=era).all()
    
    @staticmethod
    def find_by_type(content_type: str) -> List[HistoricalContent]:
        """Find content by type"""
        return HistoricalContent.query.filter_by(content_type=content_type).all()
    
    @staticmethod
    def save(content: HistoricalContent) -> HistoricalContent:
        """Save content"""
        db.session.add(content)
        db.session.commit()
        return content
    
    @staticmethod
    def update(content_id: str, data: dict) -> Optional[HistoricalContent]:
        """Update content"""
        content = HistoricalContentRepository.find_by_id(content_id)
        if not content:
            return None
        
        for key, value in data.items():
            if hasattr(content, key):
                setattr(content, key, value)
        
        db.session.commit()
        return content


class TimelineRepository:
    """Repository for Timeline operations"""
    
    @staticmethod
    def find_all() -> List[Timeline]:
        """Get all timelines"""
        return Timeline.query.all()
    
    @staticmethod
    def find_by_id(timeline_id: str) -> Optional[Timeline]:
        """Find timeline by ID"""
        return Timeline.query.filter_by(id=timeline_id).first()
    
    @staticmethod
    def save(timeline: Timeline) -> Timeline:
        """Save timeline"""
        db.session.add(timeline)
        db.session.commit()
        return timeline


class LakeViewRepository:
    """Repository for LakeView operations"""
    
    @staticmethod
    def find_near_location(
        latitude: float,
        longitude: float,
        radius_km: float = 5
    ) -> List[LakeView]:
        """Find lake view data near location"""
        # In a real application, this would use spatial indexing
        from app.shared.utils import calculate_distance
        
        all_views = LakeView.query.all()
        nearby = []
        
        for view in all_views:
            distance = calculate_distance(latitude, longitude, view.latitude, view.longitude)
            if distance <= radius_km:
                nearby.append(view)
        
        return nearby
    
    @staticmethod
    def save(lake_view: LakeView) -> LakeView:
        """Save lake view data"""
        db.session.add(lake_view)
        db.session.commit()
        return lake_view
