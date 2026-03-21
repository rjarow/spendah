"""
Transaction API endpoints - refactored to use service layer.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionResponse,
    TransactionUpdate,
    TransactionListResponse,
)
from app.services.transaction_service import TransactionService

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
    db: Session = Depends(get_db),
):
    """List transactions with filtering and pagination"""
    service = TransactionService(db)
    result = service.list_transactions(
        page=page,
        per_page=per_page,
        account_id=account_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        is_recurring=is_recurring,
    )

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in result["items"]],
        total=result["total"],
        page=result["page"],
        pages=result["pages"],
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Get a single transaction"""
    service = TransactionService(db)
    transaction = service.get_transaction(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str, update: TransactionUpdate, db: Session = Depends(get_db)
):
    """Update a transaction and record user corrections for AI learning"""
    service = TransactionService(db)
    transaction = service.update_transaction(
        transaction_id, update.model_dump(exclude_unset=True)
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)


@router.post("/bulk-categorize")
def bulk_categorize(request: BulkCategorizeRequest, db: Session = Depends(get_db)):
    """Bulk update category for multiple transactions"""
    service = TransactionService(db)
    updated = service.bulk_categorize(request.transaction_ids, request.category_id)
    return {"updated": updated}
