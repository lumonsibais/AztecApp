"""Tours repository"""
from app.extensions import db
from app.tours.models import Tour, TourProgress
from typing import List, Optional, Tuple


class TourRepository:
    """Repository for Tour model operations"""
    
    @staticmethod
    def find_by_id(tour_id: str) -> Optional[Tour]:
        """Find tour by ID"""
        return Tour.query.filter_by(id=tour_id).first()
    
    @staticmethod
    def find_all(skip: int = 0, limit: int = 10) -> Tuple[List[Tour], int]:
        """Get all published tours with pagination"""
        query = Tour.query.filter_by(status='published')
        total = query.count()
        tours = query.offset(skip).limit(limit).all()
        return tours, total
    
    @staticmethod
    def find_free_tours(limit: int = 3) -> List[Tour]:
        """Get free tours for non-premium users"""
        return Tour.query.filter_by(is_free=True, status='published').limit(limit).all()
    
    @staticmethod
    def find_by_status(status: str) -> List[Tour]:
        """Find tours by status"""
        return Tour.query.filter_by(status=status).all()
    
    @staticmethod
    def save(tour: Tour) -> Tour:
        """Save or update a tour"""
        db.session.add(tour)
        db.session.commit()
        return tour
    
    @staticmethod
    def update(tour_id: str, data: dict) -> Optional[Tour]:
        """Update a tour"""
        tour = TourRepository.find_by_id(tour_id)
        if not tour:
            return None
        
        for key, value in data.items():
            if hasattr(tour, key):
                setattr(tour, key, value)
        
        db.session.commit()
        return tour
    
    @staticmethod
    def delete(tour_id: str) -> bool:
        """Delete a tour"""
        tour = TourRepository.find_by_id(tour_id)
        if not tour:
            return False
        
        db.session.delete(tour)
        db.session.commit()
        return True


class TourProgressRepository:
    """Repository for TourProgress operations"""
    
    @staticmethod
    def find_by_id(progress_id: str) -> Optional[TourProgress]:
        """Find tour progress by ID"""
        return TourProgress.query.filter_by(id=progress_id).first()
    
    @staticmethod
    def find_by_tour_and_user(tour_id: str, user_id: str) -> Optional[TourProgress]:
        """Find tour progress for a specific user and tour"""
        return TourProgress.query.filter_by(tour_id=tour_id, user_id=user_id).first()
    
    @staticmethod
    def find_user_tours(user_id: str) -> List[TourProgress]:
        """Get all tours a user has started"""
        return TourProgress.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def save(progress: TourProgress) -> TourProgress:
        """Save tour progress"""
        db.session.add(progress)
        db.session.commit()
        return progress
    
    @staticmethod
    def update(progress_id: str, data: dict) -> Optional[TourProgress]:
        """Update tour progress"""
        progress = TourProgressRepository.find_by_id(progress_id)
        if not progress:
            return None
        
        for key, value in data.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        
        db.session.commit()
        return progress
