"""Generación del OpenAPI.

Por qué apispec y no flask-smorest, que era el plan original: smorest devuelve
el objeto serializado por el schema TAL CUAL, y esta API envuelve todo en
`{success, data}`. Migrar a smorest obligaría a crear un schema-envoltorio por
endpoint y a tocar los 36 controllers —que hoy funcionan y están cubiertos por
88 tests— justo en la operación cuyo objetivo es CONGELAR el contrato. Cambiar
el código para documentarlo es al revés.

apispec genera el mismo documento sin tocar una sola ruta. Lo que smorest te
da gratis —la garantía de que el spec y el código no divergen— aquí lo da
`tests/test_contract.py`, que valida las respuestas reales contra este spec. Es
una garantía más fuerte: smorest asegura que el spec coincide con los
decoradores, no que los decoradores coincidan con la realidad.

Se emite OpenAPI 3.0.3 y no 3.1 porque el consumidor es el generador de código
Dart, cuyo soporte de 3.1 sigue siendo irregular. El spec es para que el
frontend genere su capa de datos, no para lucir versión.
"""
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from app.api_spec import schemas as s

OPENAPI_VERSION = "3.0.3"
API_VERSION = "1.0.0"

DESCRIPCION = """
API de AztecApp Explorer.

**El sobre.** Todas las respuestas viajan envueltas: `{"success": true, "data": {...}}`
en el camino feliz y `{"success": false, "error": "...", "details": {...}}` cuando algo
falla. El cliente debe desenvolver `data`.

**Acceso.** El producto vende un DESBLOQUEO ÚNICO de 15 USD que no caduca; no hay
niveles ni suscripción. Los endpoints públicos aceptan token opcional: sin él —o con
uno revocado— responden 200 con el contenido en versión teaser, no 401. Eso es
deliberado: la app tiene que poder pintar el candado.

**Qué se paga y qué no.** La logística de cada sitio (tarifa de taquilla, horarios,
cómo llegar, avisos de seguridad) viaja SIEMPRE: son datos del mundo real y esconderlos
solo manda al viajero a buscarlos fuera. Lo que va detrás del desbloqueo es lo que
escribimos nosotros: descripciones, `whyVisit`, contexto histórico y el audio de los
tours.

**Idioma.** `Accept-Language` se compara por prefijo de dos letras (`es-MX` → `es`).
El idioma base es el inglés y vive en las columnas del modelo; el español entra por la
tabla de traducciones. Si una cuenta tiene `preferredLocale`, manda sobre la cabecera.
""".strip()

TAGS = [
    {"name": "users", "description": "Cuentas, sesión y perfil."},
    {"name": "places", "description": "Sitios: Explore, Near y Saved."},
    {"name": "tours", "description": "Recorridos autoguiados y su avance."},
    {"name": "historical", "description": "Guía histórica y overlay del lago."},
    {"name": "payments", "description": "El desbloqueo único."},
]


def _sobre(nombre, data_schema, descripcion=None):
    """Envuelve un schema de datos en el sobre {success, data}."""
    contenido = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {"$ref": f"#/components/schemas/{data_schema}"},
            "message": {"type": "string"},
        },
        "required": ["success", "data"],
    }
    if descripcion:
        contenido["description"] = descripcion
    return {nombre: contenido}


# --- respuestas de error reutilizables -------------------------------------

def _err(descripcion):
    return {
        "description": descripcion,
        "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/Error"}
        }},
    }


def _ok(descripcion, envoltorio):
    return {
        "description": descripcion,
        "content": {"application/json": {
            "schema": {"$ref": f"#/components/schemas/{envoltorio}"}
        }},
    }


def _body(schema):
    return {
        "required": True,
        "content": {"application/json": {
            "schema": {"$ref": f"#/components/schemas/{schema}"}
        }},
    }


P_ACCEPT_LANGUAGE = {
    "name": "Accept-Language", "in": "header", "required": False,
    "schema": {"type": "string", "example": "es-MX"},
    "description": "Se compara por prefijo de dos letras. Soportados: en, es.",
}
P_PAGE = {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}}
P_LIMIT = {"name": "limit", "in": "query",
           "schema": {"type": "integer", "default": 10, "maximum": 100}}
