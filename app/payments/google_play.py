"""Verificación de compras de Google Play.

Dos llamadas a la Play Developer API, y la segunda NO es opcional:

  1. purchases.products.get   ¿existe esta compra y está pagada?
  2. purchases.products.acknowledge   acusar recibo

Si una compra no se acusa en **3 días**, Google la reembolsa sola y el
comprador se queda sin cargo. Nadie se entera: no hay error, no hay aviso, solo
un ingreso que nunca llega. Por eso el acuse se guarda en
`purchases.acknowledged_at` y hay un comando (`flask payments acusar-pendientes`)
para barrer las que se quedaron sin acusar porque la llamada falló.

La autenticación es una cuenta de servicio: se firma un JWT RS256 con su clave
privada, se cambia por un token de acceso en oauth2.googleapis.com y ese token
dura una hora. Se cachea en memoria porque pedir uno por compra sería una
llamada de red de más en el peor momento posible —el usuario mirando una rueda
después de pagar—.
"""
import json
import threading
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
from app.shared.constants import PROVIDER_GOOGLE

URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_API = "https://androidpublisher.googleapis.com/androidpublisher/v3"
ALCANCE = "https://www.googleapis.com/auth/androidpublisher"
TIEMPO_ESPERA = 15

# purchaseState de la Play Developer API
COMPRADA = 0
CANCELADA = 1
PENDIENTE = 2

ACUSADA = 1

# Token de acceso cacheado. Hay un lock porque gunicorn corre varios hilos por
# proceso y dos compras simultáneas pedirían dos tokens.
_cache: Dict[str, Any] = {"token": None, "expira": 0.0}
_cerrojo = threading.Lock()


def _credenciales() -> Optional[Dict[str, Any]]:
    """El JSON de la cuenta de servicio, pegado o en un fichero."""
    pegado = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_JSON") or ""
    if pegado.strip():
        try:
            return json.loads(pegado)
        except json.JSONDecodeError as e:
            raise PaymentVerificationError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON válido: {e}"
            ) from e

    ruta = (current_app.config.get("GOOGLE_SERVICE_ACCOUNT_PATH") or "").strip()
    if ruta:
        try:
            with open(ruta, "r", encoding="utf-8") as fichero:
                return json.load(fichero)
        except (OSError, json.JSONDecodeError) as e:
            raise PaymentVerificationError(
                f"No se pudo leer la cuenta de servicio de Google: {e}"
            ) from e

    return None


def configurado() -> Tuple[bool, str]:
    faltan = [
        nombre for nombre in ("GOOGLE_PACKAGE_NAME", "GOOGLE_PRODUCT_ID")
        if not (current_app.config.get(nombre) or "").strip()
    ]
    try:
        if _credenciales() is None:
            faltan.append("GOOGLE_SERVICE_ACCOUNT_JSON (o GOOGLE_SERVICE_ACCOUNT_PATH)")
    except PaymentVerificationError as e:
        return False, str(e)

    if faltan:
        return False, "falta " + ", ".join(faltan)
    return True, ""


def _token_acceso() -> str:
    ahora = time.time()
    with _cerrojo:
        # 60 s de margen: un token que caduca mientras viaja la petición es un
        # 401 intermitente imposible de reproducir.
        if _cache["token"] and _cache["expira"] - 60 > ahora:
            return _cache["token"]

        credenciales = _credenciales()
        if credenciales is None:
            raise PaymentVerificationError(
                "No hay cuenta de servicio de Google configurada"
            )

        try:
            import jwt  # PyJWT
        except ImportError as e:  # pragma: no cover - dependencia fija
            raise PaymentVerificationError(
                "Falta PyJWT para firmar la aserción de Google"
            ) from e

        emitido = int(ahora)
        try:
            asercion = jwt.encode(
                {
                    "iss": credenciales["client_email"],
                    "scope": ALCANCE,
                    "aud": URL_TOKEN,
                    "iat": emitido,
                    "exp": emitido + 3600,
                },
                credenciales["private_key"],
                algorithm="RS256",
            )
        except KeyError as e:
            raise PaymentVerificationError(
                f"A la cuenta de servicio de Google le falta el campo {e}"
            ) from e
        except Exception as e:
            raise PaymentVerificationError(
                f"No se pudo firmar la aserción de Google: {e}"
            ) from e

        try:
            respuesta = requests.post(
                URL_TOKEN,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": asercion,
                },
                timeout=TIEMPO_ESPERA,
            )
        except requests.RequestException as e:
            raise PaymentVerificationError(
                f"No se pudo pedir el token a Google: {e}"
            ) from e

        if respuesta.status_code != 200:
            raise PaymentVerificationError(
                "Google rechazó la cuenta de servicio "
                f"({respuesta.status_code}): {respuesta.text[:200]}"
            )

        datos = respuesta.json() or {}
        token = datos.get("access_token")
        if not token:
            raise PaymentVerificationError("Google devolvió una respuesta sin token")

        _cache["token"] = token
        _cache["expira"] = ahora + float(datos.get("expires_in", 3600))
        return token


