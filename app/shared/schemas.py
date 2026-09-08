"""Schemas marshmallow de entrada.

Cada schema es una whitelist: `unknown = RAISE` hace que un campo no declarado
devuelva 400 en vez de colarse hasta el modelo. Así se cierra el mass
assignment que permitía a un usuario mandar {"subscription_tier": "vip"} a
PUT /api/users/profile y ascenderse solo.

El nombre del campo es el nombre de la columna; `data_key` es el nombre que
viaja en JSON (camelCase), coherente con lo que devuelve to_dict().
"""
from marshmallow import Schema, fields, validate

from app.shared.constants import CURATIONS, PROVIDERS


class UserRegisterSchema(Schema):
    class Meta:
        unknown = "raise"

    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    first_name = fields.Str(data_key="firstName", load_default=None, allow_none=True,
                            validate=validate.Length(max=255))
    last_name = fields.Str(data_key="lastName", load_default=None, allow_none=True,
                           validate=validate.Length(max=255))


class UserLoginSchema(Schema):
    class Meta:
        unknown = "raise"

    email = fields.Email(required=True)
    password = fields.Str(required=True)


class UserProfileUpdateSchema(Schema):
    """Lo ÚNICO que un usuario puede cambiar de su propio perfil.

    Fuera quedan a propósito: subscription_tier, subscription_end_date,
    is_verified, is_active, total_tours_completed, email y password_hash.
    """

    class Meta:
        unknown = "raise"

    first_name = fields.Str(data_key="firstName", allow_none=True,
                            validate=validate.Length(max=255))
    last_name = fields.Str(data_key="lastName", allow_none=True,
                           validate=validate.Length(max=255))
    avatar_url = fields.Url(data_key="avatarUrl", allow_none=True,
                            validate=validate.Length(max=500))
    # El diseño guarda el idioma en la cuenta ("Save language"), no solo lo
    # deduce de la cabecera. Por eso sí es un campo editable del perfil.
    preferred_locale = fields.Str(
        data_key="preferredLocale", allow_none=True,
        validate=validate.OneOf(["en", "es"]),
    )


class LocationPermissionSchema(Schema):
    class Meta:
        unknown = "raise"

    response = fields.Str(required=True, validate=validate.OneOf(["granted", "denied"]))
    context = fields.Str(load_default=None, allow_none=True,
                         validate=validate.Length(max=255))


class TourProgressUpdateSchema(Schema):
    """Avance que el cliente sí puede reportar.

    Fuera quedan is_completed, completed_at y rating: el cierre de un tour pasa
    por POST /<tour_id>/complete, no por un PUT de progreso.
    """

    class Meta:
        unknown = "raise"

    current_stop_index = fields.Int(data_key="currentStopIndex",
                                     validate=validate.Range(min=0))
    last_location_lat = fields.Float(data_key="lastLocationLat",
                                     validate=validate.Range(min=-90, max=90))
    last_location_lon = fields.Float(data_key="lastLocationLon",
                                     validate=validate.Range(min=-180, max=180))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=2000))


class TourCompleteSchema(Schema):
    class Meta:
        unknown = "raise"

    rating = fields.Int(load_default=None, allow_none=True,
                        validate=validate.Range(min=1, max=5))
    notes = fields.Str(load_default=None, allow_none=True,
                       validate=validate.Length(max=2000))


class PurchaseConfirmSchema(Schema):
    """Recibo que manda el cliente tras pagar.

    Lo que llega aquí NO se cree: `providers.verificar()` lo comprueba contra
    el proveedor antes de conceder nada.
    """

    class Meta:
        unknown = "raise"

    provider = fields.Str(required=True, validate=validate.OneOf(list(PROVIDERS)))
    external_id = fields.Str(
        data_key="externalId", required=True, validate=validate.Length(min=1, max=255)
    )


class PlaceFilterSchema(Schema):
    """Filtros de la pestaña Explore: All / Near / Must See / Quick Stops."""

    class Meta:
        unknown = "exclude"

    curation = fields.Str(validate=validate.OneOf(list(CURATIONS)))


# Instancias reutilizables: los schemas no guardan estado entre cargas.
user_register_schema = UserRegisterSchema()
user_login_schema = UserLoginSchema()
user_profile_update_schema = UserProfileUpdateSchema()
location_permission_schema = LocationPermissionSchema()
tour_progress_update_schema = TourProgressUpdateSchema()
tour_complete_schema = TourCompleteSchema()
purchase_confirm_schema = PurchaseConfirmSchema()
place_filter_schema = PlaceFilterSchema()
