"""Payments models.

El producto vende un desbloqueo único. No hay suscripción, así que aquí no hay
periodos ni renovaciones: solo el registro de que alguien pagó.

Separación deliberada:
  - `purchases` guarda el HECHO del cobro, con su proveedor y su referencia.
  - `users.has_full_access` guarda el PERMISO.
El resto del backend consulta el permiso. Por eso pasar a cobrar desde las
tiendas solo cambió cómo se llena esta tabla, y ni una línea del resto.

El importe que se guarda aquí es el de referencia (FULL_ACCESS_PRICE_USD), no
lo que pagó el comprador: quien cobra es la tienda, en la moneda de su país y
al escalón de precio que se haya elegido en App Store Connect y en Play Console.
Lo que de verdad ingresó está en los informes de cada tienda, descontada su
comisión, y no hay forma de saberlo desde aquí.
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

    # De dónde vino el dinero: apple, google o manual.
    provider = db.Column(db.String(20), nullable=False)
    # Referencia del proveedor: transactionId de Apple, purchaseToken de Google.
    # Es lo que hace la operación idempotente.
    #
    # Text y no String(255): un purchaseToken de Google pasa holgadamente de los
    # 255 caracteres —suelen rondar los 350— y con el tipo anterior PostgreSQL
    # habría rechazado la fila con "value too long for type character varying".
    # Habría reventado la primera compra real de Android y ni un minuto antes.
    external_id = db.Column(db.Text)

    # Referencia de cabecera de la tienda: originalTransactionId en Apple,
    # orderId en Google. Es la que traen las notificaciones de reembolso, que no
    # siempre es la de la transacción concreta.
    original_transaction_id = db.Column(db.String(255), index=True)

    # Sandbox o Production. Un recibo de sandbox no desbloquea una instalación
    # de producción, y cuando alguien reporte un acceso raro esto es lo primero
    # que se mira.
    store_environment = db.Column(db.String(20))

    # Google reembolsa automáticamente toda compra que no se acuse en 3 días.
    # Esta marca es lo que permite encontrar las que se quedaron sin acusar
    # porque la llamada falló, antes de que se cumpla el plazo.
    acknowledged_at = db.Column(db.DateTime)

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