def _url_compra(purchase_token: str) -> str:
    paquete = current_app.config["GOOGLE_PACKAGE_NAME"]
    producto = current_app.config["GOOGLE_PRODUCT_ID"]
    return (
        f"{URL_API}/applications/{paquete}"
        f"/purchases/products/{producto}/tokens/{purchase_token}"
    )


def _consultar(purchase_token: str) -> Optional[Dict[str, Any]]:
    """purchases.products.get. None si Google no conoce el token."""
    try:
        respuesta = requests.get(
            _url_compra(purchase_token),
            headers={"Authorization": f"Bearer {_token_acceso()}"},
            timeout=TIEMPO_ESPERA,
        )
    except requests.RequestException as e:
        raise PaymentVerificationError(f"No se pudo hablar con Google Play: {e}") from e

    if respuesta.status_code == 200:
        return respuesta.json() or {}

    if respuesta.status_code in (404, 410):
        return None

    if respuesta.status_code in (401, 403):
        raise PaymentVerificationError(
            "Google rechazó nuestros permisos "
            f"({respuesta.status_code}). Revisa que la cuenta de servicio tenga "
            "acceso a la app en Play Console."
        )

    raise PaymentVerificationError(
        f"Google Play respondió {respuesta.status_code}: {respuesta.text[:200]}"
    )


def verificar(payload: Dict[str, Any]) -> ResultadoVerificacion:
    """Comprueba un purchaseToken de Play Billing contra Google."""
    listo, motivo = configurado()
    if not listo:
        raise PaymentVerificationError(
            f"El cobro por Google Play no está configurado en el servidor: {motivo}"
        )

    purchase_token = (payload or {}).get("externalId")
    if not purchase_token:
        raise PaymentVerificationError("Falta el purchaseToken de la compra")

    compra = _consultar(purchase_token)
    if compra is None:
        raise PaymentVerificationError("Google no conoce esta compra")

    estado_compra = compra.get("purchaseState")
    if estado_compra == CANCELADA:
        raise PaymentVerificationError("Google canceló o reembolsó esta compra")
    if estado_compra == PENDIENTE:
        # Pago en efectivo en una tienda física, por ejemplo. Todavía no hay
        # dinero: no se concede nada y la app vuelve a preguntar más tarde.
        raise PaymentVerificationError("La compra sigue pendiente de pago")
    if estado_compra != COMPRADA:
        raise PaymentVerificationError(
            f"La compra está en un estado inesperado ({estado_compra})"
        )

    # Si la app mandó el id de usuario al iniciar la compra, tiene que coincidir.
    # Cuando no lo manda, el campo no viene y no se comprueba nada: la validación
    # que sí existe siempre es la de `external_id` único en base de datos.
    cuenta = str(compra.get("obfuscatedExternalAccountId") or "")

    return ResultadoVerificacion(
        provider=PROVIDER_GOOGLE,
        referencia=purchase_token,
        entorno=(
            "Sandbox"
            if compra.get("purchaseType") == 0     # 0 = compra de prueba
            else "Production"
        ),
        referencia_original=str(compra.get("orderId") or ""),
        requiere_acuse=compra.get("acknowledgementState") != ACUSADA,
        producto=current_app.config.get("GOOGLE_PRODUCT_ID", ""),
        cuenta_externa=cuenta,
    )


