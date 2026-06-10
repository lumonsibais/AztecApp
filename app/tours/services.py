"""Tours service"""
from typing import List, Dict, Any, Optional
from app.tours.repositories import TourRepository, TourProgressRepository
from app.tours.models import Tour, TourProgress
from app.shared.constants import MAX_FREE_TOURS, PREMIUM_TOUR_PRICE


class TourService:
    """Service for tour-related business logic"""
    
    @staticmethod
    def get_free_tours() -> List[Dict[str, Any]]:
        """Get free tours available to all users (max 3)"""
        tours = TourRepository.find_free_tours(MAX_FREE_TOURS)
        return [t.to_dict() for t in tours]
    
    @staticmethod
    def get_all_tours(
        page: int = 1,
        limit: int = 10,
        subscription_tier: str = "free"
    ) -> Dict[str, Any]:
        """Get all available tours"""
        tours, total = TourRepository.find_all((page - 1) * limit, limit)
        
        # Filter by subscription tier
        filtered_tours = []
        for tour in tours:
            if tour.is_locked and subscription_tier == "free":
                continue
            filtered_tours.append(tour)
        
        return {
            "tours": [t.to_dict() for t in filtered_tours],
            "page": page,
            "limit": limit,
            "total": total,
        }
    
    @staticmethod
    def get_tour_details(tour_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tour"""
        tour = TourRepository.find_by_id(tour_id)
        if not tour:
            return None
        
        return tour.to_dict(include_places=True)
    
    @staticmethod
    def start_tour(tour_id: str, user_id: str) -> Optional[TourProgress]:
        """Start a tour for a user"""
        import uuid
        
        # Check if user already started this tour
        existing = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if existing:
            return existing
        
        progress = TourProgress(
            id=str(uuid.uuid4()),
            tour_id=tour_id,
            user_id=user_id,
        )
        
        return TourProgressRepository.save(progress)
    
    @staticmethod
    def update_tour_progress(
        tour_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> Optional[TourProgress]:
        """Update user's progress in a tour"""
        progress = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if not progress:
            return None
        
        return TourProgressRepository.update(progress.id, data)
    
    @staticmethod
    def complete_tour(
        tour_id: str,
        user_id: str,
        rating: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[TourProgress]:
        """Mark tour as completed"""
        from datetime import datetime
        
        progress = TourProgressRepository.find_by_tour_and_user(tour_id, user_id)
        if not progress:
            return None
        
        data = {
            "is_completed": True,
            "completed_at": datetime.utcnow(),
        }
        
        if rating:
            data["rating"] = rating
        
        if notes:
            data["notes"] = notes
        
        return TourProgressRepository.update(progress.id, data)
    
    @staticmethod
    def get_user_tours(user_id: str) -> List[Dict[str, Any]]:
        """Get all tours started by a user"""
        progresses = TourProgressRepository.find_user_tours(user_id)
        
        result = []
        for progress in progresses:
            tour = TourRepository.find_by_id(progress.tour_id)
            if tour:
                tour_data = tour.to_dict()
                tour_data["progress"] = {
                    "isCompleted": progress.is_completed,
                    "currentPlaceIndex": progress.current_place_index,
                    "rating": progress.rating,
                    "startedAt": progress.started_at.isoformat() if progress.started_at else None,
                    "completedAt": progress.completed_at.isoformat() if progress.completed_at else None,
                }
                result.append(tour_data)
        
        return result
