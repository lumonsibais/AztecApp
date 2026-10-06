"""Cobro desde las tiendas: App Store y Google Play.

No hay forma de probar aquí la integración de verdad —haría falta una cuenta de
prueba en cada tienda y una compra real—, así que lo que se prueba es lo que sí
se puede probar sin ellas: que ante CADA respuesta que las tiendas saben dar,
este backend hace lo correcto. Las respuestas están copiadas de la forma que
documentan Apple y Google.

Lo que estos tests defienden, en una línea cada uno:

  - un recibo que la tienda no confirma no desbloquea nada
  - un recibo revocado o reembolsado no desbloquea nada
  - un recibo de sandbox no desbloquea un servidor de producción
  - un recibo de otra app o de otro producto no desbloquea nada
  - un recibo ajeno no desbloquea una segunda cuenta
  - una compra de Google sin acusar no se marca como acusada
  - una notificación falsa no revoca nada
"""
import base64
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.payments import apple, google_play
from app.payments.models import Purchase
from app.payments.providers import PaymentVerificationError, verificar
from app.payments.repositories import PurchaseRepository
from app.payments.services import PurchaseService, ReciboDeOtraCuenta
from app.users.repositories import UserRepository

BUNDLE = "com.aztecapp.explorer"
PRODUCTO_APPLE = "com.aztecapp.explorer.fullaccess"
PAQUETE = "com.aztecapp.explorer"
PRODUCTO_GOOGLE = "full_access"

# Un purchaseToken real de Google ronda los 350 caracteres. Este mide lo mismo
# a propósito: es lo que destapó que la columna era VARCHAR(255).
TOKEN_GOOGLE = "hjkcnmqwertyuiopasdfghjklzxcvbnm" * 11


def registrar(client, email="tienda@example.com"):
    r = client.post("/api/users/register",
                    json={"email": email, "password": "testpassword123"})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def auth(tokens):
    return {"Authorization": "Bearer " + tokens["accessToken"]}


@pytest.fixture
def tiendas(app):
    """Credenciales de mentira, suficientes para pasar el `configurado()`."""
    app.config.update(
        PAYMENTS_ALLOW_UNVERIFIED=False,
        APPLE_BUNDLE_ID=BUNDLE,
        APPLE_ISSUER_ID="57246542-96fe-1a63-e053-0824d011072a",
        APPLE_KEY_ID="ABC123DEFG",
        APPLE_PRODUCT_ID=PRODUCTO_APPLE,
        APPLE_PRIVATE_KEY="-- no se usa, se parchea la firma --",
        APPLE_ALLOW_SANDBOX=False,
        GOOGLE_PACKAGE_NAME=PAQUETE,
        GOOGLE_PRODUCT_ID=PRODUCTO_GOOGLE,
        GOOGLE_SERVICE_ACCOUNT_JSON=json.dumps({
            "client_email": "compras@aztec.iam.gserviceaccount.com",
            "private_key": "-- no se usa, se parchea el token --",
        }),
    )
    return app


# --------------------------------------------------------------------------
# Respuestas de mentira con la forma de las de verdad
# --------------------------------------------------------------------------

def transaccion_apple(**cambios):
    base = {
        "transactionId": "2000000123456789",
        "originalTransactionId": "2000000123456789",
        "bundleId": BUNDLE,
        "productId": PRODUCTO_APPLE,
        "type": "Non-Consumable",
        "inAppOwnershipType": "PURCHASED",
        "environment": "Production",
        "purchaseDate": 1759000000000,
    }
    base.update(cambios)
    return base


def compra_google(**cambios):
    base = {
        "purchaseTimeMillis": "1759000000000",
        "purchaseState": 0,          # comprada
        "consumptionState": 0,
        "acknowledgementState": 0,   # SIN acusar
        "orderId": "GPA.1234-5678-9012-34567",
        "purchaseType": None,
    }
    base.update(cambios)
    return base


class RespuestaFalsa:
    def __init__(self, status_code, cuerpo=None, texto=""):
        self.status_code = status_code
        self._cuerpo = cuerpo if cuerpo is not None else {}
        self.text = texto or json.dumps(self._cuerpo)

    def json(self):
        return self._cuerpo


