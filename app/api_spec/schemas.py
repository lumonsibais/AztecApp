"""Schemas de RESPUESTA — la documentación del contrato.

No se usan para serializar: eso lo siguen haciendo los `to_dict()` de cada
modelo. Estos schemas describen lo que esos to_dict emiten, y existen por dos
razones:

  1. Generan el OpenAPI que consume el frontend.
  2. `tests/test_contract.py` valida contra ellos las respuestas REALES del
     servidor. Si un to_dict cambia y el schema no, el test se pone rojo.

Ese segundo punto es el que los hace fiables. Un spec escrito a mano y nunca
contrastado contra el servidor es documentación optimista; este se rompe en
cuanto deja de ser verdad.

Convención: campos que el servidor puede mandar como null llevan
`allow_none=True`; campos que solo aparecen con el desbloqueo NO son required,
porque en el teaser sencillamente no vienen en el objeto.
"""
from marshmallow import Schema, fields


# ---------------------------------------------------------------------------
# bloques compartidos
# ---------------------------------------------------------------------------

class LocationSchema(Schema):
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    neighborhood = fields.Str(allow_none=True)
    # Solo viene con número cuando la petición llevó coordenadas. Lo calcula
    # PostGIS, no el cliente.
    distanceKm = fields.Float(allow_none=True)


class BadgesSchema(Schema):
    freeEntry = fields.Bool(required=True)
    outdoor = fields.Bool(required=True)
    archaeological = fields.Bool(required=True)


class ContentAccessSchema(Schema):
    isLocked = fields.Bool(required=True)
    unlockedForViewer = fields.Bool(required=True)


class NearbyServicesSchema(Schema):
    bathrooms = fields.Bool(allow_none=True)
    cafes = fields.Bool(allow_none=True)
    hotels = fields.Bool(allow_none=True)


class EntryFeeSchema(Schema):
    """Lo que cobra el museo en su taquilla. No confundir con el desbloqueo.

    Viaja SIEMPRE, esté la ficha bloqueada o no: es un dato del mundo real que
    cualquiera encuentra en internet, y esconderlo solo saca al viajero de la
    app.
    """
    mxn = fields.Float(allow_none=True)
    usd = fields.Float(allow_none=True)
    text = fields.Str(allow_none=True)
    isFree = fields.Bool(required=True)


class HistoricalContextSchema(Schema):
    tenochtitlanName = fields.Str(allow_none=True)
    eraDescription = fields.Str(allow_none=True)


# ---------------------------------------------------------------------------
# places
# ---------------------------------------------------------------------------

class PlaceSchema(Schema):
    """Un sitio.

    Tres niveles de detalle en un mismo objeto:
      - listado: sin los bloques de logística ni de contenido
      - ficha bloqueada: + logística (entryFee, openingHours, howToGetThere)
      - ficha desbloqueada: + contenido (description, whyVisit, contexto)
    """
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    tagline = fields.Str(allow_none=True)
    # null cuando la ficha está bloqueada para quien mira.
    description = fields.Str(allow_none=True)
    location = fields.Nested(LocationSchema, required=True)
    placeType = fields.Str(allow_none=True)
    curation = fields.Str(allow_none=True, metadata={
        "enum": ["must_see", "quick_stop", None],
        "description": "Catálogo editorial. Alimenta los filtros de Explore.",
    })
    rating = fields.Float(allow_none=True, metadata={
        "description": "Valoración editorial nuestra, no media de usuarios.",
    })
    historicalSignificance = fields.Str(allow_none=True)
    estimatedVisitDuration = fields.Int(allow_none=True, metadata={
        "description": "Minutos. Ordena y filtra.",
    })
    visitDurationText = fields.Str(allow_none=True, metadata={
        "description": "Lo que se muestra: '2-4 hours'. Un entero no dice eso.",
    })
    imageUrl = fields.Str(allow_none=True)
    badges = fields.Nested(BadgesSchema, required=True)
    contentAccess = fields.Nested(ContentAccessSchema, required=True)
    nearbyServices = fields.Nested(NearbyServicesSchema, required=True)
    isSaved = fields.Bool(allow_none=True, metadata={
        "description": "El corazón. null sin sesión: no es false, es que no aplica.",
    })
    createdAt = fields.Str(allow_none=True)
    updatedAt = fields.Str(allow_none=True)

    # --- logística: solo en la ficha, pero sin depender del desbloqueo ---
    openingHours = fields.Str(allow_none=True)
    howToGetThere = fields.Str(allow_none=True)
    entryFee = fields.Nested(EntryFeeSchema)
    safetyRecommendations = fields.Str(allow_none=True)

    # --- contenido nuestro: solo con el desbloqueo ---
    whyVisit = fields.Str(allow_none=True)
    historicalContext = fields.Nested(HistoricalContextSchema)
    contentVerifiedAt = fields.Str(allow_none=True)


