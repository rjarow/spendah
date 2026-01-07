"""
Deduplication service for transactions.
"""

import hashlib
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def generate_transaction_hash(
    txn_date: date,
    amount: Decimal,
    raw_description: str,
    account_id: str
) -> str:
    """
    Generate SHA256 hash for deduplication.
    Uses date|amount|description|account_id
    """
    components = [
        txn_date.isoformat(),
        str(amount),
        raw_description.strip().lower(),
        str(account_id)
    ]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode()).hexdigest()


def is_duplicate(db: Session, txn_hash: str) -> bool:
    """Check if transaction with this hash already exists"""
    return db.query(Transaction).filter(Transaction.hash == txn_hash).first() is not None
