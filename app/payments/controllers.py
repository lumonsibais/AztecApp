"""Payments controllers"""
from flask import request, jsonify
from app.payments.services import PaymentService, SubscriptionService
from app.middleware import token_required
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES, PREMIUM_TOUR_PRICE


class PaymentController:
    """Controller for payment endpoints"""
    
    @staticmethod
    @token_required
    def get_payment_history(current_user):
        """Get user's payment history"""
        try:
            payments = PaymentService.get_user_payments(current_user)
            return jsonify(
                format_response(success=True, data={"payments": payments})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def create_payment(current_user):
        """Create a payment intent"""
        try:
            data = request.get_json()
            
            item_type = data.get("itemType")  # tour, subscription, content
            item_id = data.get("itemId")
            
            # Determine amount based on item type
            if item_type == "tour":
                amount = PREMIUM_TOUR_PRICE
            elif item_type == "subscription":
                tier = data.get("tier", "premium")
                amount = 9.99 if tier == "premium" else 19.99
            else:
                amount = data.get("amount")
            
            payment = PaymentService.create_payment(
                current_user,
                amount,
                item_type,
                item_id
            )
            
            return jsonify(
                format_response(
                    success=True,
                    message="Payment created",
                    data={"paymentId": payment.id}
                )
            ), 201
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500


class SubscriptionController:
    """Controller for subscription endpoints"""
    
    @staticmethod
    @token_required
    def get_subscription(current_user):
        """Get user's current subscription"""
        try:
            subscription = SubscriptionService.get_user_subscription(current_user)
            
            if not subscription:
                return jsonify(
                    format_response(
                        success=True,
                        data={"subscription": None}
                    )
                ), 200
            
            return jsonify(
                format_response(
                    success=True,
                    data={
                        "subscription": {
                            "tier": subscription.tier,
                            "isActive": subscription.is_active,
                            "currentPeriodEnd": subscription.current_period_end.isoformat(),
                        }
                    }
                )
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def upgrade_subscription(current_user):
        """Upgrade subscription tier"""
        try:
            data = request.get_json()
            new_tier = data.get("tier")  # premium or vip
            
            if new_tier not in ["premium", "vip"]:
                return jsonify(
                    format_response(success=False, error="Invalid tier")
                ), 400
            
            subscription = SubscriptionService.upgrade_subscription(current_user, new_tier)
            
            if not subscription:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(success=True, message="Subscription upgraded")
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def cancel_subscription(current_user):
        """Cancel subscription"""
        try:
            subscription = SubscriptionService.cancel_subscription(current_user)
            
            if not subscription:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(success=True, message="Subscription cancelled")
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
