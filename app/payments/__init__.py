"""Payments module initialization and routes"""
from flask import Blueprint

from app.payments.controllers import PurchaseController

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

# El producto vende un desbloqueo único: no hay rutas de suscripción, upgrade
# ni cancelación porque no hay nada que renovar ni que cancelar.
payments_bp.route("/access", methods=["GET"])(PurchaseController.get_access)
payments_bp.route("/purchases", methods=["GET"])(PurchaseController.get_history)
payments_bp.route("/checkout", methods=["POST"])(PurchaseController.checkout)
payments_bp.route("/confirm", methods=["POST"])(PurchaseController.confirm)
