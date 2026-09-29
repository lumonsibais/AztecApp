"""Costura con las tiendas.

El cobro se hace desde la App Store y desde Google Play. El servidor no cobra:
cobra la tienda, y aquí lo único que se hace es comprobar contra ella que el
recibo que presenta la app es cierto, es nuestro y sigue vivo.

Lo que llega del cliente no se cree nunca. Un `externalId` es una cadena que
cualquiera puede escribir; lo que concede el acceso es la respuesta de Apple o
de Google, no la petición del móvil.

Qué es `externalId` según el proveedor:

    apple    el transactionId de StoreKit 2
    google   el purchaseToken de Play Billing

Es un solo campo porque solo hay un producto. El identificador del producto no
viaja en la petición: está en la configuración del servidor, y así el cliente no
puede pedir que se le verifique "otro" producto.

`stripe` sigue en la lista de proveedores pero no tiene implementación y no debe
tenerla mientras el desbloqueo se venda dentro de la app: Apple y Google no
permiten cobrar contenido digital por fuera de su sistema, y ofrecerlo es motivo
de rechazo en revisión. La constante se queda por si algún día hay una compra
desde web, que es el único sitio donde sería legítima.
"""
from typing import Any, Dict

from flask import current_app

from app.payments import apple, google_play
from app.payments.verificacion import (
    ESTADO_ACTIVA,
    ESTADO_DESCONOCIDA,
    ESTADO_REVOCADA,
    PaymentVerificationError,
    ResultadoVerificacion,
)
from app.shared.constants import (
    PROVIDER_APPLE,
    PROVIDER_GOOGLE,
    PROVIDER_MANUAL,
    PROVIDER_STRIPE,
    PROVIDERS,
)

__all__ = [
    "ESTADO_ACTIVA",
    "ESTADO_DESCONOCIDA",
    "ESTADO_REVOCADA",
    "PaymentVerificationError",
    "ResultadoVerificacion",
    "acusar_recibo",
    "estado",
    "verificar",
]

_TIENDAS = {
    PROVIDER_APPLE: apple,
    PROVIDER_GOOGLE: google_play,
}


def verificar(provider: str, payload: Dict[str, Any]) -> ResultadoVerificacion:
    """Comprueba un cobro contra su tienda.

    Devuelve lo que la tienda confirma. Lanza PaymentVerificationError si no lo
    confirma, y entonces no se concede nada.
    """
    if provider not in PROVIDERS:
        raise PaymentVerificationError(f"Proveedor desconocido: {provider}")

    referencia = (payload or {}).get("externalId")
    if not referencia:
        raise PaymentVerificationError("Falta la referencia del proveedor")

    # Puerta de desarrollo. Con PAYMENTS_ALLOW_UNVERIFIED encendido se concede
    # el acceso sin preguntar a nadie, que es lo único que permite probar la app
    # desbloqueada sin cuentas de prueba en las dos tiendas. Fuera de una máquina
    # de desarrollo va apagado: con esto encendido, cualquiera se desbloquea la
    # app mandando una cadena inventada.
    if current_app.config.get("PAYMENTS_ALLOW_UNVERIFIED"):
        current_app.logger.warning(
            "PAYMENTS_ALLOW_UNVERIFIED: concediendo acceso SIN verificar (%s)",
            provider,
        )
        return ResultadoVerificacion(
            provider=provider, referencia=referencia, entorno="Unverified"
        )

    tienda = _TIENDAS.get(provider)
    if tienda is not None:
        return tienda.verificar(payload)

    if provider == PROVIDER_MANUAL:
        # Altas a mano: cortesías, soporte, pruebas. Se conceden desde la
        # consola del servidor, no por esta ruta, para que no exista un camino
        # en la API pública que regale accesos.
        raise PaymentVerificationError(
            "Las altas manuales se conceden desde la consola, no por la API"
        )

    if provider == PROVIDER_STRIPE:
        raise PaymentVerificationError(
            "El desbloqueo se cobra desde las tiendas; no hay cobro por Stripe"
        )

    raise PaymentVerificationError(f"Proveedor sin implementar: {provider}")


def acusar_recibo(provider: str, referencia: str) -> bool:
    """Acusa recibo de la compra si su tienda lo exige.

    Solo Google lo exige, y no es un detalle: una compra sin acusar en 3 días se
    reembolsa sola. Devuelve True si no hacía falta o si quedó hecho.
    """
    if provider != PROVIDER_GOOGLE:
        return True
    if current_app.config.get("PAYMENTS_ALLOW_UNVERIFIED"):
        return True
    return google_play.acusar_recibo(referencia)


def estado(provider: str, referencia: str) -> str:
    """Vuelve a preguntarle a la tienda por una compra ya registrada.

    Es lo que usan los webhooks: la notificación solo dice "mira esta compra", y
    la verdad se pide aquí. Devuelve ESTADO_ACTIVA, ESTADO_REVOCADA o
    ESTADO_DESCONOCIDA, y no lanza.
    """
    tienda = _TIENDAS.get(provider)
    if tienda is None:
        return ESTADO_DESCONOCIDA
    return tienda.estado(referencia)