class PlaceListSchema(Schema):
    places = fields.List(fields.Nested(PlaceSchema), required=True)
    total = fields.Int()
    page = fields.Int()
    limit = fields.Int()
    count = fields.Int()


# ---------------------------------------------------------------------------
# tours
# ---------------------------------------------------------------------------

class TourAudioSchema(Schema):
    url = fields.Str(allow_none=True, metadata={
        "description": "null si la parada está bloqueada para quien mira.",
    })
    durationSeconds = fields.Int(allow_none=True)
    isLocked = fields.Bool(required=True)


class TourStopSchema(Schema):
    id = fields.Str(required=True)
    position = fields.Int(required=True, metadata={
        "description": "Orden del recorrido, empezando en 0.",
    })
    placeId = fields.Str(required=True)
    transitionText = fields.Str(allow_none=True)
    audio = fields.Nested(TourAudioSchema, required=True)
    place = fields.Nested(PlaceSchema)


class LastLocationSchema(Schema):
    latitude = fields.Float(allow_none=True)
    longitude = fields.Float(allow_none=True)


class TourProgressSchema(Schema):
    """El avance guardado. Lo devuelven /start, /progress y /complete.

    Devolver el objeto entero y no solo el id es deliberado: el cliente lee lo
    que el servidor guardó en vez de fiarse de lo que acaba de mandar. Con la
    app abierta en dos dispositivos, esa diferencia se nota.
    """
    id = fields.Str(required=True)
    tourId = fields.Str(required=True)
    currentStopIndex = fields.Int(allow_none=True)
    isCompleted = fields.Bool(required=True)
    rating = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)
    startedAt = fields.Str(allow_none=True)
    completedAt = fields.Str(allow_none=True)
    lastLocation = fields.Nested(LastLocationSchema, required=True)
    updatedAt = fields.Str(allow_none=True)


class UserTourProgressSchema(Schema):
    """El avance tal como viaja incrustado en cada tour de /tours/user/tours."""
    isCompleted = fields.Bool(required=True)
    currentStopIndex = fields.Int(allow_none=True)
    rating = fields.Int(allow_none=True)
    startedAt = fields.Str(allow_none=True)
    completedAt = fields.Str(allow_none=True)


class TourStatisticsSchema(Schema):
    views = fields.Int(allow_none=True)
    completions = fields.Int(allow_none=True)


class TourSchema(Schema):
    id = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    isFree = fields.Bool(allow_none=True)
    isLocked = fields.Bool(allow_none=True)
    unlockedForViewer = fields.Bool()
    estimatedDuration = fields.Int(allow_none=True)
    durationText = fields.Str(allow_none=True)
    difficultyLevel = fields.Str(allow_none=True)
    imageUrl = fields.Str(allow_none=True)
    totalDistance = fields.Float(allow_none=True)
    hasEntryFees = fields.Bool()
    stopsCount = fields.Int()
    includesAudio = fields.Bool()
    rating = fields.Float(allow_none=True)
    statistics = fields.Nested(TourStatisticsSchema)
    createdAt = fields.Str(allow_none=True)
    updatedAt = fields.Str(allow_none=True)

    contentDescription = fields.Str(allow_none=True, metadata={
        "description": "El guion. Solo con el desbloqueo.",
    })
    stops = fields.List(fields.Nested(TourStopSchema), metadata={
        "description": "Las paradas. Solo con el desbloqueo: el teaser conserva "
                       "stopsCount e includesAudio para poder pintar el candado.",
    })
    progress = fields.Nested(UserTourProgressSchema, metadata={
        "description": "Solo en GET /tours/user/tours. Es un bloque reducido: "
                       "el avance completo lo devuelven /start, /progress y "
                       "/complete.",
    })


