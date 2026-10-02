"""Payments service.

Tres operaciones y un invariante:

  iniciar()      deja una compra pendiente y devuelve lo que el cliente necesita
  confirmar()    verifica el cobro contra la tienda y CONCEDE el permiso
  restaurar()    vuelve a conceder el permiso a partir de una compra ya hecha

El invariante es que `users.has_full_access` solo lo toca este servicio, y solo
después de que `providers.verificar()` haya dado el visto bueno.

El cobro lo hace la tienda, no nosotros. Lo que llega por la API es siempre un
recibo que hay que ir a comprobar: nada de lo que mande el cliente concede nada
por sí mismo.
"""
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.payments.models import Purchase
from app.payments.providers import (
    ESTADO_ACTIVA,
    ESTADO_REVOCADA,
    PaymentVerificationError,
    ResultadoVerificacion,
    acusar_recibo,
    estado as estado_en_tienda,
    verificar,
)
from app.payments.repositories import PurchaseRepository
from app.shared.constants import (
    CURRENCY_USD,
    FULL_ACCESS_PRICE_USD,
    FULL_ACCESS_PRODUCT,
    PROVIDER_GOOGLE,
    PURCHASE_COMPLETED,
    PURCHASE_FAILED,
    PURCHASE_PENDING,
    PURCHASE_REFUNDED,
)
from app.users.repositories import UserRepository
from app.shared.utils import utc_ahora


class AlreadyPurchased(Exception):
    """La cuenta ya tiene el desbloqueo. Cobrar otra vez sería un error."""


class ReciboDeOtraCuenta(Exception):
    """El recibo ya está aplicado a otra cuenta.

    Sin esto, un recibo válido circulando por un foro desbloquearía tantas
    cuentas como quisiera quien lo pegara. Una compra, una cuenta.
    """


class NoHayCompra(Exception):
    """No consta ninguna compra que restaurar para esta cuenta."""


