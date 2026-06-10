"""Payments service"""
from typing import Optional, Dict, Any
from app.payments.repositories import PaymentRepository, SubscriptionRepository
from app.payments.models import Payment, Subscription
from app.users.services import UserService
import uuid
from datetime import datetime, timedelta


class PaymentService:
    """Service for payment-related operations"""
    
    @staticmethod
    def create_payment(
        user_id: str,
        amount: float,
        item_type: str,
        item_id: str,
        stripe_payment_intent_id: str = None
    ) -> Payment:
        """Create a payment record"""
        payment = Payment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            item_type=item_type,
            item_id=item_id,
            status="pending",
            stripe_payment_intent_id=stripe_payment_intent_id,
        )
        
        return PaymentRepository.save(payment)
    
    @staticmethod
    def complete_payment(payment_id: str, transaction_id: str = None) -> Optional[Payment]:
        """Mark payment as completed"""
        data = {
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "transaction_id": transaction_id,
        }
        
        return PaymentRepository.update(payment_id, data)
    
    @staticmethod
    def fail_payment(payment_id: str, error: str = None) -> Optional[Payment]:
        """Mark payment as failed"""
        return PaymentRepository.update(
            payment_id,
            {"status": "failed"}
        )
    
    @staticmethod
    def refund_payment(payment_id: str, reason: str = None) -> Optional[Payment]:
        """Refund a payment"""
        payment = PaymentRepository.find_by_id(payment_id)
        if not payment:
            return None
        
        return PaymentRepository.update(
            payment_id,
            {
                "status": "refunded",
                "refund_amount": payment.amount,
                "refund_reason": reason,
                "refunded_at": datetime.utcnow(),
            }
        )
    
    @staticmethod
    def get_user_payments(user_id: str) -> list:
        """Get user's payment history"""
        payments = PaymentRepository.find_by_user(user_id)
        return [p.to_dict() for p in payments]


class SubscriptionService:
    """Service for subscription management"""
    
    @staticmethod
    def create_subscription(
        user_id: str,
        tier: str,
        monthly_price: float,
        stripe_subscription_id: str = None,
        stripe_customer_id: str = None
    ) -> Subscription:
        """Create a subscription"""
        current_period_end = datetime.utcnow() + timedelta(days=30)
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            monthly_price=monthly_price,
            current_period_end=current_period_end,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
        )
        
        return SubscriptionRepository.save(subscription)
    
    @staticmethod
    def upgrade_subscription(user_id: str, new_tier: str) -> Optional[Subscription]:
        """Upgrade user's subscription tier"""
        subscription = SubscriptionRepository.find_by_user_id(user_id)
        if not subscription:
            return None
        
        return SubscriptionRepository.update(
            subscription.id,
            {"tier": new_tier}
        )
    
    @staticmethod
    def cancel_subscription(user_id: str) -> Optional[Subscription]:
        """Cancel subscription"""
        subscription = SubscriptionRepository.find_by_user_id(user_id)
        if not subscription:
            return None
        
        return SubscriptionRepository.update(
            subscription.id,
            {
                "is_active": False,
                "cancelled_at": datetime.utcnow(),
            }
        )
    
    @staticmethod
    def get_user_subscription(user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        return SubscriptionRepository.find_by_user_id(user_id)
