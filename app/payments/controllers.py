"""Payments controllers"""
from flask import current_app, jsonify, request
from marshmallow import ValidationError

from app.middleware import token_required
from app.payments.providers import PaymentVerificationError
from app.payments.services import (
    AlreadyPurchased,
    NoHayCompra,
    PurchaseService,
    ReciboDeOtraCuenta,
)
from app.shared.constants import ERROR_MESSAGES
from app.shared.schemas import purchase_confirm_schema
from app.shared.utils import format_response


def _validation_error(err: ValidationError):
    return jsonify(
        format_response(
            success=False,
            error=ERROR_MESSAGES["VALIDATION_ERROR"],
            details=err.messages,
        )
    ), 400


def _cobro_no_verificado(err: Exception):
    """402: la tienda no confirma el cobro.

    Era 501 mientras no había ninguna pasarela implementada, y ahora sería
    mentira: el cobro está implementado y lo que pasa es que ESTE recibo no
    vale. El detalle va en la respuesta a propósito —"Google canceló esta
    compra" y "Apple no conoce esta transacción" mandan a sitios muy distintos
    a quien tenga que atender el caso—.
    """
    current_app.logger.warning("Cobro no verificado: %s", err)
    return jsonify(
        format_response(
            success=False,
            error=ERROR_MESSAGES["PAYMENT_FAILED"],
            details=str(err),
        )
    ), 402


def _recibo_ajeno(err: Exception):
    """409: el recibo ya está aplicado a otra cuenta.

    Antes esto devolvía un 200 diciendo "purchase already applied" sin conceder
    nada, que es la peor de las respuestas: quien lo intentaba veía un éxito y
    la app se quedaba bloqueada sin explicar por qué.
    """
    current_app.logger.warning("Recibo de otra cuenta: %s", err)
    return jsonify(
        format_response(success=False, error=str(err))
    ), 409


def _server_error(exc: Exception):
    current_app.logger.exception("Unhandled error in payments controller: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


class PurchaseController:
    """Compra del desbloqueo completo."""

    @staticmethod
    @token_required
    def get_access(current_user):
        """¿Tiene esta cuenta el contenido desbloqueado?

        Es lo que la app consulta al abrir para saber si pinta candados.
        """
        try:
            estado = PurchaseService.estado_de_acceso(current_user)
            if estado is None:
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"]
                    )
                ), 404

            return jsonify(format_response(success=True, data=estado)), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def get_history(current_user):
        """Historial de compras de la cuenta."""
        try:
            return jsonify(
                format_response(
                    success=True,
                    data={"purchases": PurchaseService.historial(current_user)},
                )
            ), 200
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def checkout(current_user):
        """Abre una compra pendiente."""
        try:
            compra = PurchaseService.iniciar(current_user)
            if compra is None:
                return jsonify(
                    format_response(
                        success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"]
                    )
                ), 404

            return jsonify(
                format_response(
                    success=True,
                    message="Purchase started",
                    data=compra.to_dict(),
                )
            ), 201

        except AlreadyPurchased:
            return jsonify(
                format_response(
                    success=False, error=ERROR_MESSAGES["ALREADY_PURCHASED"]
                )
            ), 409
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def confirm(current_user):
        """Confirma el cobro y concede el acceso.

        El recibo que manda la app se comprueba contra su tienda antes de
        conceder nada: `externalId` es el transactionId de StoreKit o el
        purchaseToken de Play Billing, y lo que decide es la respuesta de Apple
        o de Google, no la petición.

        402 cuando la tienda no confirma el cobro, 409 cuando el recibo ya está
        aplicado a otra cuenta.
        """
        try:
            datos = purchase_confirm_schema.load(request.get_json(silent=True) or {})

            compra, recien = PurchaseService.confirmar(
                current_user, datos["provider"], {"externalId": datos["external_id"]}
            )

            return jsonify(
                format_response(
                    success=True,
                    message="Access granted" if recien else "Purchase already applied",
                    data=compra.to_dict(),
                )
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except ReciboDeOtraCuenta as err:
            return _recibo_ajeno(err)
        except PaymentVerificationError as err:
            return _cobro_no_verificado(err)
        except Exception as e:
            return _server_error(e)

    @staticmethod
    @token_required
    def restore(current_user):
        """Restaura una compra anterior.

        Detrás de esto va el botón "Restore Purchases" que Apple exige en toda
        app con producto no consumible; sin él, la revisión rechaza la entrega.

        Admite dos formas de llamarla:

          con `provider` y `externalId`  el cliente le pidió a la tienda sus
              transacciones y manda la que encontró. Es el camino normal y se
              verifica igual que una compra nueva.

          sin cuerpo  no hay recibo que presentar y lo único que se puede hacer
              es devolver lo que ya conste a nombre de esta cuenta. Sirve para
              cuando la app reinstala y el usuario vuelve a entrar con su
              cuenta; 404 si nunca compró.
        """
        try:
            cuerpo = request.get_json(silent=True) or {}

            if cuerpo:
                datos = purchase_confirm_schema.load(cuerpo)
                proveedor = datos["provider"]
                payload = {"externalId": datos["external_id"]}
            else:
                proveedor, payload = "", {}

            compra, recien = PurchaseService.restaurar(
                current_user, proveedor, payload)

            return jsonify(
                format_response(
                    success=True,
                    message="Access restored" if recien else "Access already active",
                    data=compra.to_dict(),
                )
            ), 200

        except ValidationError as err:
            return _validation_error(err)
        except NoHayCompra:
            return jsonify(
                format_response(
                    success=False,
                    error="No purchase found to restore for this account",
                )
            ), 404
        except ReciboDeOtraCuenta as err:
            return _recibo_ajeno(err)
        except PaymentVerificationError as err:
            return _cobro_no_verificado(err)
        except Exception as e:
            return _server_error(e)
