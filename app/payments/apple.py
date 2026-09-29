"""Verificación de compras de la App Store.

`verifyReceipt` está obsoleto desde 2023 y Apple ya no lo recomienda para
código nuevo. Lo que se usa aquí es la **App Store Server API**:

    GET /inApps/v1/transactions/{transactionId}

autenticada con una clave de App Store Connect (issuer id + key id + un .p8 de
curva elíptica) firmando un JWT ES256. La respuesta trae `signedTransactionInfo`,
un JWS cuyo payload describe la transacción.

Sobre la firma del JWS
----------------------
El JWS viene firmado por Apple y la forma canónica de comprobarlo es validar la
cadena de certificados del encabezado `x5c` contra la Apple Root CA G3. Aquí no
se hace, y es una decisión, no un olvido: este JWS no nos lo ha mandado un
cliente, lo hemos ido a buscar nosotros por HTTPS a `api.storekit.itunes.apple.com`
autenticándonos con nuestra clave. El canal ya prueba el origen. Validar además
la firma no añadiría nada que TLS no diga ya.

Donde sí haría falta es al recibir una notificación en un webhook, porque ahí el
payload lo manda quien quiera. Por eso el webhook NO se fía del payload: extrae
el identificador y vuelve aquí a preguntar. Ver `app/payments/webhooks.py`.

El día que se quiera la validación completa de la cadena, la biblioteca oficial
`app-store-server-library` la trae hecha.
"""
import base64
import json
import time
from typing import Any, Dict, Optional, Tuple

import requests
from flask import current_app

from app.payments.verificacion import (
    ESTADO_ACTIVA,
    ESTADO_DESCONOCIDA,
    ESTADO_REVOCADA,
    PaymentVerificationError,
    ResultadoVerificacion,
)
from app.shared.constants import PROVIDER_APPLE

HOST_PRODUCCION = "https://api.storekit.itunes.apple.com"
HOST_SANDBOX = "https://api.storekit-sandbox.itunes.apple.com"

AUDIENCIA = "appstoreconnect-v1"
ALCANCE_TOKEN = 20 * 60          # Apple rechaza tokens de más de 60 minutos
TIEMPO_ESPERA = 15               # segundos

# Tipos de propiedad que dan acceso. FAMILY_SHARED aparece cuando la compra se
# comparte en familia, que Apple espera que se respete si está activado en App
# Store Connect; si no lo está, nunca llega.
PROPIEDAD_VALIDA = ("PURCHASED", "FAMILY_SHARED")


def _config(clave: str) -> str:
    return (current_app.config.get(clave) or "").strip()


def _clave_privada() -> str:
    """El contenido del .p8.

    Se admite pegado en una variable de entorno o como ruta a un fichero. La
    ruta es más cómoda en local; la variable es lo único que hay en un
    contenedor.
    """
    pegada = current_app.config.get("APPLE_PRIVATE_KEY") or ""
    if pegada.strip():
        # En un .env las saltos de línea de una clave PEM se escriben "\n".
        return pegada.replace("\\n", "\n").strip()

    ruta = _config("APPLE_PRIVATE_KEY_PATH")
    if ruta:
        try:
            with open(ruta, "r", encoding="utf-8") as fichero:
                return fichero.read().strip()
        except OSError as e:
            raise PaymentVerificationError(
                f"No se pudo leer la clave de App Store Connect: {e}"
            ) from e

    return ""


def configurado() -> Tuple[bool, str]:
    """¿Están las credenciales? Devuelve (sí/no, qué falta)."""
    faltan = [
        nombre for nombre in (
            "APPLE_BUNDLE_ID", "APPLE_ISSUER_ID", "APPLE_KEY_ID", "APPLE_PRODUCT_ID",
        ) if not _config(nombre)
    ]
    if not _clave_privada():
        faltan.append("APPLE_PRIVATE_KEY (o APPLE_PRIVATE_KEY_PATH)")

    if faltan:
        return False, "falta " + ", ".join(faltan)
    return True, ""


def _token() -> str:
    """JWT ES256 para la App Store Server API."""
    try:
        import jwt  # PyJWT
    except ImportError as e:  # pragma: no cover - dependencia fija
        raise PaymentVerificationError(
            "Falta PyJWT para firmar el token de App Store Connect"
        ) from e

    ahora = int(time.time())
    try:
        return jwt.encode(
            {
                "iss": _config("APPLE_ISSUER_ID"),
                "iat": ahora,
                "exp": ahora + ALCANCE_TOKEN,
                "aud": AUDIENCIA,
                "bid": _config("APPLE_BUNDLE_ID"),
            },
            _clave_privada(),
            algorithm="ES256",
            headers={"kid": _config("APPLE_KEY_ID"), "typ": "JWT"},
        )
    except Exception as e:
        # Una clave mal pegada se ve aquí y en ningún otro sitio.
        raise PaymentVerificationError(
            f"No se pudo firmar el token de App Store Connect: {e}"
        ) from e


def _payload_jws(jws: str) -> Dict[str, Any]:
    """El cuerpo de un JWS, sin comprobar la firma (ver el docstring del módulo)."""
    try:
        cuerpo = jws.split(".")[1]
        # base64url sin relleno: hay que devolvérselo.
        cuerpo += "=" * (-len(cuerpo) % 4)
        return json.loads(base64.urlsafe_b64decode(cuerpo))
    except Exception as e:
        raise PaymentVerificationError(
            f"Apple devolvió una transacción ilegible: {e}"
        ) from e


