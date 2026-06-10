"""Historical content service"""
from typing import List, Dict, Any, Optional
from app.historical.repositories import (
    HistoricalContentRepository,
    TimelineRepository,
    LakeViewRepository,
)
from app.historical.models import HistoricalContent, Timeline, LakeView


class HistoricalContentService:
    """Service for historical content"""
    
    @staticmethod
    def get_content_by_place(place_id: str) -> List[Dict[str, Any]]:
        """Get historical content related to a place"""
        contents = HistoricalContentRepository.find_by_place(place_id)
        return [c.to_dict() for c in contents]
    
    @staticmethod
    def get_content_by_era(era: str) -> List[Dict[str, Any]]:
        """Get content from a specific historical era"""
        contents = HistoricalContentRepository.find_by_era(era)
        return [c.to_dict() for c in contents]
    
    @staticmethod
    def get_all_content(content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all historical content"""
        if content_type:
            contents = HistoricalContentRepository.find_by_type(content_type)
        else:
            contents = HistoricalContent.query.all()
        
        return [c.to_dict() for c in contents]
    
    @staticmethod
    def get_content_detail(content_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed content"""
        content = HistoricalContentRepository.find_by_id(content_id)
        if not content:
            return None
        
        data = content.to_dict()
        
        # Add full content based on type
        if content.content_type == "text":
            data["content"] = content.text_content
        elif content.content_type == "audio":
            data["audioUrl"] = content.audio_url
        elif content.content_type == "video":
            data["videoUrl"] = content.video_url
        
        # Add sources
        if content.sources:
            data["sources"] = content.sources
        
        return data


class TimelineService:
    """Service for timelines"""
    
    @staticmethod
    def get_all_timelines() -> List[Dict[str, Any]]:
        """Get all timelines"""
        timelines = TimelineRepository.find_all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
            }
            for t in timelines
        ]


class LakeViewService:
    """Service for lake view overlays"""
    
    @staticmethod
    def get_lake_data(
        latitude: float,
        longitude: float,
        radius_km: float = 5
    ) -> List[Dict[str, Any]]:
        """Get lake overlay data for a location"""
        views = LakeViewRepository.find_near_location(latitude, longitude, radius_km)
        
        return [
            {
                "id": v.id,
                "latitude": v.latitude,
                "longitude": v.longitude,
                "wasWater": v.was_water,
                "yearEstimate": v.year_estimate,
                "description": v.description,
                "tenochtitlanName": v.tenochtitlan_name,
            }
            for v in views
        ]
    
    @staticmethod
    def create_lake_view_data(
        latitude: float,
        longitude: float,
        was_water: bool,
        description: str = None,
        tenochtitlan_name: str = None
    ) -> LakeView:
        """Create lake view data point"""
        import uuid
        
        lake_view = LakeView(
            id=str(uuid.uuid4()),
            latitude=latitude,
            longitude=longitude,
            was_water=was_water,
            description=description,
            tenochtitlan_name=tenochtitlan_name,
        )
        
        return LakeViewRepository.save(lake_view)