def jws_de(payload: dict) -> str:
    """Un JWS con el payload pedido. La firma no importa: no se comprueba."""
    cuerpo = base64.urlsafe_b64encode(
        json.dumps(payload).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJFUzI1NiJ9.{cuerpo}.firma"


# --------------------------------------------------------------------------
# Apple
# --------------------------------------------------------------------------

def _apple_responde(transaccion=None, status=200):
    """Parchea la llamada HTTP a Apple y la firma del token."""
    cuerpo = ({"signedTransactionInfo": jws_de(transaccion)}
              if transaccion is not None else {})
    return (
        patch.object(apple, "_token", return_value="token-falso"),
        patch.object(apple.requests, "get",
                     return_value=RespuestaFalsa(status, cuerpo)),
    )


def test_apple_concede_el_acceso_con_una_compra_valida(client, tiendas):
    tokens = registrar(client, "apple-ok@example.com")
    p1, p2 = _apple_responde(transaccion_apple())

    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(tokens))

    assert r.status_code == 200, r.get_json()
    datos = r.get_json()["data"]
    assert datos["status"] == "completed"
    assert datos["provider"] == "apple"

    estado = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert estado["hasFullAccess"] is True


def test_apple_guarda_la_referencia_original_y_el_entorno(client, tiendas, app):
    """Sin originalTransactionId no hay forma de casar un reembolso con su compra."""
    tokens = registrar(client, "apple-ref@example.com")
    p1, p2 = _apple_responde(transaccion_apple(
        transactionId="2000000999", originalTransactionId="2000000111"))

    with p1, p2:
        client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000999"},
                    headers=auth(tokens))

    compra = PurchaseRepository.find_by_reference("apple", "2000000999")
    assert compra.original_transaction_id == "2000000111"
    assert compra.store_environment == "Production"


def test_apple_no_concede_nada_si_no_conoce_la_transaccion(client, tiendas):
    tokens = registrar(client, "apple-404@example.com")
    p1, p2 = _apple_responde(status=404)

    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple", "externalId": "inventado"},
                        headers=auth(tokens))

    assert r.status_code == 402
    assert UserRepository.find_by_id(
        tokens["user"]["id"]).has_full_access is False


@pytest.mark.parametrize("cambio,motivo", [
    ({"revocationDate": 1759100000000, "revocationReason": 1}, "reembolsada"),
    ({"bundleId": "com.otra.app"}, "de otra app"),
    ({"productId": "com.aztecapp.explorer.otracosa"}, "de otro producto"),
    ({"type": "Auto-Renewable Subscription"}, "no es un no consumible"),
    ({"environment": "Sandbox"}, "de sandbox en un servidor de producción"),
])
def test_apple_rechaza_las_compras_que_no_valen(client, tiendas, cambio, motivo):
    tokens = registrar(client, f"apple-{abs(hash(motivo))}@example.com")
    p1, p2 = _apple_responde(transaccion_apple(**cambio))

    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(tokens))

    assert r.status_code == 402, f"debería rechazar una compra {motivo}"
    estado = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert estado["hasFullAccess"] is False


def test_apple_acepta_sandbox_cuando_se_permite(client, tiendas, app):
    """Durante la revisión de Apple hace falta: el revisor compra en sandbox."""
    app.config["APPLE_ALLOW_SANDBOX"] = True
    tokens = registrar(client, "apple-sandbox@example.com")
    p1, p2 = _apple_responde(transaccion_apple(environment="Sandbox"))

    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(tokens))

    assert r.status_code == 200


def test_apple_sin_credenciales_no_concede_nada(client, app):
    """Un servidor sin configurar niega el acceso; no lo regala."""
    app.config.update(PAYMENTS_ALLOW_UNVERIFIED=False, APPLE_BUNDLE_ID="",
                      APPLE_ISSUER_ID="", APPLE_KEY_ID="", APPLE_PRODUCT_ID="",
                      APPLE_PRIVATE_KEY="", APPLE_PRIVATE_KEY_PATH="")
    tokens = registrar(client, "apple-nc@example.com")

    r = client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000123456789"},
                    headers=auth(tokens))

    assert r.status_code == 402
    assert "no está configurado" in r.get_json()["details"]


# --------------------------------------------------------------------------
# Google
# --------------------------------------------------------------------------

def _google_responde(compra=None, status=200, acuse=RespuestaFalsa(204)):
    return (
        patch.object(google_play, "_token_acceso", return_value="token-falso"),
        patch.object(google_play.requests, "get",
                     return_value=RespuestaFalsa(status, compra or {})),
        patch.object(google_play.requests, "post", return_value=acuse),
    )


