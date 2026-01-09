"""
Account API endpoints.
"""

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

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
        items=accounts,
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
        type=account.type
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


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
    if account_update.type is not None:
        account.type = account_update.type
    if account_update.is_active is not None:
        account.is_active = account_update.is_active

    db.commit()
    db.refresh(account)
    return account


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
