"""
Transaction service layer.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.transaction import Transaction
from app.models.user_correction import UserCorrection

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction operations."""

    def __init__(self, db: Session):
        self.db = db

    def list_transactions(
        self,
        page: int = 1,
        per_page: int = 50,
        account_id: Optional[str] = None,
        category_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        is_recurring: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List transactions with filtering and pagination."""
        query = self.db.query(Transaction)

        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if is_recurring is not None:
            query = query.filter(Transaction.is_recurring == is_recurring)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Transaction.raw_description.ilike(search_term),
                    Transaction.clean_merchant.ilike(search_term),
                )
            )

        total = query.count()
        query = query.order_by(Transaction.date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        transactions = query.all()
        pages = (total + per_page - 1) // per_page

        return {"items": transactions, "total": total, "page": page, "pages": pages}

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a single transaction by ID."""
        return (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

    def update_transaction(
        self, transaction_id: str, update_data: Dict[str, Any]
    ) -> Optional[Transaction]:
        """
        Update a transaction and record user corrections for AI learning.

        Args:
            transaction_id: ID of the transaction to update
            update_data: Dictionary of fields to update

        Returns:
            Updated transaction or None if not found
        """
        transaction = (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

        if not transaction:
            return None

        category_id = update_data.get("category_id")
        clean_merchant = update_data.get("clean_merchant")

        if (
            category_id
            and transaction.ai_categorized
            and category_id != transaction.category_id
        ):
            self._record_category_correction(
                transaction.raw_description,
                clean_merchant or transaction.clean_merchant,
                category_id,
            )

        if clean_merchant and clean_merchant != transaction.clean_merchant:
            self._record_merchant_correction(
                transaction.raw_description,
                clean_merchant,
                category_id or transaction.category_id,
            )

        for field, value in update_data.items():
            if value is not None:
                setattr(transaction, field, value)

        if category_id:
            transaction.ai_categorized = False

        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def bulk_categorize(self, transaction_ids: List[str], category_id: str) -> int:
        """
        Bulk update category for multiple transactions.

        Args:
            transaction_ids: List of transaction IDs to update
            category_id: Category ID to assign

        Returns:
            Number of transactions updated
        """
        updated = (
            self.db.query(Transaction)
            .filter(Transaction.id.in_(transaction_ids))
            .update(
                {"category_id": category_id, "ai_categorized": False},
                synchronize_session=False,
            )
        )

        self.db.commit()
        return updated

    def _record_category_correction(
        self, raw_description: str, clean_merchant: Optional[str], category_id: str
    ):
        """Record a category correction for AI learning."""
        correction = UserCorrection(
            id=str(uuid.uuid4()),
            raw_description=raw_description,
            clean_merchant=clean_merchant,
            category_id=category_id,
        )
        self.db.add(correction)
        logger.debug(f"Recorded category correction for: {raw_description[:50]}")

    def _record_merchant_correction(
        self, raw_description: str, clean_merchant: str, category_id: Optional[str]
    ):
        """Record a merchant name correction for AI learning."""
        existing = (
            self.db.query(UserCorrection)
            .filter(UserCorrection.raw_description == raw_description)
            .first()
        )

        if existing:
            existing.clean_merchant = clean_merchant
            if category_id:
                existing.category_id = category_id
        else:
            correction = UserCorrection(
                id=str(uuid.uuid4()),
                raw_description=raw_description,
                clean_merchant=clean_merchant,
                category_id=category_id,
            )
            self.db.add(correction)

        logger.debug(f"Recorded merchant correction for: {raw_description[:50]}")
