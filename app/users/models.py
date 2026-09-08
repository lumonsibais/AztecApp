"""Users models"""
from datetime import datetime

from app.extensions import db
from app.shared.enums import LocationPermissionStatus
from app.shared.utils import utc_ahora


class User(db.Model):
    """User model"""

    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(500))

    # Idioma elegido en ajustes. Manda sobre la cabecera Accept-Language: el
    # diseño tiene una pantalla con "Save language", así que la preferencia se
    # guarda en la cuenta y viaja entre dispositivos.
    preferred_locale = db.Column(db.String(5))

    # Acceso al contenido de pago.
    # Es un PERMISO, no una suscripción: el producto vende un desbloqueo único
    # de 15 USD que no caduca. Lo escribe PurchaseService cuando una compra se
    # completa; el registro de la compra vive aparte, en `purchases`.
    has_full_access = db.Column(db.Boolean, default=False, nullable=False)
    full_access_since = db.Column(db.DateTime)

    # Location permissions
    location_permission_status = db.Column(
        db.String(50),
        default="not_asked"
    )  # not_asked, granted, denied, revoked
    location_permission_last_prompted = db.Column(db.DateTime)

    # Stats — los contadores que el perfil muestra como "Sites" y "Tours"
    total_tours_completed = db.Column(db.Integer, default=0)
    total_places_visited = db.Column(db.Integer, default=0)
    last_location_update = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)

    # Account
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    # Audit
    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "avatarUrl": self.avatar_url,
            "preferredLocale": self.preferred_locale,
            "hasFullAccess": bool(self.has_full_access),
            "fullAccessSince": (
                self.full_access_since.isoformat() if self.full_access_since else None
            ),
            "locationPermissionStatus": self.location_permission_status,
            "stats": {
                "toursCompleted": self.total_tours_completed or 0,
                "placesVisited": self.total_places_visited or 0,
            },
            "isVerified": self.is_verified,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class LocationPermissionLog(db.Model):
    """Track location permission requests and responses"""

    __tablename__ = 'location_permission_logs'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=utc_ahora)
    response = db.Column(db.String(50))  # granted, denied
    context = db.Column(db.String(255))  # where was it requested from


class TokenBlocklist(db.Model):
    """Tokens JWT revocados.

    Sin esto un logout no invalida nada: el token seguiría siendo válido hasta
    su expiración (30 días el access, 90 el refresh).
    Las filas caducadas se pueden purgar por `expires_at`.
    """

    __tablename__ = 'token_blocklist'

    id = db.Column(db.String(36), primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(16), nullable=False)  # access, refresh
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=utc_ahora)
    expires_at = db.Column(db.DateTime, nullable=False)


class SavedPlace(db.Model):
    """Sitio guardado por un usuario — el corazón de las tarjetas.

    Alimenta la pestaña Saved del menú inferior. La restricción única evita que
    un doble toque cree dos filas: guardar es idempotente.
    """

    __tablename__ = 'saved_places'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.String(36), db.ForeignKey('places.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_ahora)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'place_id', name='uq_saved_place'),
        # El listado siempre se pide por usuario y ordenado por fecha.
        db.Index('ix_saved_places_user', 'user_id', 'created_at'),
    )


class ContentRead(db.Model):
    """Artículo de la guía histórica marcado como leído.

    El diseño tiene un botón "Mark read" y la lista distingue lo leído de lo
    pendiente, así que el estado es por usuario y por artículo.
    """

    __tablename__ = 'content_reads'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(
        db.String(36), db.ForeignKey('historical_content.id'), nullable=False
    )
    read_at = db.Column(db.DateTime, default=utc_ahora)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_id', name='uq_content_read'),
        db.Index('ix_content_reads_user', 'user_id'),
    )