def _consultar(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Pregunta a Apple por una transacción. None si no la conoce.

    Se pregunta primero a producción y, si ahí no existe, a sandbox. Ese es el
    orden que recomienda Apple y el único que funciona durante la revisión de
    la app: el revisor compra en sandbox contra el binario de producción.
    """
    hosts = [HOST_PRODUCCION]
    if current_app.config.get("APPLE_ALLOW_SANDBOX"):
        hosts.append(HOST_SANDBOX)

    cabeceras = {"Authorization": f"Bearer {_token()}"}
    ultimo_error = None

    for host in hosts:
        url = f"{host}/inApps/v1/transactions/{transaction_id}"
        try:
            respuesta = requests.get(url, headers=cabeceras, timeout=TIEMPO_ESPERA)
        except requests.RequestException as e:
            ultimo_error = f"no se pudo hablar con {host}: {e}"
            continue

        if respuesta.status_code == 200:
            firmado = (respuesta.json() or {}).get("signedTransactionInfo")
            if not firmado:
                raise PaymentVerificationError(
                    "Apple respondió sin signedTransactionInfo"
                )
            return _payload_jws(firmado)

        if respuesta.status_code == 404:
            continue  # en este entorno no existe; se prueba el siguiente

        if respuesta.status_code in (401, 403):
            raise PaymentVerificationError(
                "App Store Connect rechazó nuestras credenciales "
                f"({respuesta.status_code}). Revisa issuer id, key id y el .p8."
            )

        ultimo_error = f"{host} respondió {respuesta.status_code}"

    if ultimo_error:
        raise PaymentVerificationError(f"No se pudo verificar con Apple: {ultimo_error}")

    return None


def _revisar(transaccion: Dict[str, Any]) -> None:
    """Comprueba que la transacción es la nuestra y sigue viva.

    Lanza PaymentVerificationError con el motivo concreto: cuando alguien
    escriba a soporte diciendo que pagó y la app no se abre, el motivo exacto
    es lo único que hace falta.
    """
    bundle = transaccion.get("bundleId")
    if bundle != _config("APPLE_BUNDLE_ID"):
        raise PaymentVerificationError(
            f"La compra es de otra app (bundleId '{bundle}')"
        )

    producto = transaccion.get("productId")
    if producto != _config("APPLE_PRODUCT_ID"):
        raise PaymentVerificationError(
            f"La compra es de otro producto ('{producto}')"
        )

    # El desbloqueo es un no consumible. Si esto llega como consumible o como
    # suscripción, el identificador del producto está mal configurado en App
    # Store Connect, y conceder un acceso permanente por una suscripción sería
    # regalar el contenido.
    tipo = transaccion.get("type")
    if tipo and tipo != "Non-Consumable":
        raise PaymentVerificationError(
            f"La compra no es un no consumible (type '{tipo}')"
        )

    propiedad = transaccion.get("inAppOwnershipType")
    if propiedad and propiedad not in PROPIEDAD_VALIDA:
        raise PaymentVerificationError(
            f"La compra no pertenece a quien la presenta ('{propiedad}')"
        )

    if transaccion.get("revocationDate"):
        motivo = transaccion.get("revocationReason")
        raise PaymentVerificationError(
            f"Apple revocó esta compra (reembolso, motivo {motivo})"
        )

    entorno = transaccion.get("environment", "")
    if entorno == "Sandbox" and not current_app.config.get("APPLE_ALLOW_SANDBOX"):
        raise PaymentVerificationError(
            "Es una compra de sandbox y este servidor solo acepta producción"
        )


def verificar(payload: Dict[str, Any]) -> ResultadoVerificacion:
    """Comprueba un transactionId de StoreKit contra Apple."""
    listo, motivo = configurado()
    if not listo:
        raise PaymentVerificationError(
            f"El cobro por App Store no está configurado en el servidor: {motivo}"
        )

    transaction_id = (payload or {}).get("externalId")
    if not transaction_id:
        raise PaymentVerificationError("Falta el transactionId de la compra")

    transaccion = _consultar(transaction_id)
    if transaccion is None:
        raise PaymentVerificationError(
            "Apple no conoce esta transacción"
        )

    _revisar(transaccion)

    return ResultadoVerificacion(
        provider=PROVIDER_APPLE,
        # Se guarda el transactionId que Apple confirma, no el que mandó el
        # cliente: si difirieran, el bueno es el de Apple.
        referencia=str(transaccion.get("transactionId") or transaction_id),
        entorno=transaccion.get("environment", ""),
        referencia_original=str(transaccion.get("originalTransactionId") or ""),
        requiere_acuse=False,          # Apple no tiene acuse de recibo
        producto=transaccion.get("productId", ""),
        cuenta_externa=str(transaccion.get("appAccountToken") or ""),
    )


def estado(referencia: str) -> str:
    """Estado actual de una compra, para los webhooks.

    No lanza: un webhook que no puede resolver el estado no debe tumbar la
    petición, porque la tienda la reintentaría en bucle.
    """
    try:
        transaccion = _consultar(referencia)
    except PaymentVerificationError as e:
        current_app.logger.warning("No se pudo consultar a Apple: %s", e)
        return ESTADO_DESCONOCIDA

    if transaccion is None:
        return ESTADO_DESCONOCIDA
    if transaccion.get("revocationDate"):
        return ESTADO_REVOCADA
    return ESTADO_ACTIVA
