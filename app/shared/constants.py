"""Shared constants across the application"""

# --------------------------------------------------------------------------
# Modelo de acceso
# --------------------------------------------------------------------------
# El producto vende UN desbloqueo: 15 USD que abren todo el contenido, para
# siempre. No hay niveles ni mensualidad. Lo que antes era una escala de tres
# tiers con caducidad es ahora un permiso binario en la cuenta.
FULL_ACCESS_PRICE_USD = 15.00
FULL_ACCESS_PRODUCT = "full_access"

# Proveedores de cobro admitidos. Cuál se usa está por decidir —tiendas o
# pasarela propia—, así que el resto del backend no consulta esto: mira el
# permiso de la cuenta. Esto solo describe de dónde vino el dinero.
PROVIDER_STRIPE = "stripe"
PROVIDER_APPLE = "apple"
PROVIDER_GOOGLE = "google"
PROVIDER_MANUAL = "manual"          # altas a mano: pruebas, cortesías, soporte
PROVIDERS = (PROVIDER_STRIPE, PROVIDER_APPLE, PROVIDER_GOOGLE, PROVIDER_MANUAL)

PURCHASE_PENDING = "pending"
PURCHASE_COMPLETED = "completed"
PURCHASE_FAILED = "failed"
PURCHASE_REFUNDED = "refunded"

# --------------------------------------------------------------------------
# Curación editorial
# --------------------------------------------------------------------------
# "Must See" y "Quick Stops" no son tipos de sitio: son listas que mantiene el
# equipo a mano. Por eso viven en su propia columna y no en place_type.
CURATION_MUST_SEE = "must_see"
CURATION_QUICK_STOP = "quick_stop"
CURATIONS = (CURATION_MUST_SEE, CURATION_QUICK_STOP)

# --------------------------------------------------------------------------
# Monedas
# --------------------------------------------------------------------------
# Las entradas de museos se cobran en pesos y el desbloqueo de la app en
# dólares. Son dos importes distintos y hay que poder mostrar los dos.
CURRENCY_USD = "USD"
CURRENCY_MXN = "MXN"

# Location
LOCATION_PROXIMITY_RADIUS = 5  # km
TENOCHTITLAN_CENTER_LAT = 19.4326
TENOCHTITLAN_CENTER_LON = -99.1332

# Épocas del conmutador del mapa: el overlay salta entre el lago de 1500 y la
# ciudad actual, no se enciende y se apaga.
#
# El año presente NO tiene geometría, y eso no es un pendiente: en el diseño,
# con "2026" seleccionado se ve el mapa de Google tal cual, sin capa encima.
# El overlay es lo que se AÑADE al pasar a 1500.
ERA_HISTORIC_YEAR = 1500
ERA_PRESENT_YEAR = 2026

# Cada polígono del overlay es agua o tierra: el mapa de 1500 pinta el lago en
# azul y las islas en arena, y el color lo decide este campo, no el nombre del
# polígono.
SURFACE_WATER = "water"
SURFACE_LAND = "land"
SURFACES = (SURFACE_WATER, SURFACE_LAND)

# Features
LAKE_VIEW_ENABLED = True
HISTORICAL_OVERLAY_ENABLED = True

MAX_FREE_TOURS = 3

# Error messages
ERROR_MESSAGES = {
    "UNAUTHORIZED": "Unauthorized access",
    "NOT_FOUND": "Resource not found",
    "VALIDATION_ERROR": "Validation error",
    "INTERNAL_ERROR": "Internal server error",
    "LOCATION_PERMISSION_DENIED": "Location permission denied",
    "PAYMENT_FAILED": "Payment processing failed",
    "ACCESS_REQUIRED": "Full access required",
    "INVALID_CREDENTIALS": "Invalid credentials",
    "USER_NOT_FOUND": "User not found",
    "EMAIL_EXISTS": "Email already registered",
    "ACCOUNT_DISABLED": "Account is disabled",
    "TOKEN_REVOKED": "Token has been revoked",
    "ALREADY_PURCHASED": "This account already has full access",
    "ALREADY_SAVED": "Place already saved",
}

# Pagination defaults
DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 100

# Timeouts (in seconds)
LOCATION_PERMISSION_TIMEOUT = 30
PAYMENT_TIMEOUT = 60
