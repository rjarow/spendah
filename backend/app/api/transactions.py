"""
Transaction API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import date
from pydantic import BaseModel
import uuid

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.user_correction import UserCorrection
from app.schemas.transaction import (
    TransactionResponse,
    TransactionUpdate,
    TransactionListResponse
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[str]
    category_id: str


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    is_recurring: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List transactions with filtering and pagination"""
    query = db.query(Transaction)

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
                Transaction.clean_merchant.ilike(search_term)
            )
        )

    total = query.count()

    query = query.order_by(Transaction.date.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    transactions = query.all()
    pages = (total + per_page - 1) // per_page

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        pages=pages
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Get a single transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction and record user corrections for AI learning"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if update.category_id and transaction.ai_categorized and update.category_id != transaction.category_id:
        correction = UserCorrection(
            id=str(uuid.uuid4()),
            raw_description=transaction.raw_description,
            clean_merchant=update.clean_merchant or transaction.clean_merchant,
            category_id=update.category_id
        )
        db.add(correction)

    if update.clean_merchant and update.clean_merchant != transaction.clean_merchant:
        existing = db.query(UserCorrection).filter(
            UserCorrection.raw_description == transaction.raw_description
        ).first()
        if existing:
            existing.clean_merchant = update.clean_merchant
        else:
            correction = UserCorrection(
                id=str(uuid.uuid4()),
                raw_description=transaction.raw_description,
                clean_merchant=update.clean_merchant,
                category_id=update.category_id or transaction.category_id
            )
            db.add(correction)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    if update.category_id:
        transaction.ai_categorized = False

    db.commit()
    db.refresh(transaction)

    return TransactionResponse.model_validate(transaction)


@router.post("/bulk-categorize")
def bulk_categorize(
    request: BulkCategorizeRequest,
    db: Session = Depends(get_db)
):
    """Bulk update category for multiple transactions"""
    updated = 0
    for txn_id in request.transaction_ids:
        transaction = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if transaction:
            transaction.category_id = request.category_id
            transaction.ai_categorized = False
            updated += 1

    db.commit()
    return {"updated": updated}
