"""Place models"""
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import event

from app.extensions import db
from app.shared.enums import PlaceType
from app.shared.utils import utc_ahora


class Place(db.Model):
    """Un sitio del catálogo."""

    __tablename__ = 'places'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)

    # Gancho de una línea que va en la tarjeta ("Witness the sacred beating
    # heart of the Aztec Empire."). Es distinto de `description`, que es el
    # cuerpo largo de la ficha: la tarjeta no puede mostrar un párrafo.
    tagline = db.Column(db.String(255))
    description = db.Column(db.Text, nullable=False)

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    # Espejo geográfico de latitude/longitude. Las dos columnas Float siguen
    # siendo la interfaz pública; geom es lo que consultan ST_DWithin y el
    # índice GiST. La mantiene sola el listener del final del archivo.
    geom = db.Column(
        Geography(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=True,
    )
    # Zona o colonia: el diseño la enseña como etiqueta ("Centro Histórico").
    neighborhood = db.Column(db.String(120))

    place_type = db.Column(db.String(50), nullable=False)

    # Curación editorial. Los filtros de Explore son All / Near / Must See /
    # Quick Stops: los dos últimos no son tipos de sitio, son listas que
    # mantiene el equipo a mano. Por eso viven aquí y no en place_type.
    curation = db.Column(db.String(20), index=True)   # must_see | quick_stop
    editorial_rating = db.Column(db.Float)            # las estrellas de la tarjeta

    historical_significance = db.Column(db.Text, nullable=False)
    # Secciones fijas de la ficha en el diseño. No son la descripción: tienen
    # su propio encabezado y su propio texto.
    why_visit = db.Column(db.Text)                    # "Why you should go?"
    how_to_get_there = db.Column(db.Text)             # "How to get there"

    tenochtitlan_name = db.Column(db.String(255))
    era_description = db.Column(db.Text)
    archaeological = db.Column(db.Boolean, default=False)

    # Duración: el número sirve para ordenar y filtrar; el texto es lo que se
    # muestra, porque el diseño escribe "30 min si solo lo ves desde fuera,
    # 1-3 horas si entras al museo" y eso no cabe en un entero.
    estimated_visit_duration = db.Column(db.Integer, nullable=False)  # minutos
    visit_duration_text = db.Column(db.String(255))

    image_url = db.Column(db.String(500))

    # Acceso: un único desbloqueo, sin niveles.
    is_locked = db.Column(db.Boolean, default=False)

    # Información práctica
    opening_hours = db.Column(db.String(255))
    # Las entradas se cobran en pesos y hay que poder mostrarlas también en
    # dólares. El texto acompaña porque muchas tarifas son condicionales.
    entry_fee_mxn = db.Column(db.Numeric(10, 2))
    entry_fee_usd = db.Column(db.Numeric(10, 2))
    entry_fee_text = db.Column(db.String(500))
    is_free_entry = db.Column(db.Boolean, default=False)   # distintivo "Free Entry"
    is_outdoor = db.Column(db.Boolean, default=False)      # distintivo "Outdoor View"
    safety_recommendations = db.Column(db.Text)

    # Servicios cercanos
    has_bathrooms = db.Column(db.Boolean, default=False)
    has_cafes = db.Column(db.Boolean, default=False)
    has_hotels = db.Column(db.Boolean, default=False)

    # Frescura del contenido. El documento de producto señala la información
    # desactualizada —horarios, cierres, costos— como la frustración principal
    # del usuario objetivo, así que conviene saber cuándo se revisó cada ficha.
    content_verified_at = db.Column(db.DateTime)

    # Audit
    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    # La relación M2M con Tour se declara UNA sola vez, en TourStop
    # (app/tours/models.py). Desde aquí se llega con el backref `Place.stops`.

    def to_dict(
        self,
        include_full_details=False,
        unlocked=True,
        distance_km=None,
        is_saved=None,
    ):
        """Serializa el sitio.

        `unlocked=False` devuelve el TEASER: el sitio sigue en el listado con
        nombre, ubicación, imagen y distintivos, pero sin el cuerpo de pago.
        La app necesita pintar el candado, que es donde ocurre la conversión.

        `distance_km` lo calcula PostGIS cuando la petición trae coordenadas.
        `is_saved` solo tiene sentido con sesión; sin ella viaja como None.
        """
        data = {
            'id': self.id,
            'name': self.name,
            'tagline': self.tagline,
            'description': self.description if unlocked else None,
            'location': {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'neighborhood': self.neighborhood,
                'distanceKm': (
                    round(distance_km, 2) if distance_km is not None else None
                ),
            },
            'placeType': self.place_type,
            'curation': self.curation,
            'rating': self.editorial_rating,
            'historicalSignificance': (
                self.historical_significance if unlocked else None
            ),
            'estimatedVisitDuration': self.estimated_visit_duration,
            'visitDurationText': self.visit_duration_text,
            'imageUrl': self.image_url,
            'badges': {
                'freeEntry': bool(self.is_free_entry),
                'outdoor': bool(self.is_outdoor),
                'archaeological': bool(self.archaeological),
            },
            'contentAccess': {
                'isLocked': bool(self.is_locked),
                'unlockedForViewer': unlocked,
            },
            'nearbyServices': {
                'bathrooms': self.has_bathrooms,
                'cafes': self.has_cafes,
                'hotels': self.has_hotels,
            },
            'isSaved': is_saved,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_full_details:
            # LOGÍSTICA — abierta, se pague o no.
            #
            # Cuánto cuesta la entrada, a qué hora abre y cómo se llega son
            # datos del mundo real que cualquiera resuelve en Google en veinte
            # segundos. Cobrarlos no produce ingresos: produce una salida de la
            # app, que es exactamente lo contrario de lo que queremos.
            #
            # Las recomendaciones de seguridad van en este bloque por otra
            # razón: cobrar por avisar de un riesgo no se hace.
            data.update({
                'howToGetThere': self.how_to_get_there,
                'openingHours': self.opening_hours,
                'entryFee': {
                    'mxn': float(self.entry_fee_mxn) if self.entry_fee_mxn is not None else None,
                    'usd': float(self.entry_fee_usd) if self.entry_fee_usd is not None else None,
                    'text': self.entry_fee_text,
                    'isFree': bool(self.is_free_entry),
                },
                'safetyRecommendations': self.safety_recommendations,
            })

        if include_full_details and unlocked:
            # CONTENIDO — lo que escribimos nosotros. Esto sí es el producto.
            data.update({
                'whyVisit': self.why_visit,
                'historicalContext': {
                    'tenochtitlanName': self.tenochtitlan_name,
                    'eraDescription': self.era_description,
                },
                'contentVerifiedAt': (
                    self.content_verified_at.isoformat()
                    if self.content_verified_at else None
                ),
            })

        return data


def _sincronizar_geom(mapper, connection, target):
    """Mantiene geom alineada con latitude/longitude.

    Va como listener y no como propiedad calculada para que todo el código que
    ya existe —seed.py, PlaceService.create_place, los tests— siga escribiendo
    solo lat/lng y obtenga la geometría gratis.

    Ojo con el orden: PostGIS escribe POINT(longitud latitud), al revés de como
    se nombra un par de coordenadas en el habla.
    """
    if target.latitude is not None and target.longitude is not None:
        target.geom = f"SRID=4326;POINT({target.longitude} {target.latitude})"
    else:
        target.geom = None


event.listen(Place, "before_insert", _sincronizar_geom)
event.listen(Place, "before_update", _sincronizar_geom)
