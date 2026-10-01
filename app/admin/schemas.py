"""Validación de lo que entra por la API de administración.

Todo con `unknown = RAISE`. La regla del proyecto es la misma de siempre y no
cambia por ser una ruta de administración: un campo que no está en la lista
devuelve 400 en vez de ignorarse. Ignorar en silencio es peor de lo que parece
—quien carga el catálogo cree que guardó algo que no se guardó— y además fue
justo el mecanismo de la escalada de privilegios que arreglamos en el sprint 1.

Lo que queda fuera a propósito, aunque sean columnas de la tabla:
  - `id` en las actualizaciones: renombrar la clave de un sitio rompe los
    guardados y las paradas de tour que apuntan a él.
  - `views_count`, `completion_count`: los mueve el servidor, no el editor.
  - `geom`: la deriva el listener de lat/lng. Escribirla a mano sería tener
    dos fuentes de verdad para lo mismo.
"""
from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.shared.constants import CURATIONS, SURFACES
from app.shared.i18n import SUPPORTED_LOCALES

# El idioma base vive en las columnas del modelo; los demás, en `translations`.
LOCALES_TRADUCIBLES = [l for l in SUPPORTED_LOCALES if l != "en"]


class _Base(Schema):
    class Meta:
        unknown = "raise"


class FotoSchema(_Base):
    """Una foto de la galería de un sitio."""

    url = fields.Url(required=True, validate=validate.Length(max=500))
    caption = fields.Str(validate=validate.Length(max=255), allow_none=True)
    position = fields.Int(required=True, validate=validate.Range(min=0))


class TraduccionPlaceSchema(_Base):
    """Los campos de un sitio que tiene sentido traducir."""
    name = fields.Str(validate=validate.Length(min=1, max=255))
    tagline = fields.Str(validate=validate.Length(max=255))
    description = fields.Str()
    historical_significance = fields.Str()
    why_visit = fields.Str()
    how_to_get_there = fields.Str()
    visit_duration_text = fields.Str(validate=validate.Length(max=255))
    entry_fee_text = fields.Str(validate=validate.Length(max=500))
    opening_hours = fields.Str(validate=validate.Length(max=255))
    safety_recommendations = fields.Str()
    era_description = fields.Str()


class PlaceCrearSchema(_Base):
    """Un sitio nuevo.

    El id lo pone quien escribe y no el servidor: son legibles
    (`templo-mayor`), salen en las URLs y hacen que el seed y las pruebas se
    puedan leer. A cambio hay que validar la forma, porque un id con espacios o
    acentos acaba en una URL mal formada.
    """
    id = fields.Str(required=True, validate=validate.Regexp(
        r"^[a-z0-9]+(-[a-z0-9]+)*$",
        error="El id va en minúsculas, con guiones y sin acentos: 'templo-mayor'",
    ))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True)
    latitude = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    place_type = fields.Str(required=True, validate=validate.Length(max=50))
    historical_significance = fields.Str(required=True)
    estimated_visit_duration = fields.Int(
        required=True, validate=validate.Range(min=1, max=24 * 60))

    tagline = fields.Str(validate=validate.Length(max=255))
    neighborhood = fields.Str(validate=validate.Length(max=120))
    curation = fields.Str(validate=validate.OneOf(list(CURATIONS)), allow_none=True)
    editorial_rating = fields.Float(validate=validate.Range(min=0, max=5), allow_none=True)
    why_visit = fields.Str()
    how_to_get_there = fields.Str()
    tenochtitlan_name = fields.Str(validate=validate.Length(max=255))
    era_description = fields.Str()
    archaeological = fields.Bool()
    visit_duration_text = fields.Str(validate=validate.Length(max=255))
    image_url = fields.Url(validate=validate.Length(max=500))

    # La galería del carrusel. Se manda entera y sustituye a la anterior, igual
    # que las paradas de un tour: quien edita una ficha la tiene delante
    # completa, y así no existen los estados intermedios con dos fotos en la
    # misma posición. Mandar `images: []` vacía la galería; no mandarla la deja
    # como estaba.
    images = fields.List(fields.Nested(FotoSchema))

    is_locked = fields.Bool()
    is_published = fields.Bool()
    opening_hours = fields.Str(validate=validate.Length(max=255))
    entry_fee_mxn = fields.Decimal(places=2, as_string=False,
                                   validate=validate.Range(min=0), allow_none=True)
    entry_fee_usd = fields.Decimal(places=2, as_string=False,
                                   validate=validate.Range(min=0), allow_none=True)
    entry_fee_text = fields.Str(validate=validate.Length(max=500))
    is_free_entry = fields.Bool()
    is_outdoor = fields.Bool()
    safety_recommendations = fields.Str()
    has_bathrooms = fields.Bool()
    has_cafes = fields.Bool()
    has_hotels = fields.Bool()

    # Traducciones en la misma llamada. Cargar una ficha bilingüe en dos
    # peticiones invita a que la segunda se quede sin hacer.
    translations = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(LOCALES_TRADUCIBLES)),
        values=fields.Nested(TraduccionPlaceSchema),
    )

    @validates_schema
    def _fotos_sin_repetir(self, data, **kwargs):
        """La base lo impediría con su UNIQUE, pero con un 500 en vez de un 400."""
        posiciones = [f["position"] for f in (data.get("images") or [])]
        repetida = next((x for x in posiciones if posiciones.count(x) > 1), None)
        if repetida is not None:
            raise ValidationError(
                f"La posición {repetida} está repetida entre las fotos.", "images")

    @validates_schema
    def _tarifa_coherente(self, data, **kwargs):
        """Gratis y con precio a la vez es un error de captura, no un caso raro."""
        if not data.get("is_free_entry"):
            return
        for campo in ("entry_fee_mxn", "entry_fee_usd"):
            if data.get(campo):
                raise ValidationError(
                    "Marcado como entrada gratuita pero con importe.", campo)