class PurchaseService:
    """Compra del desbloqueo completo."""

    @staticmethod
    def iniciar(user_id: str) -> Purchase:
        """Crea una compra pendiente.

        Devuelve la fila para que el cliente arranque el pago con la tienda que
        toque. Si la cuenta ya tiene acceso, se niega: el desbloqueo es único y
        no caduca, así que una segunda compra es siempre un error.
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

    # ------------------------------------------------------------------
    # Confirmación y restauración
    # ------------------------------------------------------------------

    @staticmethod
    def _comprobar_titular(resultado: ResultadoVerificacion, user_id: str) -> None:
        """Si la tienda dice de quién es la compra, tiene que ser de quien la presenta.

        La app manda el id de usuario al iniciar la compra (`appAccountToken` en
        StoreKit, `obfuscatedExternalAccountId` en Play Billing) y la tienda lo
        devuelve intacto. Cuando viene, es la comprobación más fuerte que hay
        contra el reenvío de recibos ajenos, porque la fija la tienda y no se
        puede falsificar desde el cliente.

        Cuando no viene no se comprueba nada aquí: queda la unicidad de
        (provider, external_id) en base de datos, que impide que un mismo recibo
        se aplique dos veces aunque no impide el primer reenvío.
        """
        if resultado.cuenta_externa and resultado.cuenta_externa != user_id:
            raise ReciboDeOtraCuenta(
                "La tienda dice que esta compra pertenece a otra cuenta"
            )

    @staticmethod
    def _conceder(user_id: str, resultado: ResultadoVerificacion) -> Tuple[Purchase, bool]:
        """Registra la compra verificada y concede el acceso.

        Devuelve (compra, recien_concedido).
        """
        ahora = utc_ahora()
        datos_tienda = {
            "provider": resultado.provider,
            "external_id": resultado.referencia,
            "original_transaction_id": resultado.referencia_original or None,
            "store_environment": resultado.entorno or None,
        }

        existente = PurchaseRepository.find_by_reference(
            resultado.provider, resultado.referencia
        )

        if existente is not None:
            if existente.user_id != user_id:
                raise ReciboDeOtraCuenta(
                    "Este recibo ya está aplicado a otra cuenta"
                )

            if existente.status != PURCHASE_COMPLETED:
                # Nuestra fila decía reembolsada o fallida y la tienda acaba de
                # decir que la compra está viva —Apple revierte reembolsos—.
                # Manda la tienda.
                existente = PurchaseRepository.update(existente.id, {
                    **datos_tienda,
                    "status": PURCHASE_COMPLETED,
                    "purchased_at": existente.purchased_at or ahora,
                    "refunded_at": None,
                    "refund_reason": None,
                })

            recien = PurchaseService._asegurar_acceso(user_id, ahora)
            PurchaseService._acusar(existente, resultado)
            return existente, recien

        # La compra que abrió /checkout es ESTA misma, ya cobrada: se completa
        # en vez de insertar otra fila. Si no, el historial de un usuario que
        # pagó una vez enseñaría dos apuntes —uno "pending" eterno y uno
        # "completed"— y la app tendría que filtrarlos.
        abierta = PurchaseRepository.find_pending_for_user(user_id)
        if abierta is not None:
            compra = PurchaseRepository.update(abierta.id, {
                **datos_tienda,
                "status": PURCHASE_COMPLETED,
                "purchased_at": ahora,
            })
        else:
            compra = PurchaseRepository.save(
                Purchase(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    product=FULL_ACCESS_PRODUCT,
                    amount=FULL_ACCESS_PRICE_USD,
                    currency=CURRENCY_USD,
                    status=PURCHASE_COMPLETED,
                    purchased_at=ahora,
                    **datos_tienda,
                )
            )

        PurchaseService._asegurar_acceso(user_id, ahora)
        PurchaseService._acusar(compra, resultado)
        return compra, True

    @staticmethod
    def _asegurar_acceso(user_id: str, ahora) -> bool:
        """Concede el acceso si no lo tenía. Devuelve si acaba de concederse."""
        usuario = UserRepository.find_by_id(user_id)
        if usuario is not None and usuario.has_full_access:
            return False

        UserRepository.update(
            user_id, {"has_full_access": True, "full_access_since": ahora}
        )
        return True

    @staticmethod
    def _acusar(compra: Purchase, resultado: ResultadoVerificacion) -> None:
        """Acusa recibo a la tienda si hace falta.

        Va DESPUÉS de conceder el acceso y a propósito: si el acuse falla, el
        usuario que acaba de pagar ya tiene lo que compró. Lo que no se hace es
        marcar la fila como acusada, para que `acusar_pendientes` la reintente
        antes de que a Google se le cumpla el plazo de 3 días y la reembolse.
        """
        if compra is None or compra.provider != PROVIDER_GOOGLE:
            return
        if compra.acknowledged_at is not None:
            return

        if not resultado.requiere_acuse:
            # La propia consulta dijo que ya estaba acusada —una reinstalación
            # que vuelve a presentar el mismo recibo, por ejemplo—. Se anota sin
            # gastar otra llamada.
            PurchaseRepository.update(compra.id, {"acknowledged_at": utc_ahora()})
            return

        if acusar_recibo(compra.provider, compra.external_id):
            PurchaseRepository.update(compra.id, {"acknowledged_at": utc_ahora()})

    @staticmethod
    def confirmar(
        user_id: str, provider: str, payload: Dict[str, Any]
    ) -> Tuple[Purchase, bool]:
        """Verifica el cobro contra la tienda y concede el acceso.

        Devuelve (compra, recien_concedido). Es idempotente: si el mismo recibo
        llega dos veces, la segunda no duplica nada.

        Lanza PaymentVerificationError si la tienda no valida el cobro y
        ReciboDeOtraCuenta si el recibo ya está aplicado a otra cuenta; en
        ninguno de los dos casos se concede nada.
        """
        resultado = verificar(provider, payload)
        PurchaseService._comprobar_titular(resultado, user_id)
        return PurchaseService._conceder(user_id, resultado)

    @staticmethod
    def restaurar(
        user_id: str, provider: str, payload: Dict[str, Any]
    ) -> Tuple[Optional[Purchase], bool]:
        """Restaura una compra anterior.

        Es lo que hay detrás del botón "Restore Purchases", que Apple exige en
        toda app con producto no consumible: sin él, la revisión rechaza la
        entrega. El cliente pide sus transacciones a la tienda y manda la que
        encuentre; el servidor la verifica igual que una compra nueva.

        La diferencia con confirmar() está en qué significa no encontrar nada:
        una compra que no existe no es un fallo de cobro, es una cuenta que
        nunca compró, y la app tiene que poder distinguirlo para enseñar el
        mensaje correcto.
        """
        referencia = (payload or {}).get("externalId")
        if not referencia:
            # Sin recibo que presentar, lo único que se puede restaurar es lo
            # que ya conste a nombre de esta cuenta.
            compra = PurchaseRepository.find_completed_for_user(user_id)
            if compra is None:
                raise NoHayCompra(user_id)
            recien = PurchaseService._asegurar_acceso(user_id, utc_ahora())
            return compra, recien

        return PurchaseService.confirmar(user_id, provider, payload)

    # ------------------------------------------------------------------
    # Reembolsos
    # ------------------------------------------------------------------

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
    def sincronizar_con_tienda(
        provider: str, referencia: str, motivo: str = None
    ) -> Optional[str]:
        """Le pregunta a la tienda por una compra y ajusta lo que conste aquí.

        Es lo que hacen los webhooks. La notificación NO decide nada: solo dice
        qué compra mirar. Así, una notificación falsa —cualquiera puede mandar
        un POST— no puede revocar ni conceder nada, porque lo que manda es la
        respuesta de la tienda a una petición autenticada nuestra.

        Devuelve qué se hizo: "revocada", "sin cambios" o None si la compra no
        consta.
        """
        compra = PurchaseRepository.find_by_store_reference(provider, referencia)
        if compra is None:
            return None

        situacion = estado_en_tienda(provider, compra.external_id)

        if situacion == ESTADO_REVOCADA:
            if compra.status != PURCHASE_REFUNDED:
                PurchaseService.reembolsar(compra.id, motivo or "Reembolso de la tienda")
                return "revocada"
            return "sin cambios"

        if situacion == ESTADO_ACTIVA:
            return "sin cambios"

        # La tienda no sabe decirlo. No se toca nada: retirar un acceso por una
        # respuesta que no entendemos sería quitarle a alguien lo que pagó.
        return "sin cambios"

    @staticmethod
    def acusar_pendientes(limite: int = 200) -> Dict[str, int]:
        """Reintenta el acuse de recibo de las compras de Google que se quedaron sin él.

        Existe porque el acuse se hace después de conceder el acceso y puede
        fallar sin que nadie se entere: la petición ya se respondió con éxito.
        Google reembolsa a los 3 días, así que esto tiene que correr antes.
        """
        pendientes = PurchaseRepository.find_sin_acuse(PROVIDER_GOOGLE, limite)
        hechas = 0
        for compra in pendientes:
            if acusar_recibo(compra.provider, compra.external_id):
                PurchaseRepository.update(
                    compra.id, {"acknowledged_at": utc_ahora()})
                hechas += 1
        return {"revisadas": len(pendientes), "acusadas": hechas}

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

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
            # Precio de referencia. El que ve el comprador lo pone la tienda,
            # en su moneda y según el escalón elegido en App Store Connect y en
            # Play Console; la app debe enseñar el de la tienda, no este.
            "price": FULL_ACCESS_PRICE_USD,
            "currency": CURRENCY_USD,
        }
