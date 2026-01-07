"""
Alert database models.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text, JSON, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AlertType(str, enum.Enum):
    """Alert type enumeration."""
    large_purchase = "large_purchase"
    price_increase = "price_increase"
    new_recurring = "new_recurring"
    subscription_review = "subscription_review"
    unusual_merchant = "unusual_merchant"
    annual_charge = "annual_charge"


class Severity(str, enum.Enum):
    """Alert severity enumeration."""
    info = "info"
    warning = "warning"
    attention = "attention"


class Alert(Base):
    """Alert model for tracking insights and notifications."""

    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(Severity), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    recurring_group_id = Column(String(36), ForeignKey("recurring_groups.id"), nullable=True)
    alert_metadata = Column(JSON, nullable=True)  # Flexible data
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    action_taken = Column(String(100), nullable=True)  # "kept", "cancelled", "reviewed", etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")
    recurring_group = relationship("RecurringGroup", back_populates="alerts")


class AlertSettings(Base):
    """Alert settings model for configuring alert thresholds."""

    __tablename__ = "alert_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    large_purchase_threshold = Column(Numeric(12, 2), nullable=True)  # Dollar amount
    large_purchase_multiplier = Column(Numeric(5, 2), default=3.0, nullable=False)
    unusual_merchant_threshold = Column(Numeric(12, 2), default=200.0, nullable=False)
    subscription_review_days = Column(Integer, default=90, nullable=False)
    last_subscription_review = Column(DateTime, nullable=True)
    annual_charge_warning_days = Column(Integer, default=14, nullable=False)
    alerts_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