class PlaceActualizarSchema(PlaceCrearSchema):
    """Igual, pero todo opcional y sin poder cambiar el id.

    Se hereda en lugar de repetir la lista: si alguien añade un campo al crear
    y olvida el editar, el resultado es un campo que se puede poner una vez y
    no corregir nunca.
    """
    id = fields.Str(
        validate=validate.Regexp(r"^$", error="El id de un sitio no se cambia"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.required = False


class TourParadaSchema(_Base):
    place_id = fields.Str(required=True)
    position = fields.Int(required=True, validate=validate.Range(min=0))
    audio_url = fields.Url(validate=validate.Length(max=500), allow_none=True)
    audio_duration_seconds = fields.Int(
        validate=validate.Range(min=0), allow_none=True)
    transition_text = fields.Str(allow_none=True)

    # Minutos andando hasta la parada siguiente. La última los deja sin poner.
    walk_minutes_to_next = fields.Int(
        validate=validate.Range(min=0, max=24 * 60), allow_none=True)


class TraduccionTourSchema(_Base):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str()
    content_description = fields.Str()
    duration_text = fields.Str(validate=validate.Length(max=120))


class TourCrearSchema(_Base):
    id = fields.Str(required=True, validate=validate.Regexp(
        r"^[a-z0-9]+(-[a-z0-9]+)*$",
        error="El id va en minúsculas, con guiones y sin acentos",
    ))
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True)
    estimated_duration = fields.Int(
        required=True, validate=validate.Range(min=1, max=24 * 60))

    status = fields.Str(validate=validate.OneOf(["draft", "published", "archived"]))
    content_description = fields.Str()
    duration_text = fields.Str(validate=validate.Length(max=120))
    difficulty_level = fields.Str(validate=validate.OneOf(["easy", "medium", "hard"]))
    neighborhood = fields.Str(validate=validate.Length(max=120))
    image_url = fields.Url(validate=validate.Length(max=500))
    total_distance = fields.Float(validate=validate.Range(min=0), allow_none=True)
    has_entry_fees = fields.Bool()
    editorial_rating = fields.Float(validate=validate.Range(min=0, max=5), allow_none=True)
    is_free = fields.Bool()
    is_locked = fields.Bool()

    # Las paradas van con el tour: un recorrido sin ellas no es nada, y
    # mandarlas aparte deja la puerta a tours a medio montar.
    stops = fields.List(fields.Nested(TourParadaSchema))

    translations = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(LOCALES_TRADUCIBLES)),
        values=fields.Nested(TraduccionTourSchema),
    )

    @validates_schema
    def _paradas_sin_repetir(self, data, **kwargs):
        """La base lo impediría con su UNIQUE, pero con un 500 en vez de un 400.

        Vale más decir cuál es la parada repetida que devolver un error de
        integridad que el editor no sabe leer.
        """
        paradas = data.get("stops") or []

        posiciones = [p["position"] for p in paradas]
        repetida = next((x for x in posiciones if posiciones.count(x) > 1), None)
        if repetida is not None:
            raise ValidationError(
                f"La posición {repetida} está repetida entre las paradas.", "stops")

        sitios = [p["place_id"] for p in paradas]
        repetido = next((x for x in sitios if sitios.count(x) > 1), None)
        if repetido is not None:
            raise ValidationError(
                f"El sitio '{repetido}' aparece dos veces en el recorrido.", "stops")


