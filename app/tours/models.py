"""Tours models"""
from datetime import datetime

from app.extensions import db
from app.shared.utils import utc_ahora


class TourStop(db.Model):
    """Una parada del recorrido.

    Sustituye a la tabla de asociación `tour_places`, que solo podía guardar la
    pareja tour-sitio y una columna `order` que nadie leía. El diseño necesita
    bastante más por parada: su audio, cuánto dura y el texto que lleva a la
    siguiente ("Next, let's go to the Aztec's sacred precinct"). Eso son datos
    de la RELACIÓN, no del sitio: el Templo Mayor no tiene un único audio, tiene
    uno distinto según el tour que lo recorra.
    """

    __tablename__ = 'tour_stops'

    id = db.Column(db.String(36), primary_key=True)
    tour_id = db.Column(db.String(36), db.ForeignKey('tours.id'), nullable=False)
    place_id = db.Column(db.String(36), db.ForeignKey('places.id'), nullable=False)

    # Orden dentro del recorrido. Sin esto las paradas salían en orden
    # arbitrario, que en un tour a pie es sencillamente estar perdido.
    position = db.Column(db.Integer, nullable=False, default=0)

    # La guía de audio es lo que se paga: las capas del diseño se llaman
    # `locked-audio-content`. Va por parada, no por tour.
    audio_url = db.Column(db.String(500))
    audio_duration_seconds = db.Column(db.Integer)

    # Texto de enlace entre esta parada y la siguiente.
    transition_text = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utc_ahora)

    place = db.relationship('Place', backref='stops')

    __table_args__ = (
        db.UniqueConstraint('tour_id', 'position', name='uq_tour_stop_position'),
        db.UniqueConstraint('tour_id', 'place_id', name='uq_tour_stop_place'),
    )

    def to_dict(self, unlocked=True, include_place=True):
        data = {
            "id": self.id,
            "position": self.position,
            "placeId": self.place_id,
            "transitionText": self.transition_text if unlocked else None,
            "audio": {
                "url": self.audio_url if unlocked else None,
                "durationSeconds": self.audio_duration_seconds,
                "isLocked": not unlocked and bool(self.audio_url),
            },
        }

        if include_place and self.place is not None:
            data["place"] = self.place.to_dict(unlocked=unlocked)

        return data


class Tour(db.Model):
    """Tour autoguiado."""

    __tablename__ = 'tours'

    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(50), nullable=False, default='draft')  # draft, published, archived

    # Acceso: un único desbloqueo, sin niveles.
    is_free = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)

    # Duración: el número ordena y filtra; el texto es lo que se muestra,
    # porque el diseño anuncia "1 - 2 hours" y eso no es un entero.
    estimated_duration = db.Column(db.Integer, nullable=False)  # minutos
    duration_text = db.Column(db.String(120))

    difficulty_level = db.Column(db.String(50))  # easy, medium, hard
    image_url = db.Column(db.String(500))

    total_distance = db.Column(db.Float)  # km
    # "💰 No entry fees" es una promesa del anuncio del tour, no una suma.
    has_entry_fees = db.Column(db.Boolean, default=False)

    content_description = db.Column(db.Text)

    views_count = db.Column(db.Integer, default=0)
    completion_count = db.Column(db.Integer, default=0)
    editorial_rating = db.Column(db.Float)

    stops = db.relationship(
        'TourStop',
        backref='tour',
        order_by='TourStop.position',
        cascade='all, delete-orphan',
    )

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    @property
    def places(self):
        """Los sitios del tour, en el orden del recorrido."""
        return [s.place for s in self.stops if s.place is not None]

    @property
    def includes_audio(self) -> bool:
        """Si alguna parada trae audio. Antes era una columna que había que
        acordarse de mantener a mano."""
        return any(s.audio_url for s in self.stops)

    def to_dict(self, include_stops=False, unlocked=True):
        """Serializa el tour.

        `unlocked=False` es el teaser: título, descripción corta, duración y
        precio siguen viajando —es lo que la app enseña junto al candado— pero
        el guion, el audio y la ruta no.
        """
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'isFree': self.is_free,
            'isLocked': bool(self.is_locked),
            'unlockedForViewer': unlocked,
            'estimatedDuration': self.estimated_duration,
            'durationText': self.duration_text,
            'difficultyLevel': self.difficulty_level,
            'imageUrl': self.image_url,
            'totalDistance': self.total_distance,
            'hasEntryFees': bool(self.has_entry_fees),
            'stopsCount': len(self.stops),
            'includesAudio': self.includes_audio,
            'rating': self.editorial_rating,
            'statistics': {
                'views': self.views_count,
                'completions': self.completion_count,
            },
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }

        if unlocked:
            data['contentDescription'] = self.content_description

        if include_stops and unlocked:
            data['stops'] = [s.to_dict(unlocked=unlocked) for s in self.stops]

        return data


class TourProgress(db.Model):
    """Avance de un usuario dentro de un tour."""

    __tablename__ = 'tour_progress'

    id = db.Column(db.String(36), primary_key=True)
    tour_id = db.Column(db.String(36), db.ForeignKey('tours.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    started_at = db.Column(db.DateTime, default=utc_ahora)
    completed_at = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)

    current_stop_index = db.Column(db.Integer, default=0)
    last_location_lat = db.Column(db.Float)
    last_location_lon = db.Column(db.Float)

    rating = db.Column(db.Integer)  # 1-5
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    __table_args__ = (
        db.UniqueConstraint('tour_id', 'user_id', name='uq_tour_progress'),
    )

    def to_dict(self):
        """El avance completo, tal como quedó guardado.

        Los endpoints de progreso devolvían solo `{progressId}`, lo que obligaba
        al cliente a fiarse de lo que acababa de mandar en vez de leer lo que el
        servidor guardó. Con la app abierta en dos sitios —o con dos PUT que se
        cruzan— eso es divergir en silencio, y el usuario acaba viendo una
        parada que no es la suya.
        """
        return {
            'id': self.id,
            'tourId': self.tour_id,
            'currentStopIndex': self.current_stop_index,
            'isCompleted': bool(self.is_completed),
            'rating': self.rating,
            'notes': self.notes,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'completedAt': (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            'lastLocation': {
                'latitude': self.last_location_lat,
                'longitude': self.last_location_lon,
            },
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
