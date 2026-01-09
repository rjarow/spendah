"""Service for alert detection and management."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from app.models.alert import Alert, AlertType, Severity, AlertSettings
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup
from app.models.category import Category
from app.ai.client import get_ai_client
from app.ai.prompts import ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER


def get_or_create_settings(db: Session) -> AlertSettings:
    """Get alert settings, creating default if none exist."""
    settings = db.query(AlertSettings).first()
    if not settings:
        settings = AlertSettings(
            id=str(uuid.uuid4()),
            large_purchase_multiplier=Decimal("3.0"),
            unusual_merchant_threshold=Decimal("200.0"),
            alerts_enabled=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_category_average(db: Session, category_id: str, months: int = 3) -> float:
    """Get average spending for a category over the last N months."""
    cutoff = datetime.now() - timedelta(days=months * 30)

    result = db.query(func.avg(func.abs(Transaction.amount))).filter(
        Transaction.category_id == category_id,
        Transaction.amount < 0,
        Transaction.date >= cutoff.date()
    ).scalar()

    return float(result) if result else 0.0


def is_first_time_merchant(db: Session, merchant: str, exclude_txn_id: str = None) -> bool:
    """Check if this is the first transaction from this merchant."""
    query = db.query(Transaction).filter(
        Transaction.clean_merchant == merchant
    )
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)

    return query.count() == 0


def get_recurring_for_merchant(db: Session, merchant: str) -> Optional[RecurringGroup]:
    """Find recurring group matching this merchant."""
    # Simple pattern match - could be improved with fuzzy matching
    return db.query(RecurringGroup).filter(
        RecurringGroup.merchant_pattern.ilike(f"%{merchant}%"),
        RecurringGroup.is_active == True
    ).first()


def check_price_increase(
    db: Session,
    merchant: str,
    new_amount: float,
    recurring_group: Optional[RecurringGroup]
) -> Optional[Dict[str, Any]]:
    """Check if this transaction represents a price increase from a recurring charge."""
    if not recurring_group:
        return None

    if recurring_group.expected_amount:
        old_amount = float(recurring_group.expected_amount)
        if new_amount > old_amount * 1.05:  # 5% threshold for price increase
            return {
                "previous_amount": old_amount,
                "new_amount": new_amount,
                "increase": new_amount - old_amount,
                "percent_increase": ((new_amount - old_amount) / old_amount) * 100
            }

    return None


def analyze_transaction_for_alerts(
    db: Session,
    transaction: Transaction
) -> Optional[Alert]:
    """
    Analyze a transaction for anomalies and create an alert if needed.
    Uses AI for complex analysis, rule-based for simple checks.
    """
    settings = get_or_create_settings(db)

    if not settings.alerts_enabled:
        return None

    amount = abs(float(transaction.amount))
    merchant = transaction.clean_merchant or transaction.raw_description

    # Get context
    category_avg = get_category_average(db, transaction.category_id) if transaction.category_id else 0
    is_new_merchant = is_first_time_merchant(db, merchant, transaction.id)
    recurring = get_recurring_for_merchant(db, merchant)
    price_increase = check_price_increase(db, merchant, amount, recurring)

    # Rule-based checks first (faster, no AI needed)

    # Check 1: Price increase on recurring
    if price_increase:
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.price_increase,
            severity=Severity.warning,
            title=f"Price increase: {merchant}",
            description=f"Was ${price_increase['previous_amount']:.2f}/mo → Now ${price_increase['new_amount']:.2f}/mo (+${price_increase['increase']:.2f})",
            transaction_id=str(transaction.id),
            recurring_group_id=str(recurring.id) if recurring else None,
            metadata={
                "previous_amount": price_increase['previous_amount'],
                "new_amount": price_increase['new_amount'],
                "increase": price_increase['increase'],
                "percent_increase": price_increase['percent_increase']
            }
        )
        db.add(alert)
        db.commit()
        return alert

    # Check 2: Large purchase (rule-based)
    multiplier = float(settings.large_purchase_multiplier)
    if category_avg > 0 and amount > category_avg * multiplier:
        actual_multiplier = amount / category_avg
        severity = Severity.attention if actual_multiplier > 5 else Severity.warning

        # Get category name
        category = db.query(Category).filter(Category.id == transaction.category_id).first()
        category_name = category.name if category else "this category"

        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=severity,
            title=f"Large purchase: {merchant}",
            description=f"${amount:.2f} is {actual_multiplier:.1f}x your usual {category_name} spending of ${category_avg:.2f}",
            transaction_id=str(transaction.id),
            metadata={
                "amount": amount,
                "category_avg": category_avg,
                "multiplier": actual_multiplier
            }
        )
        db.add(alert)
        db.commit()
        return alert

    # Check 3: Unusual merchant (first time, high amount)
    unusual_threshold = float(settings.unusual_merchant_threshold)
    if is_new_merchant and amount > unusual_threshold:
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.unusual_merchant,
            severity=Severity.info,
            title=f"New merchant: {merchant}",
            description=f"First purchase at {merchant}: ${amount:.2f}",
            transaction_id=str(transaction.id),
            metadata={
                "amount": amount,
                "threshold": unusual_threshold,
                "is_first_time": True
            }
        )
        db.add(alert)
        db.commit()
        return alert

    return None


def get_alerts(
    db: Session,
    is_read: Optional[bool] = None,
    is_dismissed: Optional[bool] = None,
    alert_type: Optional[str] = None,
    limit: int = 50
) -> List[Alert]:
    """Get alerts with optional filters."""
    query = db.query(Alert)

    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)

    if is_dismissed is not None:
        query = query.filter(Alert.is_dismissed == is_dismissed)
    else:
        # Default: hide dismissed
        query = query.filter(Alert.is_dismissed == False)

    if alert_type:
        query = query.filter(Alert.type == alert_type)

    return query.order_by(Alert.created_at.desc()).limit(limit).all()


def get_unread_count(db: Session) -> int:
    """Get count of unread, non-dismissed alerts."""
    return db.query(Alert).filter(
        Alert.is_read == False,
        Alert.is_dismissed == False
    ).count()


def mark_all_read(db: Session) -> int:
    """Mark all alerts as read. Returns count updated."""
    result = db.query(Alert).filter(
        Alert.is_read == False
    ).update({Alert.is_read: True})
    db.commit()
    return result


def create_new_recurring_alert(db: Session, recurring_group: RecurringGroup) -> Alert:
    """Create an alert for a newly detected recurring charge."""
    alert = Alert(
        id=str(uuid.uuid4()),
        type=AlertType.new_recurring,
        severity=Severity.info,
        title=f"New subscription: {recurring_group.name}",
        description=f"Detected new recurring charge: ${recurring_group.expected_amount:.2f}/{recurring_group.frequency.value}",
        recurring_group_id=str(recurring_group.id),
        metadata={
            "amount": float(recurring_group.expected_amount) if recurring_group.expected_amount else None,
            "frequency": recurring_group.frequency.value
        }
    )
    db.add(alert)
    db.commit()
    return alert