class TourActualizarSchema(TourCrearSchema):
    id = fields.Str(
        validate=validate.Regexp(r"^$", error="El id de un tour no se cambia"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.required = False


class TraduccionContenidoSchema(_Base):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str()
    text_content = fields.Str()
    topic = fields.Str(validate=validate.Length(max=100))
    era = fields.Str(validate=validate.Length(max=100))
    date_description = fields.Str(validate=validate.Length(max=255))


class ContenidoCrearSchema(_Base):
    id = fields.Str(required=True, validate=validate.Regexp(
        r"^[a-z0-9]+(-[a-z0-9]+)*$",
        error="El id va en minúsculas, con guiones y sin acentos",
    ))
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True)
    content_type = fields.Str(required=True,
                              validate=validate.OneOf(["text", "audio", "video"]))

    text_content = fields.Str()
    audio_url = fields.Url(validate=validate.Length(max=500))
    video_url = fields.Url(validate=validate.Length(max=500))
    timeline_id = fields.Str(allow_none=True)
    sort_order = fields.Int(validate=validate.Range(min=0), allow_none=True)
    era = fields.Str(validate=validate.Length(max=100))
    date_description = fields.Str(validate=validate.Length(max=255))
    topic = fields.Str(validate=validate.Length(max=100))
    reading_time_minutes = fields.Int(
        validate=validate.Range(min=1, max=180), allow_none=True)
    place_id = fields.Str(allow_none=True)
    is_locked = fields.Bool()
    author = fields.Str(validate=validate.Length(max=255))
    sources = fields.Raw()
    verified = fields.Bool()

    translations = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(LOCALES_TRADUCIBLES)),
        values=fields.Nested(TraduccionContenidoSchema),
    )

    @validates_schema
    def _cuerpo_segun_tipo(self, data, **kwargs):
        """Un artículo de audio sin audio es una ficha que no se puede abrir."""
        requerido = {
            "text": "text_content",
            "audio": "audio_url",
            "video": "video_url",
        }.get(data.get("content_type"))

        if requerido and not data.get(requerido):
            raise ValidationError(
                f"Un contenido de tipo '{data['content_type']}' necesita "
                f"'{requerido}'.", requerido)


class ContenidoActualizarSchema(ContenidoCrearSchema):
    id = fields.Str(
        validate=validate.Regexp(r"^$", error="El id de un artículo no se cambia"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.required = False

    @validates_schema
    def _cuerpo_segun_tipo(self, data, **kwargs):
        """Solo se comprueba si la actualización cambia el tipo.

        En una edición parcial el tipo puede no venir, y exigir el cuerpo
        entonces impediría corregir una errata del título.
        """
        if "content_type" not in data:
            return
        super()._cuerpo_segun_tipo(data, **kwargs)


class LakeGeometriaSchema(_Base):
    """Un polígono del overlay histórico.

    Va por API y no solo por seed porque los trazados de verdad los va a ir
    afinando alguien con un mapa delante, y pedirle un despliegue por cada
    corrección es garantizar que no se corrijan.
    """
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    surface_type = fields.Str(required=True, validate=validate.OneOf(list(SURFACES)))
    geometry = fields.Dict(required=True)
    year_estimate = fields.Int(validate=validate.Range(min=-5000, max=3000))
    tenochtitlan_name = fields.Str(validate=validate.Length(max=255))
    description = fields.Str()

    @validates_schema
    def _geometria_valida(self, data, **kwargs):
        geom = data.get("geometry") or {}
        if geom.get("type") != "Polygon":
            raise ValidationError("La geometría tiene que ser un Polygon.", "geometry")
        anillos = geom.get("coordinates")
        if not isinstance(anillos, list) or not anillos:
            raise ValidationError("Faltan las coordenadas del polígono.", "geometry")
        for anillo in anillos:
            if not isinstance(anillo, list) or len(anillo) < 4:
                raise ValidationError(
                    "Cada anillo necesita al menos 4 puntos.", "geometry")
            if anillo[0] != anillo[-1]:
                raise ValidationError(
                    "El anillo tiene que cerrarse: el último punto debe "
                    "repetir el primero.", "geometry")


place_crear_schema = PlaceCrearSchema()
place_actualizar_schema = PlaceActualizarSchema()
tour_crear_schema = TourCrearSchema()
tour_actualizar_schema = TourActualizarSchema()
contenido_crear_schema = ContenidoCrearSchema()
contenido_actualizar_schema = ContenidoActualizarSchema()
lake_geometria_schema = LakeGeometriaSchema()
