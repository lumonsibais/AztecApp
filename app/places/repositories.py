"""Places repository for database operations"""
from app.extensions import db
from app.places.models import Place
from app.shared.utils import calculate_distance
from typing import List, Optional, Tuple


class PlaceRepository:
    """Repository for Place model operations"""
    
    @staticmethod
    def find_by_id(place_id: str) -> Optional[Place]:
        """Find place by ID"""
        return Place.query.filter_by(id=place_id).first()
    
    @staticmethod
    def find_all(skip: int = 0, limit: int = 10) -> Tuple[List[Place], int]:
        """Get all places with pagination"""
        query = Place.query
        total = query.count()
        places = query.offset(skip).limit(limit).all()
        return places, total
    
    @staticmethod
    def find_by_type(place_type: str) -> List[Place]:
        """Find places by type"""
        return Place.query.filter_by(place_type=place_type).all()
    
    @staticmethod
    def find_nearby(
        user_latitude: float,
        user_longitude: float,
        radius_km: float = 5,
        limit: int = 10
    ) -> List[Place]:
        """Find places near user location"""
        places = Place.query.all()
        nearby = []
        
        for place in places:
            distance = calculate_distance(
                user_latitude,
                user_longitude,
                place.latitude,
                place.longitude
            )
            if distance <= radius_km:
                nearby.append((place, distance))
        
        # Sort by distance and limit results
        nearby.sort(key=lambda x: x[1])
        return [place for place, _ in nearby[:limit]]
    
    @staticmethod
    def find_by_location(
        latitude: float,
        longitude: float,
        radius_km: float = 5
    ) -> List[Place]:
        """Find all places within radius of location"""
        return PlaceRepository.find_nearby(latitude, longitude, radius_km, limit=None)
    
    @staticmethod
    def save(place: Place) -> Place:
        """Save or update a place"""
        db.session.add(place)
        db.session.commit()
        return place
    
    @staticmethod
    def update(place_id: str, data: dict) -> Optional[Place]:
        """Update a place"""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return None
        
        for key, value in data.items():
            if hasattr(place, key):
                setattr(place, key, value)
        
        db.session.commit()
        return place
    
    @staticmethod
    def delete(place_id: str) -> bool:
        """Delete a place"""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return False
        
        db.session.delete(place)
        db.session.commit()
        return True
    
    @staticmethod
    def get_recommended_places(
        user_latitude: float,
        user_longitude: float,
        subscription_tier: str = "free",
        limit: int = 10
    ) -> List[Place]:
        """Get recommended places based on user location and subscription"""
        nearby = PlaceRepository.find_nearby(
            user_latitude,
            user_longitude,
            radius_km=10,
            limit=limit * 2
        )
        
        # Filter by subscription tier
        filtered = []
        for place in nearby:
            if place.is_locked and subscription_tier == "free":
                continue
            filtered.append(place)
        
        return filtered[:limit]