def test_google_concede_el_acceso_y_acusa_recibo(client, tiendas):
    """El acuse no es opcional: sin él Google reembolsa a los 3 días."""
    tokens = registrar(client, "google-ok@example.com")
    p1, p2, p3 = _google_responde(compra_google())

    with p1, p2, p3 as post:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    assert r.status_code == 200, r.get_json()
    assert post.called, "no se acusó recibo a Google"
    assert ":acknowledge" in post.call_args[0][0]

    compra = PurchaseRepository.find_by_reference("google", TOKEN_GOOGLE)
    assert compra.acknowledged_at is not None


def test_google_guarda_un_purchase_token_entero(client, tiendas):
    """El token pasa de 255 caracteres: con la columna vieja esto reventaba."""
    assert len(TOKEN_GOOGLE) > 255

    tokens = registrar(client, "google-largo@example.com")
    p1, p2, p3 = _google_responde(compra_google())

    with p1, p2, p3:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    assert r.status_code == 200, r.get_json()
    compra = PurchaseRepository.find_by_reference("google", TOKEN_GOOGLE)
    assert compra is not None
    assert compra.external_id == TOKEN_GOOGLE


def test_google_no_marca_como_acusada_una_compra_cuyo_acuse_fallo(client, tiendas):
    """Si el acuse falla, la fila queda sin marcar para que el barrido la recoja."""
    tokens = registrar(client, "google-acuse@example.com")
    p1, p2, p3 = _google_responde(
        compra_google(), acuse=RespuestaFalsa(503, texto="Service Unavailable"))

    with p1, p2, p3:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    # El usuario pagó: el acceso se le da igual.
    assert r.status_code == 200
    compra = PurchaseRepository.find_by_reference("google", TOKEN_GOOGLE)
    assert compra.acknowledged_at is None

    # Y el barrido la encuentra.
    assert compra.id in [c.id for c in PurchaseRepository.find_sin_acuse("google")]


def test_el_barrido_reintenta_el_acuse_pendiente(client, tiendas):
    tokens = registrar(client, "google-barrido@example.com")
    p1, p2, p3 = _google_responde(compra_google(), acuse=RespuestaFalsa(503))
    with p1, p2, p3:
        client.post("/api/payments/confirm",
                    json={"provider": "google", "externalId": TOKEN_GOOGLE},
                    headers=auth(tokens))

    p1, p2, p3 = _google_responde(compra_google(), acuse=RespuestaFalsa(204))
    with p1, p2, p3:
        resultado = PurchaseService.acusar_pendientes()

    assert resultado == {"revisadas": 1, "acusadas": 1}
    assert PurchaseRepository.find_by_reference(
        "google", TOKEN_GOOGLE).acknowledged_at is not None


def test_google_no_acusa_una_compra_que_ya_venia_acusada(client, tiendas):
    tokens = registrar(client, "google-ya@example.com")
    p1, p2, p3 = _google_responde(compra_google(acknowledgementState=1))

    with p1, p2, p3 as post:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    assert r.status_code == 200
    assert not post.called


@pytest.mark.parametrize("estado,motivo", [
    (1, "cancelada o reembolsada"),
    (2, "pendiente de pago"),
])
def test_google_rechaza_las_compras_que_no_estan_pagadas(
        client, tiendas, estado, motivo):
    tokens = registrar(client, f"google-{estado}@example.com")
    p1, p2, p3 = _google_responde(compra_google(purchaseState=estado))

    with p1, p2, p3:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    assert r.status_code == 402, f"debería rechazar una compra {motivo}"
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is False


def test_google_rechaza_una_compra_que_la_tienda_no_conoce(client, tiendas):
    tokens = registrar(client, "google-404@example.com")
    p1, p2, p3 = _google_responde(status=404)

    with p1, p2, p3:
        r = client.post("/api/payments/confirm",
                        json={"provider": "google", "externalId": TOKEN_GOOGLE},
                        headers=auth(tokens))

    assert r.status_code == 402


# --------------------------------------------------------------------------
# Un recibo, una cuenta
# --------------------------------------------------------------------------

def test_un_recibo_no_desbloquea_una_segunda_cuenta(client, tiendas):
    """Un recibo válido circulando por un foro no puede abrir cuentas sin fin."""
    primera = registrar(client, "duenio@example.com")
    segunda = registrar(client, "colado@example.com")

    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        assert client.post("/api/payments/confirm",
                           json={"provider": "apple",
                                 "externalId": "2000000123456789"},
                           headers=auth(primera)).status_code == 200

    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(segunda))

    assert r.status_code == 409
    acceso = client.get("/api/payments/access",
                        headers=auth(segunda)).get_json()["data"]
    assert acceso["hasFullAccess"] is False