P_CURATION = {
    "name": "curation", "in": "query",
    "schema": {"type": "string", "enum": ["must_see", "quick_stop"]},
    "description": "Filtros de la barra de Explore. Un valor desconocido se ignora.",
}
P_LAT = {"name": "latitude", "in": "query", "required": True,
         "schema": {"type": "number", "format": "double"}}
P_LON = {"name": "longitude", "in": "query", "required": True,
         "schema": {"type": "number", "format": "double"}}
P_RADIUS = {"name": "radius", "in": "query",
            "schema": {"type": "number", "default": 5},
            "description": "Kilómetros."}

AUTH = [{"bearerAuth": []}]

# Token OPCIONAL. El `{}` vacío es como OpenAPI dice "también vale sin
# autenticación": sin él, un mock que respete el spec —Prism lo hace— devuelve
# 401 en endpoints que la app tiene que poder llamar sin sesión, y el frontend
# se pasa la tarde persiguiendo un fantasma.
AUTH_OPCIONAL = [{}, {"bearerAuth": []}]

AUTH_OPCIONAL_DESC = (
    "Token opcional: sin él la respuesta llega en versión teaser, con 200."
)


def build_spec() -> APISpec:
    spec = APISpec(
        title="AztecApp Explorer API",
        version=API_VERSION,
        openapi_version=OPENAPI_VERSION,
        plugins=[MarshmallowPlugin()],
        info={"description": DESCRIPCION},
        servers=[
            # 5001 y no 5000: en las máquinas del equipo el 5000 ya lo tiene
            # iBet, y en macOS también AirPlay Receiver.
            {"url": "http://localhost:5001", "description": "Backend local"},
            {"url": "http://localhost:4010", "description": "Mock de Prism"},
        ],
        tags=TAGS,
    )

    spec.components.security_scheme("bearerAuth", {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
    })

    for nombre, esquema in [
        ("Location", s.LocationSchema), ("Badges", s.BadgesSchema),
        ("ContentAccess", s.ContentAccessSchema),
        ("NearbyServices", s.NearbyServicesSchema),
        ("EntryFee", s.EntryFeeSchema),
        ("HistoricalContext", s.HistoricalContextSchema),
        ("Place", s.PlaceSchema), ("PlaceList", s.PlaceListSchema),
        ("TourAudio", s.TourAudioSchema), ("TourStop", s.TourStopSchema),
        ("TourProgress", s.TourProgressSchema),
        ("TourStatistics", s.TourStatisticsSchema),
        ("Tour", s.TourSchema), ("TourList", s.TourListSchema),
        ("HistoricalContent", s.HistoricalContentSchema),
        ("Topic", s.TopicSchema), ("Timeline", s.TimelineSchema),
        ("GeoJSONGeometry", s.GeoJSONGeometrySchema),
        ("LakeFeatureProperties", s.LakeFeaturePropertiesSchema),
        ("LakeFeature", s.LakeFeatureSchema),
        ("LakeOverlay", s.LakeOverlaySchema),
        ("UserStats", s.UserStatsSchema), ("User", s.UserSchema),
        ("Auth", s.AuthSchema), ("AccessToken", s.AccessTokenSchema),
        ("AccessState", s.AccessStateSchema), ("Purchase", s.PurchaseSchema),
        ("PurchaseList", s.PurchaseListSchema),
        ("LocationPermission", s.LocationPermissionSchema),
        ("RegisterRequest", s.RegisterRequestSchema),
        ("LoginRequest", s.LoginRequestSchema),
        ("ProfileUpdateRequest", s.ProfileUpdateRequestSchema),
        ("LocationPermissionRequest", s.LocationPermissionRequestSchema),
        ("TourProgressUpdateRequest", s.TourProgressUpdateRequestSchema),
        ("TourCompleteRequest", s.TourCompleteRequestSchema),
        ("PurchaseConfirmRequest", s.PurchaseConfirmRequestSchema),
        ("Error", s.ErrorSchema),
    ]:
        spec.components.schema(nombre, schema=esquema)

    # Envoltorios: uno por forma de `data`.
    envoltorios = {}
    for nombre, data in [
        ("PlaceResponse", "Place"), ("PlaceListResponse", "PlaceList"),
        ("TourResponse", "Tour"), ("TourListResponse", "TourList"),
        ("TourProgressResponse", "TourProgress"),
        ("HistoricalContentResponse", "HistoricalContent"),
        ("UserResponse", "User"), ("AuthResponse", "Auth"),
        ("AccessTokenResponse", "AccessToken"),
        ("AccessStateResponse", "AccessState"),
        ("PurchaseResponse", "Purchase"),
        ("PurchaseListResponse", "PurchaseList"),
        ("LakeOverlayResponse", "LakeOverlay"),
        ("LocationPermissionResponse", "LocationPermission"),
    ]:
        envoltorios.update(_sobre(nombre, data))

    envoltorios["ContentListResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "content": {"type": "array", "items": {
                        "$ref": "#/components/schemas/HistoricalContent"}},
                    "count": {"type": "integer"},
                },
                "required": ["content"],
            },
        },
        "required": ["success", "data"],
    }
    envoltorios["TopicListResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "topics": {"type": "array", "items": {
                        "$ref": "#/components/schemas/Topic"}},
                },
                "required": ["topics"],
            },
        },
        "required": ["success", "data"],
    }
    envoltorios["TimelineListResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "timelines": {"type": "array", "items": {
                        "$ref": "#/components/schemas/Timeline"}},
                },
                "required": ["timelines"],
            },
        },
        "required": ["success", "data"],
    }
    envoltorios["UserTourListResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "tours": {"type": "array", "items": {
                        "$ref": "#/components/schemas/Tour"}},
                    "count": {"type": "integer"},
                },
                "required": ["tours"],
            },
        },
        "required": ["success", "data"],
    }
    envoltorios["MessageResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "message": {"type": "string"},
            "data": {"type": "object", "nullable": True},
        },
        "required": ["success"],
    }

    for nombre, definicion in envoltorios.items():
        spec.components.schema(nombre, definicion)

    _rutas(spec)
    return spec


