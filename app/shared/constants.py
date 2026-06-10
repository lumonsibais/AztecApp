"""Shared constants across the application"""

# Pricing
PREMIUM_TOUR_PRICE = 15  # USD
MAX_FREE_TOURS = 3

# Location
LOCATION_PROXIMITY_RADIUS = 5  # km
TENOCHTITLAN_CENTER_LAT = 19.4326
TENOCHTITLAN_CENTER_LON = -99.1332

# Features
LAKE_VIEW_ENABLED = True
HISTORICAL_OVERLAY_ENABLED = True

# Error messages
ERROR_MESSAGES = {
    "UNAUTHORIZED": "Unauthorized access",
    "NOT_FOUND": "Resource not found",
    "VALIDATION_ERROR": "Validation error",
    "INTERNAL_ERROR": "Internal server error",
    "LOCATION_PERMISSION_DENIED": "Location permission denied",
    "PAYMENT_FAILED": "Payment processing failed",
    "SUBSCRIPTION_REQUIRED": "Premium subscription required",
    "INVALID_CREDENTIALS": "Invalid credentials",
    "USER_NOT_FOUND": "User not found",
    "EMAIL_EXISTS": "Email already registered",
}

# Pagination defaults
DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 100

# Timeouts (in seconds)
LOCATION_PERMISSION_TIMEOUT = 30
PAYMENT_TIMEOUT = 60
