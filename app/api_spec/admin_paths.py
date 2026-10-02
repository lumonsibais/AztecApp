"""Las rutas de administración, en el mismo documento que las públicas.

Podrían vivir en un OpenAPI aparte, y se consideró. Van juntas por una razón
concreta: `tests/test_contract.py` comprueba que NINGUNA ruta de la aplicación
quede sin documentar, y ese test es la red que evita que el contrato mienta.
Sacar un prefijo entero a otro archivo significaría exceptuarlo de esa
comprobación, y una excepción es exactamente donde se cuela la siguiente ruta
sin documentar.

Van con la etiqueta `admin`, así que en cualquier visor quedan agrupadas y
separadas de lo que consume la app.

Los cuerpos de petición se generan desde los schemas de `app/admin/schemas.py`,
que son los mismos que validan de verdad. Escribirlos otra vez aquí sería
tener dos descripciones del mismo formulario, y la que se quedaría vieja es
siempre la de la documentación.
"""
from app.admin import schemas as adm

AUTH = [{"bearerAuth": []}]

# 404 y no 403 para quien no es administrador: un 403 confirma que la ruta
# existe, y esta parte de la API no tiene por qué ser descubrible desde la app.
_NO_ADMIN = (
    "Requiere una cuenta de administrador. Quien no lo sea recibe **404**, no "
    "403: confirmar la existencia de la ruta no aporta nada y sí ayuda a quien "
    "esté buscando por dónde entrar."
)


def _err(descripcion):
    return {
        "description": descripcion,
        "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/Error"}}},
    }


def _ok(descripcion, envoltorio):
    return {
        "description": descripcion,
        "content": {"application/json": {
            "schema": {"$ref": f"#/components/schemas/{envoltorio}"}}},
    }


def _body(schema):
    return {
        "required": True,
        "content": {"application/json": {
            "schema": {"$ref": f"#/components/schemas/{schema}"}}},
    }


SCHEMAS = [
    ("AdminPlaceCrear", adm.PlaceCrearSchema),
    ("AdminPlaceActualizar", adm.PlaceActualizarSchema),
    ("AdminTourCrear", adm.TourCrearSchema),
    ("AdminTourActualizar", adm.TourActualizarSchema),
    ("AdminContenidoCrear", adm.ContenidoCrearSchema),
    ("AdminContenidoActualizar", adm.ContenidoActualizarSchema),
    ("AdminLakeGeometria", adm.LakeGeometriaSchema),
]

ENVOLTORIOS = {
    "AdminPlaceListResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "places": {"type": "array", "items": {
                        "$ref": "#/components/schemas/Place"}},
                    "count": {"type": "integer"},
                    "drafts": {"type": "integer", "description":
                               "Cuántos están sin publicar."},
                },
                "required": ["places"],
            },
        },
        "required": ["success", "data"],
    },
    "AdminLakeListResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "data": {
                "type": "object",
                "properties": {
                    "geometries": {"type": "array", "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "surfaceType": {"type": "string",
                                            "enum": ["water", "land"]},
                            "yearEstimate": {"type": "integer", "nullable": True},
                            "tenochtitlanName": {"type": "string", "nullable": True},
                            "description": {"type": "string", "nullable": True},
                        },
                    }},
                    "count": {"type": "integer"},
                },
                "required": ["geometries"],
            },
        },
        "required": ["success", "data"],
    },
    "AdminLakeCreadaResponse": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "message": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "surfaceType": {"type": "string"},
                },
                "required": ["id"],
            },
        },
        "required": ["success", "data"],
    },
}


