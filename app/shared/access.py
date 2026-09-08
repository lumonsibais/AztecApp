"""Control de acceso al contenido de pago.

Punto ÚNICO de decisión. Antes esto comparaba niveles de suscripción; ahora el
producto vende un solo desbloqueo, así que la pregunta es binaria: ¿esta cuenta
lo compró o no?

Deliberadamente NO mira compras. Mira el permiso que quedó en la cuenta cuando
una compra se completó. Así el resto del backend no sabe —ni le importa— si el
dinero entró por Stripe, por Apple o por Google, y esa decisión se puede tomar
más adelante sin tocar nada de esto.
"""
from typing import Any


def can_access(has_full_access: bool, is_locked: bool) -> bool:
    """¿Puede esta cuenta abrir este contenido?

    Lo que no está bloqueado lo ve todo el mundo, incluidos los anónimos: el
    contenido base gratuito es el gancho del freemium.
    """
    if not is_locked:
        return True
    return bool(has_full_access)


def can_access_resource(has_full_access: bool, resource: Any) -> bool:
    """Igual que can_access, leyendo el flag del propio modelo."""
    return can_access(has_full_access, bool(getattr(resource, "is_locked", False)))
