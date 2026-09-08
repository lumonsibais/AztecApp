"""Payments repository"""
from typing import List, Optional

from app.extensions import db
from app.payments.models import Purchase
from app.shared.constants import PURCHASE_COMPLETED, PURCHASE_PENDING


class PurchaseRepository:
    """Acceso a la tabla de compras."""

    @staticmethod
    def find_by_id(purchase_id: str) -> Optional[Purchase]:
        return Purchase.query.filter_by(id=purchase_id).first()

    @staticmethod
    def find_by_reference(provider: str, external_id: str) -> Optional[Purchase]:
        """Busca por la referencia del proveedor.

        Es la consulta que hace idempotente el cobro: si un recibo llega dos
        veces —reintento del cliente, webhook duplicado— la segunda encuentra
        la compra ya registrada en vez de crear otra.
        """
        if not external_id:
            return None
        return Purchase.query.filter_by(
            provider=provider, external_id=external_id
        ).first()

    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Purchase]:
        return (
            Purchase.query.filter_by(user_id=user_id)
            .order_by(Purchase.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def find_completed_for_user(user_id: str) -> Optional[Purchase]:
        return Purchase.query.filter_by(
            user_id=user_id, status=PURCHASE_COMPLETED
        ).first()

    @staticmethod
    def find_pending_for_user(user_id: str) -> Optional[Purchase]:
        """La compra que quedó abierta y todavía no se ha cobrado.

        Sirve para no acumular filas muertas: si alguien pulsa "comprar", se
        arrepiente y vuelve a pulsar, es el mismo intento, no dos.
        """
        return (
            Purchase.query.filter_by(user_id=user_id, status=PURCHASE_PENDING)
            .order_by(Purchase.created_at.desc())
            .first()
        )

    @staticmethod
    def save(purchase: Purchase) -> Purchase:
        db.session.add(purchase)
        db.session.commit()
        return purchase

    @staticmethod
    def update(purchase_id: str, data: dict) -> Optional[Purchase]:
        purchase = PurchaseRepository.find_by_id(purchase_id)
        if not purchase:
            return None

        for key, value in data.items():
            if hasattr(purchase, key):
                setattr(purchase, key, value)

        db.session.commit()
        return purchase