def registrar(spec):
    """Añade componentes y rutas de administración al documento."""
    for nombre, esquema in SCHEMAS:
        spec.components.schema(nombre, schema=esquema)

    for nombre, definicion in ENVOLTORIOS.items():
        spec.components.schema(nombre, definicion)

    # ---------------- sitios ----------------
    spec.path(path="/api/admin/places", operations={
        "get": {
            "tags": ["admin"], "summary": "Catálogo completo, borradores incluidos",
            "description": "Al revés que el listado público: lo primero que "
                           "necesita ver quien carga contenido es lo que "
                           "tiene a medias.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "responses": {"200": _ok("Catálogo", "AdminPlaceListResponse"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador")}},
        "post": {
            "tags": ["admin"], "summary": "Crear un sitio",
            "description": "Nace **en borrador**: no aparece en Explore hasta "
                           "que se publica. El `id` lo pone quien escribe y "
                           "tiene que ser legible (`templo-mayor`), porque "
                           "acaba en las URLs.\n\n"
                           "Las traducciones van en la misma llamada: cargar "
                           "una ficha bilingüe en dos peticiones invita a "
                           "dejar la segunda sin hacer.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "requestBody": _body("AdminPlaceCrear"),
            "responses": {"201": _ok("Sitio creado", "PlaceResponse"),
                          "400": _err("Campo fuera de la lista blanca o valor inválido"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador"),
                          "409": _err("Ya existe un sitio con ese id")}}})

    spec.path(path="/api/admin/places/{place_id}", operations={
        "put": {
            "tags": ["admin"], "summary": "Editar un sitio",
            "description": "Edición parcial: solo lo que se manda. El `id` no "
                           "se puede cambiar — renombrar la clave rompería los "
                           "guardados y las paradas de tour que apuntan a "
                           "él.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "parameters": [{"name": "place_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "requestBody": _body("AdminPlaceActualizar"),
            "responses": {"200": _ok("Sitio actualizado", "PlaceResponse"),
                          "400": _err("Campo no editable o valor inválido"),
                          "401": _err("Sin token"),
                          "404": _err("No existe, o la cuenta no es de administrador")}}})

    # ---------------- tours ----------------
    spec.path(path="/api/admin/tours", operations={
        "get": {
            "tags": ["admin"], "summary": "Todos los tours con sus paradas",
            "security": AUTH,
            "responses": {"200": _ok("Tours", "UserTourListResponse"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador")}},
        "post": {
            "tags": ["admin"], "summary": "Crear un tour con su recorrido",
            "description": "Las paradas van en la misma llamada: un recorrido "
                           "sin ellas no es nada, y mandarlas aparte deja la "
                           "puerta a tours a medio montar.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "requestBody": _body("AdminTourCrear"),
            "responses": {"201": _ok("Tour creado", "TourResponse"),
                          "400": _err("Posiciones repetidas o campo inválido"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador"),
                          "409": _err("El id ya existe, o una parada apunta a "
                                      "un sitio que no existe")}}})

    spec.path(path="/api/admin/tours/{tour_id}", operations={
        "put": {
            "tags": ["admin"], "summary": "Editar un tour",
            "description": "Si se manda `stops`, **sustituye al recorrido "
                           "entero**. Una lista vacía deja el tour sin "
                           "paradas; no mencionarlas no las toca.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "parameters": [{"name": "tour_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "requestBody": _body("AdminTourActualizar"),
            "responses": {"200": _ok("Tour actualizado", "TourResponse"),
                          "400": _err("Valor inválido"),
                          "401": _err("Sin token"),
                          "404": _err("No existe, o la cuenta no es de administrador"),
                          "409": _err("Una parada apunta a un sitio inexistente")}}})

    # ---------------- guía histórica ----------------
    spec.path(path="/api/admin/content", operations={
        "get": {
            "tags": ["admin"], "summary": "Todos los artículos",
            "security": AUTH,
            "responses": {"200": _ok("Artículos", "ContentListResponse"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador")}},
        "post": {
            "tags": ["admin"], "summary": "Crear un artículo",
            "description": "El cuerpo tiene que corresponder al tipo: uno de "
                           "audio sin `audio_url` es una ficha que no se "
                           "puede abrir.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "requestBody": _body("AdminContenidoCrear"),
            "responses": {"201": _ok("Artículo creado", "HistoricalContentResponse"),
                          "400": _err("Falta el cuerpo del tipo, o campo inválido"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador"),
                          "409": _err("El id ya existe, o apunta a una "
                                      "cronología o un sitio inexistente")}}})

    spec.path(path="/api/admin/content/{content_id}", operations={
        "put": {
            "tags": ["admin"], "summary": "Editar un artículo",
            "description": "Edición parcial. La coherencia entre tipo y cuerpo "
                           "solo se comprueba si la actualización cambia el "
                           "tipo: si no, corregir una errata del título "
                           "obligaría a remandar el artículo entero.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "parameters": [{"name": "content_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "requestBody": _body("AdminContenidoActualizar"),
            "responses": {"200": _ok("Artículo actualizado",
                                     "HistoricalContentResponse"),
                          "400": _err("Valor inválido"),
                          "401": _err("Sin token"),
                          "404": _err("No existe, o la cuenta no es de administrador"),
                          "409": _err("Apunta a algo que no existe")}}})

    # ---------------- overlay del lago ----------------
    spec.path(path="/api/admin/lake-geometries", operations={
        "get": {
            "tags": ["admin"], "summary": "Polígonos del overlay",
            "security": AUTH,
            "parameters": [{"name": "year", "in": "query",
                            "schema": {"type": "integer"}}],
            "responses": {"200": _ok("Polígonos", "AdminLakeListResponse"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador")}},
        "post": {
            "tags": ["admin"], "summary": "Cargar un polígono",
            "description": "Va por API y no solo por el seed porque los "
                           "trazados de verdad los va a ir afinando alguien "
                           "con un mapa delante, y pedirle un despliegue por "
                           "cada corrección garantiza que no se corrijan.\n\n"
                           "El anillo tiene que cerrarse: el último punto "
                           "repite el primero.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "requestBody": _body("AdminLakeGeometria"),
            "responses": {"201": _ok("Polígono creado", "AdminLakeCreadaResponse"),
                          "400": _err("Geometría mal formada, o rechazada por PostGIS"),
                          "401": _err("Sin token"),
                          "404": _err("La cuenta no es de administrador")}}})

    spec.path(path="/api/admin/lake-geometries/{geometria_id}", operations={
        "delete": {
            "tags": ["admin"], "summary": "Borrar un polígono",
            "description": "El **único borrado real** de toda la API. Aquí sí "
                           "y en el resto no, porque un polígono mal trazado "
                           "no tiene nada colgando: nadie lo ha guardado en "
                           "favoritos ni forma parte del recorrido de un "
                           "tour. Un sitio o un artículo se retiran con "
                           "`is_published` o `status`, que conserva lo que "
                           "apunta a ellos.\n\n" + _NO_ADMIN,
            "security": AUTH,
            "parameters": [{"name": "geometria_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "responses": {"200": _ok("Borrado", "MessageResponse"),
                          "401": _err("Sin token"),
                          "404": _err("No existe, o la cuenta no es de administrador")}}})
