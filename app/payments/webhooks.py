"""Notificaciones de las tiendas.

Aquí llegan los avisos de Apple (App Store Server Notifications V2) y de Google
(Real-time developer notifications, por Pub/Sub). Sirven para una cosa que la
app no puede contar: los reembolsos. Cuando alguien pide el dinero de vuelta y
la tienda se lo devuelve, nadie abre la app para avisarnos; si esto no existe,
la cuenta se queda con el contenido desbloqueado y sin haber pagado.

La regla de este módulo
-----------------------
**El contenido de la notificación no decide nada.** Estos dos endpoints son
públicos —tienen que serlo, los llama la tienda— y cualquiera puede mandarles
un POST diciendo lo que quiera. Así que del cuerpo se saca UNA cosa, el
identificador de la compra, y con él se va a preguntarle a la tienda por una
conexión autenticada nuestra. Lo que revoca o no revoca es esa respuesta.

Eso hace que una notificación falsificada no pueda hacer daño: lo peor que
consigue quien las invente es que le preguntemos a Apple por una compra. Es
también la razón de no verificar aquí la firma JWS de Apple ni el token OIDC de
Pub/Sub: no hay nada que proteger detrás, porque no nos fiamos del mensaje ni
aunque venga firmado.

Se responde 200 casi siempre. Un 4xx o un 5xx hace que la tienda reintente
—Apple durante tres días, Pub/Sub durante siete—, y no se quiere reintentar una
notificación que ya se procesó o que no nos interesa. El 500 se reserva para lo
único que sí conviene reintentar: que algo nuestro estuviera caído.
"""
import base64
import hmac
import json
from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, request

from app.payments.services import PurchaseService
from app.shared.constants import PROVIDER_APPLE, PROVIDER_GOOGLE
from app.shared.utils import format_response

# Tipos de aviso de Apple que significan "esta compra ya no vale".
APPLE_REEMBOLSOS = ("REFUND", "REVOKE")

# oneTimeProductNotification.notificationType de Google
GOOGLE_COMPRADA = 1
GOOGLE_CANCELADA = 2


def _autorizado() -> bool:
    """Secreto compartido opcional en la URL del webhook.

    Pub/Sub no deja añadir cabeceras a las entregas push, así que el único sitio
    donde cabe un secreto es la propia URL del endpoint que se configura en la
    consola. No es lo que protege el sistema —eso lo hace no fiarse del cuerpo—,
    solo evita que un curioso nos haga consultar la API de las tiendas a su
    gusto. Si no se configura, no se comprueba.
    """
    esperado = (current_app.config.get("STORE_WEBHOOK_SECRET") or "").strip()
    if not esperado:
        return True
    return hmac.compare_digest(esperado, request.args.get("token", ""))


def _cuerpo_jws(jws: str) -> Dict[str, Any]:
    """El payload de un JWS, sin comprobar la firma. Ver el docstring del módulo."""
    partes = (jws or "").split(".")
    if len(partes) < 2:
        return {}
    relleno = partes[1] + "=" * (-len(partes[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(relleno))
    except Exception:
        return {}


def _referencia_apple(cuerpo: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Saca (referencia, tipo de aviso) de una notificación V2."""
    firmado = (cuerpo or {}).get("signedPayload")
    if not firmado:
        return None, ""

    aviso = _cuerpo_jws(firmado)
    tipo = aviso.get("notificationType", "")
    datos = aviso.get("data") or {}

    transaccion = _cuerpo_jws(datos.get("signedTransactionInfo", ""))
    referencia = (
        transaccion.get("transactionId")
        or transaccion.get("originalTransactionId")
        or datos.get("originalTransactionId")
    )
    return (str(referencia) if referencia else None), tipo


def _referencia_google(cuerpo: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Saca (purchaseToken, tipo de aviso) de una RTDN."""
    mensaje = (cuerpo or {}).get("message") or {}
    datos = mensaje.get("data")
    if not datos:
        return None, ""

    relleno = datos + "=" * (-len(datos) % 4)
    try:
        aviso = json.loads(base64.urlsafe_b64decode(relleno))
    except Exception:
        return None, ""

    if "testNotification" in aviso:
        return None, "test"

    # Un reembolso llega como voidedPurchaseNotification y trae el token de la
    # compra anulada. Es la notificación que de verdad importa aquí.
    anulada = aviso.get("voidedPurchaseNotification") or {}
    if anulada.get("purchaseToken"):
        return str(anulada["purchaseToken"]), "voided"

    producto = aviso.get("oneTimeProductNotification") or {}
    if producto.get("purchaseToken"):
        return str(producto["purchaseToken"]), str(producto.get("notificationType", ""))

    return None, ""


def _ok(detalle: str, **extra):
    return jsonify(format_response(success=True, message=detalle, data=extra)), 200


class WebhookController:

    @staticmethod
    def apple():
        """App Store Server Notifications V2."""
        if not _autorizado():
            # 200 a propósito: si es ruido, que no lo reintenten.
            current_app.logger.warning("Webhook de Apple con secreto incorrecto")
            return _ok("ignored")

        referencia, tipo = _referencia_apple(request.get_json(silent=True) or {})
        current_app.logger.info("Aviso de Apple: %s (%s)", tipo, referencia)

        if not referencia:
            return _ok("ignored", reason="sin referencia")

        # Se sincroniza con cualquier aviso, no solo con los de reembolso: el
        # tipo viene del mensaje, del que no nos fiamos. Preguntar de más a la
        # tienda es barato; dar por buena una clasificación que nos han mandado,
        # no.
        try:
            resultado = PurchaseService.sincronizar_con_tienda(
                PROVIDER_APPLE, referencia,
                motivo=f"App Store: {tipo}" if tipo in APPLE_REEMBOLSOS else None,
            )
        except Exception as e:
            # 500 para que Apple reintente: esto sí conviene recuperarlo.
            current_app.logger.exception("Fallo procesando aviso de Apple: %s", e)
            return jsonify(format_response(
                success=False, error="Internal error")), 500

        if resultado is None:
            return _ok("ignored", reason="compra desconocida")
        return _ok(resultado)

    @staticmethod
    def google():
        """Real-time developer notifications de Google Play (Pub/Sub push)."""
        if not _autorizado():
            current_app.logger.warning("Webhook de Google con secreto incorrecto")
            return _ok("ignored")

        referencia, tipo = _referencia_google(request.get_json(silent=True) or {})
        current_app.logger.info("Aviso de Google: %s (%s)", tipo, referencia)

        if tipo == "test":
            # Play Console manda una de estas al configurar el tema. Contestar
            # 200 es justo lo que comprueba.
            return _ok("test notification received")

        if not referencia:
            return _ok("ignored", reason="sin referencia")

        try:
            resultado = PurchaseService.sincronizar_con_tienda(
                PROVIDER_GOOGLE, referencia,
                motivo="Google Play: compra anulada" if tipo == "voided" else None,
            )
        except Exception as e:
            current_app.logger.exception("Fallo procesando aviso de Google: %s", e)
            return jsonify(format_response(
                success=False, error="Internal error")), 500

        if resultado is None:
            return _ok("ignored", reason="compra desconocida")
        return _ok(resultado)