def test_la_tienda_manda_sobre_de_quien_es_la_compra(client, tiendas):
    """Si la tienda dice a qué cuenta pertenece, no vale presentarla en otra.

    La app manda el id de usuario al iniciar la compra y la tienda lo devuelve
    intacto: es la comprobación que no se puede falsificar desde el cliente.
    """
    tokens = registrar(client, "titular@example.com")
    p1, p2 = _apple_responde(transaccion_apple(
        appAccountToken="00000000-0000-0000-0000-000000000000"))

    with p1, p2:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(tokens))

    assert r.status_code == 409


def test_el_mismo_recibo_dos_veces_no_duplica_la_compra(client, tiendas):
    tokens = registrar(client, "repetido@example.com")

    for _ in range(2):
        p1, p2 = _apple_responde(transaccion_apple())
        with p1, p2:
            r = client.post("/api/payments/confirm",
                            json={"provider": "apple",
                                  "externalId": "2000000123456789"},
                            headers=auth(tokens))
            assert r.status_code == 200

    compras = client.get("/api/payments/purchases",
                         headers=auth(tokens)).get_json()["data"]["purchases"]
    assert len(compras) == 1


# --------------------------------------------------------------------------
# Restaurar compras
# --------------------------------------------------------------------------

def test_restaurar_con_recibo_devuelve_el_acceso(client, tiendas):
    tokens = registrar(client, "restaura@example.com")
    p1, p2 = _apple_responde(transaccion_apple())

    with p1, p2:
        r = client.post("/api/payments/restore",
                        json={"provider": "apple",
                              "externalId": "2000000123456789"},
                        headers=auth(tokens))

    assert r.status_code == 200, r.get_json()
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is True


def test_restaurar_sin_recibo_devuelve_lo_que_ya_conste(client, tiendas):
    tokens = registrar(client, "restaura2@example.com")
    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000123456789"},
                    headers=auth(tokens))

    r = client.post("/api/payments/restore", headers=auth(tokens))

    assert r.status_code == 200
    assert r.get_json()["data"]["status"] == "completed"


def test_restaurar_sin_haber_comprado_es_404(client, tiendas):
    """404 y no 402: no es un cobro que falla, es una cuenta que nunca compró.

    La app necesita distinguirlos para enseñar el mensaje correcto.
    """
    tokens = registrar(client, "nunca@example.com")

    r = client.post("/api/payments/restore", headers=auth(tokens))

    assert r.status_code == 404


def test_restaurar_exige_token(client, tiendas):
    assert client.post("/api/payments/restore").status_code == 401


# --------------------------------------------------------------------------
# Webhooks
# --------------------------------------------------------------------------

def aviso_apple(tipo, transaccion):
    return {"signedPayload": jws_de({
        "notificationType": tipo,
        "data": {"signedTransactionInfo": jws_de(transaccion)},
    })}


def aviso_google(cuerpo):
    return {"message": {"data": base64.b64encode(
        json.dumps(cuerpo).encode()).decode()}}


def test_un_reembolso_de_apple_retira_el_acceso(client, tiendas):
    tokens = registrar(client, "apple-reembolso@example.com")
    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000123456789"},
                    headers=auth(tokens))

    # Apple avisa, y al ir a preguntar la transacción aparece revocada.
    revocada = transaccion_apple(revocationDate=1759100000000, revocationReason=1)
    p1, p2 = _apple_responde(revocada)
    with p1, p2:
        r = client.post("/api/payments/webhooks/apple",
                        json=aviso_apple("REFUND", revocada))

    assert r.status_code == 200
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is False


def test_un_aviso_falso_no_retira_nada(client, tiendas):
    """Este endpoint es público. Que lo llame cualquiera no puede costarle el
    acceso a quien pagó: lo que decide es lo que conteste la tienda, no el aviso.
    """
    tokens = registrar(client, "apple-falso@example.com")
    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000123456789"},
                    headers=auth(tokens))

    # El aviso MIENTE: dice que hubo reembolso. Apple dice que no.
    mentira = transaccion_apple(revocationDate=1759100000000)
    p1, p2 = _apple_responde(transaccion_apple())      # la verdad: sigue viva
    with p1, p2:
        r = client.post("/api/payments/webhooks/apple",
                        json=aviso_apple("REFUND", mentira))

    assert r.status_code == 200
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is True


