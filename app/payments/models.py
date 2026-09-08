"""Payments models.

El producto vende un desbloqueo único de 15 USD. No hay suscripción, así que
aquí no hay periodos ni renovaciones: solo el registro de que alguien pagó.

Separación deliberada:
  - `purchases` guarda el HECHO del cobro, con su proveedor y su referencia.
  - `users.has_full_access` guarda el PERMISO.
El resto del backend consulta el permiso. Así, cuando se decida si se cobra por
las tiendas o por pasarela propia, solo cambia cómo se llena esta tabla.
"""
from datetime import datetime

from app.extensions import db
from app.shared.utils import utc_ahora
from app.shared.constants import (
    CURRENCY_USD,
    FULL_ACCESS_PRODUCT,
    PURCHASE_PENDING,
)


class Purchase(db.Model):
    """Una compra del desbloqueo."""

    __tablename__ = 'purchases'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(
        db.String(36), db.ForeignKey('users.id'), nullable=False, index=True
    )

    product = db.Column(db.String(50), nullable=False, default=FULL_ACCESS_PRODUCT)

    # De dónde vino el dinero: stripe, apple, google o manual.
    provider = db.Column(db.String(20), nullable=False)
    # Referencia del proveedor: payment intent, transactionId de Apple,
    # purchaseToken de Google. Es lo que hace la operación idempotente.
    external_id = db.Column(db.String(255))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default=CURRENCY_USD)

    status = db.Column(db.String(20), nullable=False, default=PURCHASE_PENDING)

    purchased_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    refund_reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    __table_args__ = (
        # Un mismo recibo no puede aplicarse dos veces. En PostgreSQL los NULL
        # no chocan entre sí, así que las compras aún sin referencia (pendientes)
        # conviven sin problema.
        db.UniqueConstraint('provider', 'external_id', name='uq_purchase_provider_ref'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "product": self.product,
            "provider": self.provider,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "status": self.status,
            "purchasedAt": (
                self.purchased_at.isoformat() if self.purchased_at else None
            ),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
