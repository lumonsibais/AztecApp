"""Payments repository"""
from app.extensions import db
from app.payments.models import Payment, Subscription
from typing import Optional, List


class PaymentRepository:
    """Repository for Payment operations"""
    
    @staticmethod
    def find_by_id(payment_id: str) -> Optional[Payment]:
        """Find payment by ID"""
        return Payment.query.filter_by(id=payment_id).first()
    
    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Payment]:
        """Get payments by user"""
        return Payment.query.filter_by(user_id=user_id).limit(limit).all()
    
    @staticmethod
    def find_by_transaction_id(transaction_id: str) -> Optional[Payment]:
        """Find payment by transaction ID"""
        return Payment.query.filter_by(transaction_id=transaction_id).first()
    
    @staticmethod
    def save(payment: Payment) -> Payment:
        """Save a payment"""
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @staticmethod
    def update(payment_id: str, data: dict) -> Optional[Payment]:
        """Update a payment"""
        payment = PaymentRepository.find_by_id(payment_id)
        if not payment:
            return None
        
        for key, value in data.items():
            if hasattr(payment, key):
                setattr(payment, key, value)
        
        db.session.commit()
        return payment


class SubscriptionRepository:
    """Repository for Subscription operations"""
    
    @staticmethod
    def find_by_user_id(user_id: str) -> Optional[Subscription]:
        """Find subscription by user ID"""
        return Subscription.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def find_by_stripe_id(stripe_id: str) -> Optional[Subscription]:
        """Find subscription by Stripe ID"""
        return Subscription.query.filter_by(stripe_subscription_id=stripe_id).first()
    
    @staticmethod
    def save(subscription: Subscription) -> Subscription:
        """Save a subscription"""
        db.session.add(subscription)
        db.session.commit()
        return subscription
    
    @staticmethod
    def update(subscription_id: str, data: dict) -> Optional[Subscription]:
        """Update a subscription"""
        subscription = Subscription.query.filter_by(id=subscription_id).first()
        if not subscription:
            return None
        
        for key, value in data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        db.session.commit()
        return subscription