def _rutas(spec):
    # ---------------- users ----------------
    spec.path(path="/api/users/register", operations={"post": {
        "tags": ["users"], "summary": "Crear una cuenta",
        "description": "Cuenta completa con contraseña. Devuelve la pareja de "
                       "tokens ya lista, sin obligar a un login extra.",
        "requestBody": _body("RegisterRequest"),
        "responses": {
            "201": _ok("Cuenta creada", "AuthResponse"),
            "400": _err("Email inválido o contraseña de menos de 8 caracteres"),
            "409": _err("El email ya está registrado"),
        }}})

    spec.path(path="/api/users/login", operations={"post": {
        "tags": ["users"], "summary": "Iniciar sesión",
        "requestBody": _body("LoginRequest"),
        "responses": {
            "200": _ok("Sesión iniciada", "AuthResponse"),
            "401": _err("Credenciales inválidas o cuenta desactivada"),
        }}})

    spec.path(path="/api/users/refresh", operations={"post": {
        "tags": ["users"], "summary": "Renovar el access token",
        "description": "Requiere el REFRESH token en la cabecera. Un access "
                       "token aquí responde 401.",
        "security": AUTH,
        "responses": {
            "200": _ok("Token nuevo", "AccessTokenResponse"),
            "401": _err("Falta el refresh token, o se mandó un access token"),
        }}})

    spec.path(path="/api/users/logout", operations={"post": {
        "tags": ["users"], "summary": "Cerrar sesión",
        "description": "Mete el jti en la blocklist: el token deja de valer al "
                       "instante, no cuando caduque.",
        "security": AUTH,
        "responses": {"200": _ok("Sesión cerrada", "MessageResponse"),
                      "401": _err("Sin token")}}})

    spec.path(path="/api/users/profile", operations={
        "get": {
            "tags": ["users"], "summary": "Perfil de la cuenta",
            "security": AUTH,
            "responses": {"200": _ok("Perfil", "UserResponse"),
                          "401": _err("Sin token o token revocado"),
                          "403": _err("Cuenta desactivada")}},
        "put": {
            "tags": ["users"], "summary": "Editar el perfil",
            "description": "Lista blanca estricta. Un campo fuera de ella "
                           "devuelve 400 en vez de ignorarse en silencio.",
            "security": AUTH,
            "requestBody": _body("ProfileUpdateRequest"),
            "responses": {"200": _ok("Perfil actualizado", "UserResponse"),
                          "400": _err("Campo no editable o valor inválido"),
                          "401": _err("Sin token")}}})

    spec.path(path="/api/users/location-permission", operations={"post": {
        "tags": ["users"], "summary": "Registrar la respuesta al permiso de ubicación",
        "security": AUTH,
        "requestBody": _body("LocationPermissionRequest"),
        "responses": {"200": _ok("Registrado", "MessageResponse"),
                      "400": _err("Valor inválido"), "401": _err("Sin token")}}})

    # ---------------- places ----------------
    spec.path(path="/api/places/", operations={"get": {
        "tags": ["places"], "summary": "Listado de sitios (pestaña Explore)",
        "description": AUTH_OPCIONAL_DESC + " Con sesión, cada sitio trae "
                       "`isSaved` resuelto en la misma consulta.",
        "security": AUTH_OPCIONAL,
        "parameters": [P_PAGE, P_LIMIT, P_CURATION, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Sitios", "PlaceListResponse")}}})

    spec.path(path="/api/places/nearby", operations={"get": {
        "tags": ["places"], "summary": "Sitios cercanos, con distancia",
        "description": "Ordenados por cercanía con ST_DWithin y ST_Distance. La "
                       "distancia llega calculada en `location.distanceKm`: no "
                       "la recalcules en el cliente.",
        "security": AUTH_OPCIONAL,
        "parameters": [P_LAT, P_LON, P_RADIUS, P_CURATION, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Sitios cercanos", "PlaceListResponse"),
                      "400": _err("Faltan latitude o longitude")}}})

    spec.path(path="/api/places/recommended", operations={"get": {
        "tags": ["places"], "summary": "Sitios recomendados alrededor",
        "security": AUTH_OPCIONAL,
        "parameters": [P_LAT, P_LON, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Recomendados", "PlaceListResponse"),
                      "400": _err("Faltan coordenadas")}}})

    spec.path(path="/api/places/saved", operations={"get": {
        "tags": ["places"], "summary": "Sitios guardados (pestaña Saved)",
        "security": AUTH,
        "parameters": [P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Guardados", "PlaceListResponse"),
                      "401": _err("Sin token")}}})

    spec.path(path="/api/places/{place_id}", operations={"get": {
        "tags": ["places"], "summary": "Ficha de un sitio",
        "description": "Bloqueada: llegan metadata y logística, no el contenido. "
                       "Desbloqueada: llega todo.",
        "security": AUTH_OPCIONAL,
        "parameters": [
            {"name": "place_id", "in": "path", "required": True,
             "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Ficha", "PlaceResponse"),
                      "404": _err("No existe")}}})

    spec.path(path="/api/places/{place_id}/save", operations={
        "post": {
            "tags": ["places"], "summary": "Guardar un sitio",
            "description": "Idempotente: guardarlo dos veces no duplica nada.",
            "security": AUTH,
            "parameters": [{"name": "place_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "responses": {"201": _ok("Guardado", "MessageResponse"),
                          "401": _err("Sin token"), "404": _err("No existe")}},
        "delete": {
            "tags": ["places"], "summary": "Quitar un sitio de guardados",
            "security": AUTH,
            "parameters": [{"name": "place_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "responses": {"200": _ok("Quitado", "MessageResponse"),
                          "401": _err("Sin token"), "404": _err("No estaba guardado")}}})

    # ---------------- tours ----------------
    spec.path(path="/api/tours/", operations={"get": {
        "tags": ["tours"], "summary": "Listado de tours",
        "description": "Los bloqueados salen como teaser en vez de desaparecer: "
                       "si no, nadie llega a ver qué ofrece pagar.",
        "security": AUTH_OPCIONAL,
        "parameters": [P_PAGE, P_LIMIT, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Tours", "TourListResponse")}}})

    spec.path(path="/api/tours/free", operations={"get": {
        "tags": ["tours"], "summary": "Tours gratuitos",
        "responses": {"200": _ok("Tours gratuitos", "TourListResponse")}}})

    spec.path(path="/api/tours/user/tours", operations={"get": {
        "tags": ["tours"], "summary": "Mis tours, con su avance",
        "security": AUTH,
        "parameters": [P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Tours empezados", "UserTourListResponse"),
                      "401": _err("Sin token")}}})

    spec.path(path="/api/tours/{tour_id}", operations={"get": {
        "tags": ["tours"], "summary": "Ficha de un tour",
        "description": "`stops` solo viaja con el desbloqueo. El teaser conserva "
                       "`stopsCount` e `includesAudio` para pintar el candado.",
        "security": AUTH_OPCIONAL,
        "parameters": [{"name": "tour_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Ficha del tour", "TourResponse"),
                      "404": _err("No existe")}}})

    spec.path(path="/api/tours/{tour_id}/start", operations={"post": {
        "tags": ["tours"], "summary": "Empezar un tour",
        "description": "403 si el tour es de pago y la cuenta no tiene el "
                       "desbloqueo. Repetirlo devuelve el progreso existente.",
        "security": AUTH,
        "parameters": [{"name": "tour_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}],
        "responses": {"201": _ok("Tour iniciado", "TourProgressResponse"),
                      "401": _err("Sin token"),
                      "403": _err("Hace falta el desbloqueo"),
                      "404": _err("No existe")}}})

    spec.path(path="/api/tours/{tour_id}/progress", operations={"put": {
        "tags": ["tours"], "summary": "Reportar avance",
        "description": "`isCompleted` NO se acepta aquí: cerrar un tour pasa por "
                       "/complete. Mandarlo devuelve 400.\n\n"
                       "Devuelve el avance COMPLETO tal como quedó guardado, "
                       "no solo un id: el cliente lee el estado del servidor "
                       "en vez de fiarse del que acaba de mandar.",
        "security": AUTH,
        "parameters": [{"name": "tour_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}],
        "requestBody": _body("TourProgressUpdateRequest"),
        "responses": {"200": _ok("Avance guardado", "TourProgressResponse"),
                      "400": _err("Campo no permitido"),
                      "401": _err("Sin token"),
                      "404": _err("El tour no está empezado")}}})

    spec.path(path="/api/tours/{tour_id}/complete", operations={"post": {
        "tags": ["tours"], "summary": "Cerrar un tour",
        "description": "Mueve los contadores del perfil y del propio tour.",
        "security": AUTH,
        "parameters": [{"name": "tour_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}],
        "requestBody": _body("TourCompleteRequest"),
        "responses": {"200": _ok("Tour cerrado", "TourProgressResponse"),
                      "401": _err("Sin token"),
                      "404": _err("El tour no está empezado")}}})

    # ---------------- historical ----------------
    spec.path(path="/api/historical/chronology", operations={"get": {
        "tags": ["historical"], "summary": "Cronología, en orden",
        "security": AUTH_OPCIONAL,
        "parameters": [
            {"name": "timelineId", "in": "query", "schema": {"type": "string"}},
            P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículos ordenados", "ContentListResponse")}}})

    spec.path(path="/api/historical/topics", operations={"get": {
        "tags": ["historical"], "summary": "Temas con su número de artículos",
        "responses": {"200": _ok("Temas", "TopicListResponse")}}})

    spec.path(path="/api/historical/content", operations={"get": {
        "tags": ["historical"], "summary": "Todos los artículos",
        "security": AUTH_OPCIONAL,
        "parameters": [
            {"name": "contentType", "in": "query", "schema": {"type": "string"}},
            P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículos", "ContentListResponse")}}})

    spec.path(path="/api/historical/content/topic", operations={"get": {
        "tags": ["historical"], "summary": "Artículos de un tema",
        "security": AUTH_OPCIONAL,
        "parameters": [
            {"name": "topic", "in": "query", "required": True,
             "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículos", "ContentListResponse"),
                      "400": _err("Falta el tema")}}})

    spec.path(path="/api/historical/content/era", operations={"get": {
        "tags": ["historical"], "summary": "Artículos de una época",
        "security": AUTH_OPCIONAL,
        "parameters": [
            {"name": "era", "in": "query", "required": True,
             "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículos", "ContentListResponse"),
                      "400": _err("Falta la época")}}})

    spec.path(path="/api/historical/content/place/{place_id}", operations={"get": {
        "tags": ["historical"], "summary": "Artículos ligados a un sitio",
        "security": AUTH_OPCIONAL,
        "parameters": [{"name": "place_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículos", "ContentListResponse")}}})

    spec.path(path="/api/historical/content/{content_id}", operations={"get": {
        "tags": ["historical"], "summary": "Un artículo",
        "description": "Sin el desbloqueo llega la ficha sin cuerpo: título, de "
                       "qué va y cuánto se tarda, pero no el texto. "
                       "`nextContentId` alimenta el botón Next.",
        "security": AUTH_OPCIONAL,
        "parameters": [{"name": "content_id", "in": "path", "required": True,
                        "schema": {"type": "string"}}, P_ACCEPT_LANGUAGE],
        "responses": {"200": _ok("Artículo", "HistoricalContentResponse"),
                      "404": _err("No existe")}}})

    spec.path(path="/api/historical/content/{content_id}/read", operations={
        "post": {
            "tags": ["historical"], "summary": "Marcar como leído",
            "security": AUTH,
            "parameters": [{"name": "content_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "responses": {"200": _ok("Marcado", "MessageResponse"),
                          "401": _err("Sin token"), "404": _err("No existe")}},
        "delete": {
            "tags": ["historical"], "summary": "Desmarcar",
            "security": AUTH,
            "parameters": [{"name": "content_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "responses": {"200": _ok("Desmarcado", "MessageResponse"),
                          "401": _err("Sin token"), "404": _err("No estaba marcado")}}})

    spec.path(path="/api/historical/timelines", operations={"get": {
        "tags": ["historical"], "summary": "Cronologías disponibles",
        "responses": {"200": _ok("Cronologías", "TimelineListResponse")}}})

    spec.path(path="/api/historical/lake-view", operations={"get": {
        "tags": ["historical"], "summary": "Overlay del lago de Tenochtitlan",
        "description": (
            "FeatureCollection GeoJSON, lista para pintar sin transformarla.\n\n"
            "Los Features llegan en ORDEN DE PINTADO: primero el agua, encima la "
            "tierra. Cada uno declara su `surfaceType` (`water` o `land`), que es "
            "lo que decide el color — no lo deduzcas del nombre.\n\n"
            "`year=2026` devuelve la colección VACÍA a propósito: el diseño enseña "
            "el mapa de Google sin capa, y el overlay es lo que se añade al pasar "
            "a 1500."
        ),
        "parameters": [
            {"name": "year", "in": "query",
             "schema": {"type": "integer", "enum": [1500, 2026]},
             "description": "El conmutador del mapa."},
            {"name": "bbox", "in": "query", "schema": {"type": "string"},
             "example": "-99.2,19.3,-99.0,19.5",
             "description": "minLon,minLat,maxLon,maxLat. Recorta con "
                            "ST_Intersects: un polígono que entra por una "
                            "esquina también se devuelve."},
        ],
        "responses": {"200": _ok("Overlay", "LakeOverlayResponse"),
                      "400": _err("bbox mal formado")}}})

    # ---------------- payments ----------------
    spec.path(path="/api/payments/access", operations={"get": {
        "tags": ["payments"], "summary": "¿Tiene esta cuenta el desbloqueo?",
        "description": "Lo que la app consulta al abrir para saber si pinta candados.",
        "security": AUTH,
        "responses": {"200": _ok("Estado de acceso", "AccessStateResponse"),
                      "401": _err("Sin token")}}})

    spec.path(path="/api/payments/purchases", operations={"get": {
        "tags": ["payments"], "summary": "Historial de compras",
        "security": AUTH,
        "responses": {"200": _ok("Compras", "PurchaseListResponse"),
                      "401": _err("Sin token")}}})

    spec.path(path="/api/payments/checkout", operations={"post": {
        "tags": ["payments"], "summary": "Abrir una compra",
        "description": "Devuelve la compra pendiente para arrancar el pago. "
                       "Llamarlo dos veces devuelve la MISMA, no crea otra. "
                       "409 si la cuenta ya tiene el desbloqueo: no caduca, así "
                       "que una segunda compra siempre es un error.",
        "security": AUTH,
        "responses": {"201": _ok("Compra abierta", "PurchaseResponse"),
                      "401": _err("Sin token"),
                      "409": _err("La cuenta ya tiene acceso")}}})

    spec.path(path="/api/payments/confirm", operations={"post": {
        "tags": ["payments"], "summary": "Confirmar el cobro y conceder el acceso",
        "description": "Idempotente por (provider, externalId): un webhook "
                       "repetido encuentra la compra en vez de duplicarla.\n\n"
                       "**501 mientras la pasarela no esté implementada.** "
                       "Aceptar un recibo sin comprobarlo contra el proveedor "
                       "sería regalar el contenido a cualquiera que mande una "
                       "petición inventada.",
        "security": AUTH,
        "requestBody": _body("PurchaseConfirmRequest"),
        "responses": {"200": _ok("Acceso concedido", "PurchaseResponse"),
                      "400": _err("Cuerpo inválido"),
                      "401": _err("Sin token"),
                      "501": _err("El proveedor todavía no verifica cobros")}}})