def test_una_compra_anulada_en_google_retira_el_acceso(client, tiendas):
    tokens = registrar(client, "google-anulada@example.com")
    p1, p2, p3 = _google_responde(compra_google())
    with p1, p2, p3:
        client.post("/api/payments/confirm",
                    json={"provider": "google", "externalId": TOKEN_GOOGLE},
                    headers=auth(tokens))

    p1, p2, p3 = _google_responde(compra_google(purchaseState=1))
    with p1, p2, p3:
        r = client.post("/api/payments/webhooks/google",
                        json=aviso_google({"voidedPurchaseNotification": {
                            "purchaseToken": TOKEN_GOOGLE,
                            "orderId": "GPA.1234-5678-9012-34567",
                        }}))

    assert r.status_code == 200
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is False


def test_un_aviso_de_una_compra_desconocida_no_hace_nada(client, tiendas):
    r = client.post("/api/payments/webhooks/apple",
                    json=aviso_apple("REFUND", transaccion_apple()))
    assert r.status_code == 200


def test_los_webhooks_aguantan_un_cuerpo_cualquiera(client, tiendas):
    """Devuelven 200 sin reventar: un 500 haría que la tienda reintentara en bucle."""
    for ruta in ("apple", "google"):
        for cuerpo in ({}, {"vaya": "cosa"}, {"signedPayload": "no-es-un-jws"}):
            r = client.post(f"/api/payments/webhooks/{ruta}", json=cuerpo)
            assert r.status_code == 200, (ruta, cuerpo)


def test_la_notificacion_de_prueba_de_google_se_contesta(client, tiendas):
    """Play Console manda una al configurar el tema y comprueba que hay 200."""
    r = client.post("/api/payments/webhooks/google",
                    json=aviso_google({"testNotification": {"version": "1.0"}}))
    assert r.status_code == 200


def test_el_secreto_de_webhook_se_comprueba_cuando_se_configura(client, tiendas, app):
    app.config["STORE_WEBHOOK_SECRET"] = "un-secreto"
    tokens = registrar(client, "secreto@example.com")
    p1, p2 = _apple_responde(transaccion_apple())
    with p1, p2:
        client.post("/api/payments/confirm",
                    json={"provider": "apple", "externalId": "2000000123456789"},
                    headers=auth(tokens))

    revocada = transaccion_apple(revocationDate=1759100000000)
    p1, p2 = _apple_responde(revocada)
    with p1, p2:
        r = client.post("/api/payments/webhooks/apple?token=el-que-no-es",
                        json=aviso_apple("REFUND", revocada))

    assert r.status_code == 200          # 200 para que no lo reintenten
    acceso = client.get("/api/payments/access",
                        headers=auth(tokens)).get_json()["data"]
    assert acceso["hasFullAccess"] is True, "un aviso sin el secreto no debe tocar nada"


# --------------------------------------------------------------------------
# La puerta de desarrollo
# --------------------------------------------------------------------------

def test_stripe_ya_no_es_un_camino_de_cobro(client, tiendas):
    """Cobrar contenido digital por fuera de la tienda es motivo de rechazo."""
    tokens = registrar(client, "stripe@example.com")

    r = client.post("/api/payments/confirm",
                    json={"provider": "stripe", "externalId": "pi_123"},
                    headers=auth(tokens))

    assert r.status_code == 402
    assert "tiendas" in r.get_json()["details"]


def test_las_altas_manuales_no_se_conceden_por_la_api(client, tiendas):
    tokens = registrar(client, "manual@example.com")

    r = client.post("/api/payments/confirm",
                    json={"provider": "manual", "externalId": "cortesia"},
                    headers=auth(tokens))

    assert r.status_code == 402
    assert "consola" in r.get_json()["details"]


def test_la_puerta_de_desarrollo_no_llama_a_ninguna_tienda(client, app):
    """Con PAYMENTS_ALLOW_UNVERIFIED encendido no se pregunta a nadie.

    Es lo que permite probar la app desbloqueada sin cuentas de prueba en las
    dos tiendas, y por eso mismo va apagado fuera de una máquina de desarrollo.
    """
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "dev@example.com")

    with patch.object(apple.requests, "get") as apple_get, \
            patch.object(google_play.requests, "get") as google_get:
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple", "externalId": "lo-que-sea"},
                        headers=auth(tokens))

    assert r.status_code == 200
    assert not apple_get.called
    assert not google_get.called
