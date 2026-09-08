"""Enumerations used across the application"""
from enum import Enum


class TransportMode(Enum):
    WALKING = "walking"
    PUBLIC_TRANSPORT = "public_transport"
    UBER = "uber"
    BIKE = "bike"


class PlaceType(Enum):
    RUIN = "ruin"
    MUSEUM = "museum"
    HISTORICAL_SITE = "historical_site"
    CULTURAL_CENTER = "cultural_center"
    MONUMENT = "monument"


class TourStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PurchaseStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Curation(Enum):
    """Listas editoriales de la pestaña Explore."""
    MUST_SEE = "must_see"
    QUICK_STOP = "quick_stop"


class LocationPermissionStatus(Enum):
    NOT_ASKED = "not_asked"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
