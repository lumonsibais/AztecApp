"""Payments service.

Dos operaciones y un invariante:

  iniciar()    deja una compra pendiente y devuelve lo que el cliente necesita
  confirmar()  verifica el cobro, marca la compra y CONCEDE el permiso

El invariante es que `users.has_full_access` solo lo toca este servicio, y
solo después de que `providers.verificar()` haya dado el visto bueno.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.extensions import db
from app.payments.models import Purchase
from app.payments.providers import PaymentVerificationError, verificar
from app.payments.repositories import PurchaseRepository
from app.shared.constants import (
    CURRENCY_USD,
    FULL_ACCESS_PRICE_USD,
    FULL_ACCESS_PRODUCT,
    PURCHASE_COMPLETED,
    PURCHASE_FAILED,
    PURCHASE_PENDING,
    PURCHASE_REFUNDED,
)
from app.users.repositories import UserRepository
from app.shared.utils import utc_ahora


class AlreadyPurchased(Exception):
    """La cuenta ya tiene el desbloqueo. Cobrar otra vez sería un error."""


class PurchaseService:
    """Compra del desbloqueo completo."""

    @staticmethod
    def iniciar(user_id: str) -> Purchase:
        """Crea una compra pendiente.

        Devuelve la fila para que el cliente arranque el pago con el proveedor
        que toque. Si la cuenta ya tiene acceso, se niega: el desbloqueo es
        único y no caduca, así que una segunda compra es siempre un error.
        """
        usuario = UserRepository.find_by_id(user_id)
        if usuario is None:
            return None
        if usuario.has_full_access:
            raise AlreadyPurchased(user_id)

        # Si ya había un intento abierto, se reutiliza. Abrir uno nuevo cada
        # vez que se toca el botón llenaría `purchases` de filas pendientes
        # que no son compras, solo dudas.
        abierta = PurchaseRepository.find_pending_for_user(user_id)
        if abierta is not None:
            return abierta

        return PurchaseRepository.save(
            Purchase(
                id=str(uuid.uuid4()),
                user_id=user_id,
                product=FULL_ACCESS_PRODUCT,
                provider="",              # se sabrá al confirmar
                amount=FULL_ACCESS_PRICE_USD,
                currency=CURRENCY_USD,
                status=PURCHASE_PENDING,
            )
        )

    @staticmethod
    def confirmar(
        user_id: str, provider: str, payload: Dict[str, Any]
    ) -> Tuple[Purchase, bool]:
        """Verifica el cobro y concede el acceso.

        Devuelve (compra, recien_concedido). Es idempotente: si el mismo recibo
        llega dos veces, la segunda devuelve la compra existente sin volver a
        cobrar ni duplicar nada.

        Lanza PaymentVerificationError si el proveedor no valida el cobro; en
        ese caso NO se concede nada.
        """
        referencia = verificar(provider, payload)

        existente = PurchaseRepository.find_by_reference(provider, referencia)
        if existente is not None:
            return existente, False

        ahora = utc_ahora()

        # La compra que abrió /checkout es ESTA misma, ya cobrada: se completa
        # en vez de insertar otra fila. Si no, el historial de un usuario que
        # pagó una vez enseñaría dos apuntes —uno "pending" eterno y uno
        # "completed"— y la app tendría que filtrarlos.
        abierta = PurchaseRepository.find_pending_for_user(user_id)
        if abierta is not None:
            compra = PurchaseRepository.update(abierta.id, {
                "provider": provider,
                "external_id": referencia,
                "status": PURCHASE_COMPLETED,
                "purchased_at": ahora,
            })
        else:
            compra = PurchaseRepository.save(
                Purchase(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    product=FULL_ACCESS_PRODUCT,
                    provider=provider,
                    external_id=referencia,
                    amount=FULL_ACCESS_PRICE_USD,
                    currency=CURRENCY_USD,
                    status=PURCHASE_COMPLETED,
                    purchased_at=ahora,
                )
            )

        UserRepository.update(
            user_id, {"has_full_access": True, "full_access_since": ahora}
        )

        return compra, True

    @staticmethod
    def fallar(purchase_id: str) -> Optional[Purchase]:
        return PurchaseRepository.update(purchase_id, {"status": PURCHASE_FAILED})

    @staticmethod
    def reembolsar(purchase_id: str, motivo: str = None) -> Optional[Purchase]:
        """Devuelve el dinero y RETIRA el acceso.

        Retirarlo es la mitad que se olvida: si solo se marca la compra, la
        cuenta se queda con el contenido desbloqueado gratis.
        """
        compra = PurchaseRepository.find_by_id(purchase_id)
        if not compra:
            return None

        compra = PurchaseRepository.update(
            purchase_id,
            {
                "status": PURCHASE_REFUNDED,
                "refunded_at": utc_ahora(),
                "refund_reason": motivo,
            },
        )

        otra = PurchaseRepository.find_completed_for_user(compra.user_id)
        if otra is None:
            UserRepository.update(
                compra.user_id,
                {"has_full_access": False, "full_access_since": None},
            )

        return compra

    @staticmethod
    def historial(user_id: str) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in PurchaseRepository.find_by_user(user_id)]

    @staticmethod
    def estado_de_acceso(user_id: str) -> Dict[str, Any]:
        """Lo que la app pregunta al abrir para saber si pintar candados."""
        usuario = UserRepository.find_by_id(user_id)
        if usuario is None:
            return None

        return {
            "hasFullAccess": bool(usuario.has_full_access),
            "since": (
                usuario.full_access_since.isoformat()
                if usuario.full_access_since else None
            ),
            "product": FULL_ACCESS_PRODUCT,
            "price": FULL_ACCESS_PRICE_USD,
            "currency": CURRENCY_USD,
        }
