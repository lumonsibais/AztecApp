"""Places service for business logic"""
from typing import List, Dict, Any, Optional, Tuple
from app.places.repositories import PlaceRepository
from app.places.models import Place
from app.shared.constants import LOCATION_PROXIMITY_RADIUS


class PlaceService:
    """Service for place-related business logic"""
    
    @staticmethod
    def get_nearby_places(
        latitude: float,
        longitude: float,
        radius_km: float = LOCATION_PROXIMITY_RADIUS,
        subscription_tier: str = "free"
    ) -> List[Place]:
        """
        Get nearby places for user's current location.
        Filters content based on subscription tier.
        """
        places = PlaceRepository.find_nearby(latitude, longitude, radius_km)
        
        # Filter based on subscription tier
        if subscription_tier == "free":
            places = [p for p in places if not p.is_locked]
        
        return places
    
    @staticmethod
    def get_all_places(
        page: int = 1,
        limit: int = 10,
        place_type: Optional[str] = None,
        subscription_tier: str = "free"
    ) -> Dict[str, Any]:
        """Get all places with optional filtering"""
        if place_type:
            places = PlaceRepository.find_by_type(place_type)
        else:
            places, total = PlaceRepository.find_all(
                skip=(page - 1) * limit,
                limit=limit
            )
        
        # Filter by subscription tier
        if subscription_tier == "free":
            places = [p for p in places if not p.is_locked]
        
        return {
            "places": [p.to_dict() for p in places],
            "page": page,
            "limit": limit,
        }
    
    @staticmethod
    def get_place_details(place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place"""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return None
        
        return place.to_dict(include_full_details=True)
    
    @staticmethod
    def get_recommended_places(
        latitude: float,
        longitude: float,
        subscription_tier: str = "free",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get AI/curated recommended places"""
        places = PlaceRepository.get_recommended_places(
            latitude,
            longitude,
            subscription_tier,
            limit
        )
        return [p.to_dict() for p in places]
    
    @staticmethod
    def create_place(data: Dict[str, Any]) -> Place:
        """Create a new place (admin only)"""
        import uuid
        
        place = Place(
            id=str(uuid.uuid4()),
            name=data.get("name"),
            description=data.get("description"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            place_type=data.get("place_type"),
            historical_significance=data.get("historical_significance"),
            estimated_visit_duration=data.get("estimated_visit_duration", 60),
            image_url=data.get("image_url"),
            is_locked=data.get("is_locked", False),
            required_subscription=data.get("required_subscription"),
            unlock_price=data.get("unlock_price"),
        )
        
        return PlaceRepository.save(place)
    
    @staticmethod
    def update_place(place_id: str, data: Dict[str, Any]) -> Optional[Place]:
        """Update a place"""
        return PlaceRepository.update(place_id, data)
    
    @staticmethod
    def delete_place(place_id: str) -> bool:
        """Delete a place"""
        return PlaceRepository.delete(place_id)