class TourListSchema(Schema):
    tours = fields.List(fields.Nested(TourSchema), required=True)
    total = fields.Int()
    page = fields.Int()
    limit = fields.Int()
    count = fields.Int()


# ---------------------------------------------------------------------------
# historical
# ---------------------------------------------------------------------------

class HistoricalContentSchema(Schema):
    id = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    contentType = fields.Str(allow_none=True)
    era = fields.Str(allow_none=True)
    topic = fields.Str(allow_none=True)
    dateDescription = fields.Str(allow_none=True)
    readingTimeMinutes = fields.Int(allow_none=True)
    timelineId = fields.Str(allow_none=True)
    sortOrder = fields.Int(allow_none=True)
    placeId = fields.Str(allow_none=True)
    isLocked = fields.Bool(required=True)
    unlockedForViewer = fields.Bool(required=True)
    isRead = fields.Bool(allow_none=True, metadata={
        "description": "null sin sesión.",
    })
    author = fields.Str(allow_none=True)
    verified = fields.Bool(allow_none=True)
    createdAt = fields.Str(allow_none=True)

    nextContentId = fields.Str(allow_none=True, metadata={
        "description": "El botón Next de la cronología. Solo en el detalle.",
    })
    content = fields.Str(metadata={"description": "El texto. Solo desbloqueado."})
    audioUrl = fields.Str()
    videoUrl = fields.Str()
    sources = fields.Raw()


class TopicSchema(Schema):
    topic = fields.Str(required=True)
    count = fields.Int(required=True)


class TimelineSchema(Schema):
    id = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    sortOrder = fields.Int(allow_none=True)
    createdAt = fields.Str(allow_none=True)


class GeoJSONGeometrySchema(Schema):
    type = fields.Str(required=True, metadata={"enum": ["Polygon"]})
    coordinates = fields.Raw(required=True, metadata={
        "description": "Anillos de [longitud, latitud], como manda GeoJSON.",
    })


class LakeFeaturePropertiesSchema(Schema):
    name = fields.Str(required=True)
    surfaceType = fields.Str(required=True, metadata={
        "enum": ["water", "land"],
        "description": "Con qué color se pinta. El mapa de 1500 tiene lago azul "
                       "e islas en arena, y el color no se deduce del nombre.",
    })
    yearEstimate = fields.Int(allow_none=True)
    tenochtitlanName = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)


class LakeFeatureSchema(Schema):
    type = fields.Str(required=True, metadata={"enum": ["Feature"]})
    id = fields.Str(required=True)
    geometry = fields.Nested(GeoJSONGeometrySchema, required=True)
    properties = fields.Nested(LakeFeaturePropertiesSchema, required=True)


class LakeOverlaySchema(Schema):
    """FeatureCollection GeoJSON estándar, para pintarlo sin transformarlo.

    Los Features llegan en ORDEN DE PINTADO: el agua primero, la tierra encima.
    Con year=2026 llega vacía a propósito — el diseño enseña el mapa de Google
    sin capa, así que el overlay es lo que se añade al pasar a 1500.
    """
    type = fields.Str(required=True, metadata={"enum": ["FeatureCollection"]})
    features = fields.List(fields.Nested(LakeFeatureSchema), required=True)
    availableYears = fields.List(fields.Int(), metadata={
        "description": "Años que tienen geometría sembrada. Con esto la app "
                       "construye el conmutador en vez de llevar 1500 y 2026 "
                       "escritos a fuego.",
    })


# ---------------------------------------------------------------------------
# users y pagos
# ---------------------------------------------------------------------------

class UserStatsSchema(Schema):
    toursCompleted = fields.Int(required=True)
    placesVisited = fields.Int(required=True)


