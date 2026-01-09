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
from app.ai.prompts import (
    ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER,
    SUBSCRIPTION_REVIEW_SYSTEM, SUBSCRIPTION_REVIEW_USER,
    ANNUAL_CHARGE_DETECTION_SYSTEM, ANNUAL_CHARGE_DETECTION_USER
)
from app.models.recurring import Frequency
import json
from datetime import date


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


async def run_subscription_review(db: Session) -> Dict[str, Any]:
    """
    Run an AI-powered subscription review.
    Creates a subscription_review alert and returns insights.
    """
    settings = get_or_create_settings(db)

    # Get active recurring charges
    recurring = db.query(RecurringGroup).filter(
        RecurringGroup.is_active == True
    ).all()

    if not recurring:
        return {
            "total_monthly_cost": 0,
            "total_yearly_cost": 0,
            "subscription_count": 0,
            "insights": [],
            "summary": "No active subscriptions found."
        }

    # Calculate costs
    total_monthly = 0
    for r in recurring:
        if r.expected_amount:
            amount = float(r.expected_amount)
            if r.frequency == Frequency.weekly:
                total_monthly += amount * 4.33
            elif r.frequency == Frequency.biweekly:
                total_monthly += amount * 2.17
            elif r.frequency == Frequency.monthly:
                total_monthly += amount
            elif r.frequency == Frequency.quarterly:
                total_monthly += amount / 3
            elif r.frequency == Frequency.yearly:
                total_monthly += amount / 12

    total_yearly = total_monthly * 12

    # Prepare data for AI
    recurring_json = json.dumps([
        {
            "id": str(r.id),
            "name": r.name,
            "merchant_pattern": r.merchant_pattern,
            "amount": float(r.expected_amount) if r.expected_amount else 0,
            "frequency": r.frequency.value,
            "last_seen": r.last_seen_date.isoformat() if r.last_seen_date else None,
            "next_expected": r.next_expected_date.isoformat() if r.next_expected_date else None,
        }
        for r in recurring
    ], indent=2)

    # Get transaction activity (simplified - count per merchant)
    cutoff = datetime.now() - timedelta(days=90)

    activity = {}
    for r in recurring:
        count = db.query(Transaction).filter(
            Transaction.recurring_group_id == r.id,
            Transaction.date >= cutoff.date()
        ).count()
        activity[r.name] = count

    activity_json = json.dumps(activity, indent=2)

    # Get last review date
    last_review = db.query(Alert).filter(
        Alert.type == AlertType.subscription_review
    ).order_by(Alert.created_at.desc()).first()

    last_review_date = last_review.created_at.isoformat() if last_review else "Never"

    # Call AI for review
    client = get_ai_client()
    user_prompt = SUBSCRIPTION_REVIEW_USER.format(
        recurring_json=recurring_json,
        activity_json=activity_json,
        last_review_date=last_review_date
    )

    try:
        result = await client.complete_json(
            system_prompt=SUBSCRIPTION_REVIEW_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2000
        )

        insights = result.get("insights", [])
        summary = result.get("summary", "Review complete.")

    except Exception as e:
        print(f"Subscription review AI failed: {e}")
        insights = []
        summary = "Unable to generate AI insights. Review your subscriptions manually."

    # Create review alert
    alert = Alert(
        id=str(uuid.uuid4()),
        type=AlertType.subscription_review,
        severity=Severity.info,
        title=f"Subscription Review: {len(recurring)} active subscriptions",
        description=f"Monthly: ${total_monthly:.2f} | Yearly: ${total_yearly:.2f}. {summary}",
        metadata={
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "subscription_count": len(recurring),
            "insights": insights
        }
    )
    db.add(alert)

    # Update last review timestamp in settings
    settings.last_subscription_review = datetime.now()
    settings.updated_at = datetime.now()

    db.commit()

    return {
        "total_monthly_cost": total_monthly,
        "total_yearly_cost": total_yearly,
        "subscription_count": len(recurring),
        "insights": insights,
        "summary": summary,
        "alert_id": str(alert.id)
    }


def get_upcoming_renewals(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get recurring charges expected in the next N days."""
    cutoff = date.today() + timedelta(days=days)

    recurring = db.query(RecurringGroup).filter(
        RecurringGroup.is_active == True,
        RecurringGroup.next_expected_date != None,
        RecurringGroup.next_expected_date <= cutoff
    ).order_by(RecurringGroup.next_expected_date).all()

    renewals = []
    total = 0

    for r in recurring:
        amount = float(r.expected_amount) if r.expected_amount else 0
        days_until = (r.next_expected_date - date.today()).days

        renewals.append({
            "recurring_group_id": str(r.id),
            "merchant": r.name,
            "amount": amount,
            "frequency": r.frequency.value,
            "next_date": r.next_expected_date.isoformat(),
            "days_until": days_until
        })
        total += amount

    return {
        "renewals": renewals,
        "total_upcoming_30_days": total
    }


async def detect_annual_charges(db: Session) -> List[Dict[str, Any]]:
    """
    Use AI to detect annual subscription patterns.
    Creates annual_charge alerts for upcoming renewals.
    """
    settings = get_or_create_settings(db)
    warning_days = settings.annual_charge_warning_days or 14

    # Get transactions from last 18 months
    cutoff = date.today() - timedelta(days=548)

    transactions = db.query(Transaction).filter(
        Transaction.date >= cutoff,
        Transaction.amount < 0,
        func.abs(Transaction.amount) > 20  # Skip small charges
    ).order_by(Transaction.date.desc()).all()

    if len(transactions) < 10:
        return []

    txn_json = json.dumps([
        {
            "id": str(t.id),
            "date": t.date.isoformat(),
            "amount": float(t.amount),
            "merchant": t.clean_merchant or t.raw_description,
        }
        for t in transactions
    ], indent=2)

    client = get_ai_client()
    user_prompt = ANNUAL_CHARGE_DETECTION_USER.format(
        transactions_json=txn_json,
        current_date=date.today().isoformat()
    )

    try:
        result = await client.complete_json(
            system_prompt=ANNUAL_CHARGE_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1500
        )

        annual_subs = result.get("annual_subscriptions", [])

    except Exception as e:
        print(f"Annual charge detection failed: {e}")
        return []

    # Create alerts for upcoming annual charges
    created_alerts = []
    for sub in annual_subs:
        if sub.get("confidence", 0) < 0.6:
            continue

        predicted_date = sub.get("predicted_next_date")
        if not predicted_date:
            continue

        try:
            next_date = datetime.strptime(predicted_date, "%Y-%m-%d").date()
        except:
            continue

        days_until = (next_date - date.today()).days

        # Only alert if within warning window
        if 0 < days_until <= warning_days:
            alert = Alert(
                id=str(uuid.uuid4()),
                type=AlertType.annual_charge,
                severity=Severity.info,
                title=f"Annual renewal: {sub['merchant']}",
                description=f"${sub['amount']:.2f} expected in {days_until} days (around {predicted_date})",
                metadata={
                    "merchant": sub["merchant"],
                    "amount": sub["amount"],
                    "predicted_date": predicted_date,
                    "days_until": days_until,
                    "confidence": sub.get("confidence", 0)
                }
            )
            db.add(alert)
            created_alerts.append(sub)

    if created_alerts:
        db.commit()

    return created_alerts
