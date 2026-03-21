"""
Account API endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.models import Account
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountList,
)
from app.services.balance_inference import get_calculated_balance

router = APIRouter(tags=["accounts"])


def _enrich_account(db: Session, account: Account) -> AccountResponse:
    """Build AccountResponse with calculated_balance and is_stale."""
    calc_bal, is_stale = get_calculated_balance(db, account)
    return AccountResponse(
        id=str(account.id),
        name=account.name,
        account_type=account.account_type,
        learned_format_id=account.learned_format_id,
        is_active=account.is_active,
        created_at=account.created_at,
        current_balance=account.current_balance,
        balance_updated_at=account.balance_updated_at,
        calculated_balance=calc_bal,
        is_stale=is_stale,
    )


@router.get("", response_model=AccountList)
def list_accounts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all accounts."""
    accounts = db.query(Account).filter(Account.is_active == True).offset(skip).limit(limit).all()
    total = db.query(Account).filter(Account.is_active == True).count()

    return AccountList(
        items=[_enrich_account(db, a) for a in accounts],
        total=total
    )


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db)
):
    """Create a new account."""
    db_account = Account(
        name=account.name,
        account_type=account.account_type,
        current_balance=account.starting_balance if account.starting_balance is not None else 0,
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return _enrich_account(db, db_account)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return _enrich_account(db, account)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    account_update: AccountUpdate,
    db: Session = Depends(get_db)
):
    """Update an account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Update fields if provided
    if account_update.name is not None:
        account.name = account_update.name
    if account_update.account_type is not None:
        account.account_type = account_update.account_type
    if account_update.is_active is not None:
        account.is_active = account_update.is_active
    if account_update.current_balance is not None:
        account.current_balance = account_update.current_balance
        account.balance_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)
    return _enrich_account(db, account)


@router.delete("/{account_id}", status_code=204)
def delete_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Soft delete an account (set is_active to False)."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Soft delete
    account.is_active = False
    db.commit()
    return None


@router.post("/{account_id}/balance", response_model=AccountResponse)
def update_account_balance(
    account_id: str,
    current_balance: float,
    balance_date: datetime = None,
    db: Session = Depends(get_db)
):
    """
    Update account balance explicitly.

    Sets the current balance and timestamp.
    """
    from app.services.networth_service import record_balance_snapshot, NetWorthError

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        account.current_balance = current_balance
        account.balance_updated_at = datetime.utcnow()

        record_balance_snapshot(db, account_id, current_balance, balance_date or datetime.utcnow().date())

        db.commit()
        db.refresh(account)

        return _enrich_account(db, account)
    except NetWorthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