class UserSchema(Schema):
    id = fields.Str(required=True)
    email = fields.Email(required=True)
    firstName = fields.Str(allow_none=True)
    lastName = fields.Str(allow_none=True)
    avatarUrl = fields.Str(allow_none=True)
    preferredLocale = fields.Str(allow_none=True, metadata={
        # null entra en la lista porque el campo es nullable: una cuenta recién
        # creada todavía no ha elegido idioma y ahí manda Accept-Language.
        "enum": ["en", "es", None],
        "description": "Manda sobre Accept-Language y viaja entre dispositivos. "
                       "null mientras la cuenta no haya elegido en ajustes.",
    })
    hasFullAccess = fields.Bool(required=True)
    fullAccessSince = fields.Str(allow_none=True)
    locationPermissionStatus = fields.Str(allow_none=True)
    stats = fields.Nested(UserStatsSchema, required=True)
    isVerified = fields.Bool(allow_none=True)
    createdAt = fields.Str(allow_none=True)


class AuthSchema(Schema):
    accessToken = fields.Str(required=True)
    refreshToken = fields.Str(required=True)
    user = fields.Nested(UserSchema, required=True)


class AccessTokenSchema(Schema):
    accessToken = fields.Str(required=True)


class AccessStateSchema(Schema):
    """Lo que la app pregunta al abrir para saber si pinta candados."""
    hasFullAccess = fields.Bool(required=True)
    since = fields.Str(allow_none=True)
    product = fields.Str(required=True)
    price = fields.Float(required=True)
    currency = fields.Str(required=True)


class PurchaseSchema(Schema):
    id = fields.Str(required=True)
    product = fields.Str(required=True)
    provider = fields.Str(allow_none=True)
    amount = fields.Float(required=True)
    currency = fields.Str(required=True)
    status = fields.Str(required=True, metadata={
        "enum": ["pending", "completed", "failed", "refunded"],
    })
    purchasedAt = fields.Str(allow_none=True)
    createdAt = fields.Str(allow_none=True)


class PurchaseListSchema(Schema):
    purchases = fields.List(fields.Nested(PurchaseSchema), required=True)


class LocationPermissionSchema(Schema):
    locationPermissionStatus = fields.Str(allow_none=True)
    lastPrompted = fields.Str(allow_none=True)


# ---------------------------------------------------------------------------
# peticiones
# ---------------------------------------------------------------------------

class RegisterRequestSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, metadata={"minLength": 8})
    firstName = fields.Str()
    lastName = fields.Str()


class LoginRequestSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class ProfileUpdateRequestSchema(Schema):
    """Solo estos campos. Cualquier otro devuelve 400.

    La lista blanca es deliberada: antes un PUT con has_full_access se
    concedía el desbloqueo solo.
    """
    firstName = fields.Str()
    lastName = fields.Str()
    avatarUrl = fields.Str()
    preferredLocale = fields.Str(metadata={"enum": ["en", "es"]})


class LocationPermissionRequestSchema(Schema):
    response = fields.Str(required=True, metadata={"enum": ["granted", "denied"]})
    context = fields.Str(allow_none=True)


class TourProgressUpdateRequestSchema(Schema):
    currentStopIndex = fields.Int()
    lastLocationLat = fields.Float()
    lastLocationLon = fields.Float()
    notes = fields.Str()


class TourCompleteRequestSchema(Schema):
    rating = fields.Int(metadata={"minimum": 1, "maximum": 5})
    notes = fields.Str()


class PurchaseConfirmRequestSchema(Schema):
    provider = fields.Str(required=True, metadata={
        "enum": ["stripe", "apple", "google", "manual"],
    })
    externalId = fields.Str(required=True, metadata={
        "description": "La referencia del proveedor. Se verifica contra él "
                       "antes de conceder nada; no se cree por venir aquí.",
    })


# ---------------------------------------------------------------------------
# errores
# ---------------------------------------------------------------------------

class ErrorSchema(Schema):
    success = fields.Bool(required=True, metadata={"enum": [False]})
    error = fields.Str(required=True)
    details = fields.Raw(metadata={
        "description": "Errores por campo cuando la validación falla.",
    })
