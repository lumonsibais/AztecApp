"""Verificación de cobros por proveedor.

ESTA ES LA COSTURA que deja el cobro sin decidir sin bloquear el resto.

Todo el backend consulta `users.has_full_access`. Lo único que depende de si se
cobra por las tiendas o por pasarela propia es esta función: recibe lo que
mande el cliente y devuelve una referencia verificada, o revienta.

Ahora mismo NINGÚN proveedor real está implementado, y eso es intencionado:
aceptar un recibo sin verificarlo sería regalar el contenido a quien mandara
una petición inventada. Por eso, salvo que la configuración lo permita
explícitamente (solo en desarrollo), cualquier confirmación se rechaza.

Cuando se decida la pasarela, aquí van:
  - stripe: recuperar el PaymentIntent y comprobar que está `succeeded` y que
    el importe coincide.
  - apple:  POST a verifyReceipt / App Store Server API y validar la firma.
  - google: androidpublisher.purchases.products.get con el purchaseToken.
"""
from flask import current_app

from app.shared.constants import PROVIDER_MANUAL, PROVIDERS


class PaymentVerificationError(Exception):
    """El cobro no se pudo verificar y no se debe conceder acceso."""


def verificar(provider: str, payload: dict) -> str:
    """Comprueba el cobro y devuelve la referencia externa.

    Lanza PaymentVerificationError si no se puede verificar. Nunca devuelve
    una referencia "confiando" en el cliente.
    """
    if provider not in PROVIDERS:
        raise PaymentVerificationError(f"Proveedor desconocido: {provider}")

    referencia = (payload or {}).get("externalId")
    if not referencia:
        raise PaymentVerificationError("Falta la referencia del proveedor")

    # Puerta de desarrollo. Se enciende con PAYMENTS_ALLOW_UNVERIFIED=true y
    # permite dar de alta compras a mano para poder probar el flujo completo
    # sin pasarela. La configuración de producción la deja apagada.
    if current_app.config.get("PAYMENTS_ALLOW_UNVERIFIED"):
        return referencia

    if provider == PROVIDER_MANUAL:
        raise PaymentVerificationError(
            "Las altas manuales solo se permiten con PAYMENTS_ALLOW_UNVERIFIED"
        )

    raise PaymentVerificationError(
        f"La verificación de cobros con {provider} todavía no está implementada. "
        "Falta decidir si se cobra dentro de las tiendas o por pasarela propia."
    )
