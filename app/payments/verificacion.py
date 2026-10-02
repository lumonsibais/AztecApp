"""Tipos comunes de la verificación de cobros.

Vive en su propio módulo para que `providers.py` pueda importar a `apple.py` y
`google_play.py` sin que estos tengan que importar a `providers.py` de vuelta.
"""
from dataclasses import dataclass


class PaymentVerificationError(Exception):
    """El cobro no se pudo verificar. Nunca se concede nada tras esto."""


@dataclass(frozen=True)
class ResultadoVerificacion:
    """Lo que la tienda confirma sobre una compra.

    `referencia` es lo único que el resto del backend necesita —se guarda en
    `purchases.external_id` y es lo que hace idempotente el cobro—. El resto
    son datos que solo tienen sentido aquí abajo y que se guardan para poder
    reconstruir qué pasó cuando algo salga mal:

      entorno              Sandbox o Production. Un recibo de sandbox no
                           desbloquea una instalación de producción.
      referencia_original  originalTransactionId de Apple. Es la referencia que
                           traen las notificaciones de reembolso, no la de la
                           transacción concreta.
      requiere_acuse       Google reembolsa automáticamente toda compra que no
                           se acuse en 3 días. Si esto viene en true y nadie
                           llama a `acusar_recibo`, el dinero se devuelve solo
                           y el usuario se queda con el acceso.
      cuenta_externa       obfuscatedExternalAccountId: el id de usuario que la
                           app mandó al iniciar la compra, si lo mandó.
    """

    provider: str
    referencia: str
    entorno: str = ""
    referencia_original: str = ""
    requiere_acuse: bool = False
    producto: str = ""
    cuenta_externa: str = ""


# Estados que puede tener una compra cuando se le vuelve a preguntar a la
# tienda. Es lo que devuelven los webhooks después de ir a confirmar la verdad.
ESTADO_ACTIVA = "activa"
ESTADO_REVOCADA = "revocada"
ESTADO_DESCONOCIDA = "desconocida"
