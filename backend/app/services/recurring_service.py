"""Service for recurring transaction detection and management."""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import uuid

from app.models.recurring import RecurringGroup, Frequency
from app.models.transaction import Transaction
from app.ai.client import get_ai_client
from app.ai.prompts import RECURRING_DETECTION_SYSTEM, RECURRING_DETECTION_USER
from app.config import settings


async def detect_recurring_patterns(db: Session) -> List[Dict[str, Any]]:
    """
    Use AI to detect recurring patterns in transaction history.
    Returns list of detected patterns with transaction IDs.
    """
    # Get transactions from last 3 years for analysis (extended for testing with 2024 data)
    cutoff_date = date.today() - timedelta(days=365*3)

    transactions = db.query(Transaction).filter(
        Transaction.date >= cutoff_date,
        Transaction.amount < 0,  # Only expenses
        Transaction.recurring_group_id.is_(None)  # Not already marked as recurring
    ).order_by(Transaction.date.desc()).all()

    print(f"DEBUG: cutoff_date = {cutoff_date}")
    print(f"DEBUG: transactions matching criteria = {len(transactions)}")

    if len(transactions) < 5:
        print("DEBUG: Less than 5 transactions, returning empty")
        return []

    # Prepare transaction data for AI
    txn_data = [
        {
            "id": str(t.id),
            "date": t.date.isoformat(),
            "amount": float(t.amount),
            "merchant": t.clean_merchant or t.raw_description,
            "raw_description": t.raw_description,
        }
        for t in transactions
    ]

    # Call AI for detection
    client = get_ai_client()

    user_prompt = RECURRING_DETECTION_USER.format(
        transactions_json=json.dumps(txn_data, indent=2)
    )

    try:
        result = await client.complete_json(
            system_prompt=RECURRING_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2000
        )

        patterns = result.get("recurring_patterns", [])
        # Filter to confidence > 0.5
        return [p for p in patterns if p.get("confidence", 0) > 0.5]

    except Exception as e:
        print(f"Recurring detection failed: {e}")
        return []


def create_recurring_group_from_detection(
    db: Session,
    detection: Dict[str, Any]
) -> RecurringGroup:
    """
    Create a recurring group from a detection result and link transactions.
    """
    # Create the group
    group = RecurringGroup(
        id=str(uuid.uuid4()),
        name=detection["suggested_name"],
        merchant_pattern=detection["merchant_pattern"],
        expected_amount=Decimal(str(abs(detection["average_amount"]))),
        amount_variance=Decimal("15.0"),  # Default 15% variance
        frequency=Frequency(detection["frequency"]),
        is_active=True,
    )
    db.add(group)

    # Link transactions to this group
    transaction_ids = detection.get("transaction_ids", [])
    if transaction_ids:
        db.query(Transaction).filter(
            Transaction.id.in_(transaction_ids)
        ).update(
            {Transaction.recurring_group_id: group.id, Transaction.is_recurring: True},
            synchronize_session=False
        )

        # Set last_seen_date from most recent transaction
        most_recent = db.query(func.max(Transaction.date)).filter(
            Transaction.id.in_(transaction_ids)
        ).scalar()
        if most_recent:
            group.last_seen_date = most_recent
            group.next_expected_date = calculate_next_expected(most_recent, group.frequency)

    db.commit()
    db.refresh(group)
    return group


def calculate_next_expected(last_date: date, frequency: Frequency) -> date:
    """Calculate the next expected date based on frequency."""
    if frequency == Frequency.weekly:
        return last_date + timedelta(days=7)
    elif frequency == Frequency.biweekly:
        return last_date + timedelta(days=14)
    elif frequency == Frequency.monthly:
        # Add roughly one month
        if last_date.month == 12:
            return date(last_date.year + 1, 1, last_date.day)
        else:
            try:
                return date(last_date.year, last_date.month + 1, last_date.day)
            except ValueError:
                # Handle months with fewer days
                return date(last_date.year, last_date.month + 1, 28)
    elif frequency == Frequency.quarterly:
        # Add 3 months
        new_month = last_date.month + 3
        new_year = last_date.year
        if new_month > 12:
            new_month -= 12
            new_year += 1
        try:
            return date(new_year, new_month, last_date.day)
        except ValueError:
            return date(new_year, new_month, 28)
    elif frequency == Frequency.yearly:
        try:
            return date(last_date.year + 1, last_date.month, last_date.day)
        except ValueError:
            # Handle leap day (Feb 29) in non-leap years
            return date(last_date.year + 1, last_date.month, 28)
    else:
        return last_date + timedelta(days=30)


def get_recurring_groups(
    db: Session,
    include_inactive: bool = False
) -> List[RecurringGroup]:
    """Get all recurring groups with transaction counts."""
    query = db.query(RecurringGroup)

    if not include_inactive:
        query = query.filter(RecurringGroup.is_active == True)

    return query.order_by(RecurringGroup.name).all()


def get_group_transaction_count(db: Session, group_id: str) -> int:
    """Get count of transactions in a recurring group."""
    return db.query(Transaction).filter(
        Transaction.recurring_group_id == group_id
    ).count()


def mark_transaction_recurring(
    db: Session,
    transaction_id: str,
    recurring_group_id: Optional[str] = None,
    create_new: bool = False,
    new_name: Optional[str] = None,
    new_frequency: Optional[Frequency] = None
) -> RecurringGroup:
    """
    Mark a transaction as recurring, either linking to existing group or creating new.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    if recurring_group_id:
        # Link to existing group
        group = db.query(RecurringGroup).filter(RecurringGroup.id == recurring_group_id).first()
        if not group:
            raise ValueError(f"Recurring group {recurring_group_id} not found")
    elif create_new:
        # Create new group
        if not new_name:
            new_name = transaction.clean_merchant or transaction.raw_description
        if not new_frequency:
            new_frequency = Frequency.monthly

        group = RecurringGroup(
            id=str(uuid.uuid4()),
            name=new_name,
            merchant_pattern=transaction.clean_merchant or transaction.raw_description,
            expected_amount=abs(transaction.amount),
            amount_variance=Decimal("15.0"),
            frequency=new_frequency,
            is_active=True,
            last_seen_date=transaction.date,
            next_expected_date=calculate_next_expected(transaction.date, new_frequency),
        )
        db.add(group)
    else:
        raise ValueError("Must provide recurring_group_id or set create_new=True")

    # Link transaction
    transaction.recurring_group_id = group.id
    transaction.is_recurring = True

    # Update group's last_seen_date if this transaction is more recent
    if group.last_seen_date is None or transaction.date > group.last_seen_date:
        group.last_seen_date = transaction.date
        group.next_expected_date = calculate_next_expected(transaction.date, group.frequency)

    db.commit()
    db.refresh(group)
    return group


def unmark_transaction_recurring(db: Session, transaction_id: str) -> None:
    """Remove a transaction from its recurring group."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction:
        transaction.recurring_group_id = None
        transaction.is_recurring = False
        db.commit()
