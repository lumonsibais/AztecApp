"""Utility functions shared across modules"""
import math
from datetime import datetime
from typing import Tuple, Dict, Any
import re


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First location coordinates
        lat2, lon2: Second location coordinates
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def paginate_query(query, page: int = 1, limit: int = 10, max_limit: int = 100):
    """
    Apply pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        limit: Items per page
        max_limit: Maximum limit allowed
        
    Returns:
        Tuple of (paginated_query, total_count)
    """
    limit = min(limit, max_limit)
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    return items, total


def serialize_datetime(dt: datetime) -> str:
    """Convert datetime to ISO format string"""
    if dt is None:
        return None
    return dt.isoformat()


def format_response(
    success: bool,
    data: Any = None,
    message: str = None,
    error: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Format API response.
    
    Args:
        success: Whether the operation was successful
        data: Response data
        message: Success message
        error: Error message
        **kwargs: Additional fields to include
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "success": success,
    }
    
    if data is not None:
        response["data"] = data
    
    if message:
        response["message"] = message
    
    if error:
        response["error"] = error
    
    response.update(kwargs)
    
    return response
