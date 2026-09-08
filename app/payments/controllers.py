"""Payments controllers"""
from flask import current_app, jsonify, request
from marshmallow import ValidationError

from app.middleware import token_required
from app.payments.providers import PaymentVerificationError
from app.payments.services import AlreadyPurchased, PurchaseService
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

        La verificación la hace `providers.verificar()`. Mientras no esté
        implementada la pasarela definitiva, esto responde 501 en lugar de
        conceder nada: aceptar un recibo sin comprobarlo sería regalar el
        contenido a cualquiera que mande una petición inventada.
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
        except PaymentVerificationError as err:
            current_app.logger.warning("Cobro no verificado: %s", err)
            return jsonify(
                format_response(
                    success=False,
                    error=ERROR_MESSAGES["PAYMENT_FAILED"],
                    details=str(err),
                )
            ), 501
        except Exception as e:
            return _server_error(e)
