"""Payments models"""
from app.extensions import db
from datetime import datetime


class Payment(db.Model):
    """Payment model for tour and content purchases"""
    
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)  # USD
    currency = db.Column(db.String(3), default="USD")
    status = db.Column(db.String(50), nullable=False)  # pending, completed, failed, refunded
    
    # Item purchased
    item_type = db.Column(db.String(50), nullable=False)  # tour, subscription, content
    item_id = db.Column(db.String(36))
    
    # Payment method
    payment_method = db.Column(db.String(50))  # stripe, apple_pay, google_pay
    transaction_id = db.Column(db.String(255))  # Stripe or provider transaction ID
    
    # Stripe info
    stripe_payment_intent_id = db.Column(db.String(255))
    
    # Refund info
    refund_amount = db.Column(db.Float, default=0)
    refund_reason = db.Column(db.Text)
    refunded_at = db.Column(db.DateTime)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "userId": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "itemType": self.item_type,
            "itemId": self.item_id,
            "transactionId": self.transaction_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Subscription(db.Model):
    """Subscription model for recurring payments"""
    
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Tier
    tier = db.Column(db.String(50), nullable=False)  # premium, vip
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Pricing
    monthly_price = db.Column(db.Float, nullable=False)
    
    # Dates
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_start = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime, nullable=False)
    cancelled_at = db.Column(db.DateTime)
    
    # Stripe
    stripe_subscription_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
