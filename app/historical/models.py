"""Historical content models"""
from datetime import datetime

from geoalchemy2 import Geography

from app.extensions import db
from app.shared.constants import SURFACE_WATER
from app.shared.utils import utc_ahora


class Timeline(db.Model):
    """Una cronología: la pestaña "Chronology" de la guía histórica."""

    __tablename__ = 'timelines'

    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class HistoricalContent(db.Model):
    """Un artículo de la guía histórica."""

    __tablename__ = 'historical_content'

    id = db.Column(db.String(36), primary_key=True)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # text, audio, video

    text_content = db.Column(db.Text)
    audio_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))

    # Cronología. Antes el comentario del modelo decía que los artículos se
    # enlazarían "con una referencia a la timeline", pero esa columna no
    # existía y la pestaña Chronology no se podía construir.
    timeline_id = db.Column(db.String(36), db.ForeignKey('timelines.id'), index=True)
    # Orden dentro de la cronología. Es lo que hace posible el botón "Next".
    sort_order = db.Column(db.Integer, default=0)

    era = db.Column(db.String(255))          # "Aztec Empire (1345-1521)"
    date_description = db.Column(db.String(255))
    # Agrupación de la pestaña "Topics": religión, vida cotidiana, conquista...
    topic = db.Column(db.String(100), index=True)

    # El diseño muestra el tiempo de lectura en cada tarjeta (`ch-time`).
    reading_time_minutes = db.Column(db.Integer)

    place_id = db.Column(db.String(36), db.ForeignKey('places.id'))

    # Acceso: un único desbloqueo, sin niveles.
    is_locked = db.Column(db.Boolean, default=False)

    author = db.Column(db.String(255))
    sources = db.Column(db.Text)             # JSON array de fuentes
    verified = db.Column(db.Boolean, default=False)

    views_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    timeline = db.relationship('Timeline', backref='contents')

    def to_dict(self, unlocked=True, is_read=None):
        """Ficha del artículo.

        El cuerpo —texto, audio, vídeo, fuentes— lo añade el service y solo si
        `unlocked`. Las columnas de bloqueo existían desde el principio y no
        las miraba nadie: el contenido de pago se servía gratis.

        `is_read` solo tiene sentido con sesión; sin ella viaja como None.
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "contentType": self.content_type,
            "era": self.era,
            "topic": self.topic,
            "dateDescription": self.date_description,
            "readingTimeMinutes": self.reading_time_minutes,
            "timelineId": self.timeline_id,
            "sortOrder": self.sort_order,
            "placeId": self.place_id,
            "isLocked": bool(self.is_locked),
            "unlockedForViewer": unlocked,
            "isRead": is_read,
            "author": self.author,
            "verified": self.verified,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class LakeGeometry(db.Model):
    """Polígonos del lago de Tenochtitlan para el overlay del mapa.

    Sustituye al antiguo LakeView, que guardaba puntos sueltos con un booleano
    `was_water`: con puntos no se puede dibujar una orilla.

    `year_estimate` no es decorativo. El mapa del diseño lleva un conmutador
    «1500 / 2026», así que el overlay salta entre épocas y el año es el filtro
    que decide qué se pinta.
    """

    __tablename__ = 'lake_geometries'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    # geoalchemy2 crea el índice GiST solo con spatial_index=True.
    geom = db.Column(
        Geography(geometry_type='POLYGON', srid=4326, spatial_index=True),
        nullable=False,
    )

    year_estimate = db.Column(db.Integer, index=True)

    # Agua o tierra. En el diseño el mapa de 1500 tiene DOS colores: el lago en
    # azul y las islas en arena. Sin este campo la app tendría que adivinar por
    # el nombre del polígono, que aguanta hasta que alguien siembre el cuarto.
    surface_type = db.Column(db.String(10), nullable=False, default=SURFACE_WATER)

    tenochtitlan_name = db.Column(db.String(255))
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utc_ahora)

    # Sin to_dict: la geometría se serializa con ST_AsGeoJSON en el repositorio,
    # que es donde PostGIS puede hacerlo sin traerse el WKB a Python.
