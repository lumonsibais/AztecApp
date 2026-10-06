"""Payments module initialization and routes"""
from flask import Blueprint

from app.payments.controllers import PurchaseController
from app.payments.webhooks import WebhookController

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

# El producto vende un desbloqueo único: no hay rutas de suscripción, upgrade
# ni cancelación porque no hay nada que renovar ni que cancelar.
payments_bp.route("/access", methods=["GET"])(PurchaseController.get_access)
payments_bp.route("/purchases", methods=["GET"])(PurchaseController.get_history)
payments_bp.route("/checkout", methods=["POST"])(PurchaseController.checkout)
payments_bp.route("/confirm", methods=["POST"])(PurchaseController.confirm)

# "Restore Purchases". No es una comodidad: Apple rechaza en revisión toda app
# con producto no consumible que no ofrezca restaurar la compra.
payments_bp.route("/restore", methods=["POST"])(PurchaseController.restore)

# Avisos de las tiendas. Son las únicas rutas de la API sin autenticación, y no
# pueden tenerla: las llaman Apple y Pub/Sub, no la app. Lo que las hace seguras
# es que no se fían del cuerpo —ver app/payments/webhooks.py—.
payments_bp.route("/webhooks/apple", methods=["POST"],
                  endpoint="webhook_apple")(WebhookController.apple)
payments_bp.route("/webhooks/google", methods=["POST"],
                  endpoint="webhook_google")(WebhookController.google)
