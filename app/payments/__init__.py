"""Payments module initialization and routes"""
from flask import Blueprint
from app.payments.controllers import PaymentController, SubscriptionController

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

# Payment routes
payments_bp.route("/history", methods=["GET"])(PaymentController.get_payment_history)
payments_bp.route("/create", methods=["POST"])(PaymentController.create_payment)

# Subscription routes
payments_bp.route("/subscription", methods=["GET"])(SubscriptionController.get_subscription)
payments_bp.route("/subscription/upgrade", methods=["POST"])(SubscriptionController.upgrade_subscription)
payments_bp.route("/subscription/cancel", methods=["POST"])(SubscriptionController.cancel_subscription)