def acusar_recibo(purchase_token: str) -> bool:
    """purchases.products.acknowledge. True si quedó acusada.

    No lanza hacia arriba: esto se llama DESPUÉS de haber concedido el acceso, y
    un fallo aquí no debe deshacer una compra buena ni devolverle un error a
    quien acaba de pagar. Lo que sí hace es dejarlo en el log y devolver False
    para que la fila no se marque como acusada y el barrido la reintente.
    """
    try:
        respuesta = requests.post(
            f"{_url_compra(purchase_token)}:acknowledge",
            headers={
                "Authorization": f"Bearer {_token_acceso()}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=TIEMPO_ESPERA,
        )
    except (requests.RequestException, PaymentVerificationError) as e:
        current_app.logger.error(
            "NO SE PUDO ACUSAR RECIBO A GOOGLE (se reembolsará en 3 días): %s", e
        )
        return False

    # 204 es lo normal; 200 también aparece. 400 con "already acknowledged"
    # significa que ya estaba bien, así que cuenta como éxito.
    if respuesta.status_code in (200, 204):
        return True

    if respuesta.status_code == 400 and "already" in respuesta.text.lower():
        return True

    current_app.logger.error(
        "NO SE PUDO ACUSAR RECIBO A GOOGLE (se reembolsará en 3 días): %s %s",
        respuesta.status_code, respuesta.text[:200],
    )
    return False


def _esta_anulada(purchase_token: str, dias: int = 90) -> bool:
    """¿Aparece este token en la lista de compras anuladas?

    Hace falta porque cuando Google revoca una compra puede dejar de reconocer
    su token en `purchases.products.get`, y entonces un 404 sería ambiguo: no se
    sabría si la compra se anuló o si el token nunca existió. `voidedpurchases`
    lo resuelve sin ambigüedad y, sobre todo, lo dice Google: es lo que permite
    revocar un acceso a partir de una notificación sin fiarse de la notificación.
    """
    fin = int(time.time() * 1000)
    inicio = fin - dias * 24 * 60 * 60 * 1000
    paquete = current_app.config["GOOGLE_PACKAGE_NAME"]

    pagina = None
    for _ in range(10):        # tope de páginas: no se barre el histórico entero
        parametros = {
            "startTime": inicio,
            "endTime": fin,
            "type": 0,          # solo productos, no suscripciones
            "maxResults": 1000,
        }
        if pagina:
            parametros["token"] = pagina

        try:
            respuesta = requests.get(
                f"{URL_API}/applications/{paquete}/purchases/voidedpurchases",
                headers={"Authorization": f"Bearer {_token_acceso()}"},
                params=parametros,
                timeout=TIEMPO_ESPERA,
            )
        except (requests.RequestException, PaymentVerificationError) as e:
            current_app.logger.warning("No se pudo listar compras anuladas: %s", e)
            return False

        if respuesta.status_code != 200:
            current_app.logger.warning(
                "voidedpurchases respondió %s", respuesta.status_code)
            return False

        datos = respuesta.json() or {}
        for anulada in datos.get("voidedPurchases", []):
            if anulada.get("purchaseToken") == purchase_token:
                return True

        pagina = (datos.get("tokenPagination") or {}).get("nextPageToken")
        if not pagina:
            return False

    return False


def estado(referencia: str) -> str:
    """Estado actual de una compra, para los webhooks. No lanza."""
    try:
        compra = _consultar(referencia)
    except PaymentVerificationError as e:
        current_app.logger.warning("No se pudo consultar a Google Play: %s", e)
        return ESTADO_DESCONOCIDA

    if compra is None:
        # El token ya no existe. Puede ser una compra anulada —que es lo que se
        # está mirando— o un token inventado. Lo desempata Google, no nosotros.
        return ESTADO_REVOCADA if _esta_anulada(referencia) else ESTADO_DESCONOCIDA

    if compra.get("purchaseState") == CANCELADA:
        return ESTADO_REVOCADA
    if compra.get("purchaseState") == COMPRADA:
        # Una compra puede seguir en estado "comprada" y estar anulada por una
        # devolución tramitada desde la consola: la lista de anuladas es la que
        # manda.
        return ESTADO_REVOCADA if _esta_anulada(referencia) else ESTADO_ACTIVA
    return ESTADO_DESCONOCIDA
