"""
Net worth API endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.schemas.account import AccountResponse
from app.services.networth_service import (
    get_current_networth,
    get_networth_breakdown,
    record_balance_snapshot,
    get_networth_history,
    auto_snapshot_all_balances,
    NetWorthError
)

router = APIRouter()


@router.get("/networth")
async def get_current_networth_summary(db: Session = Depends(get_db)):
    """
    Get current net worth summary.

    Returns total assets, total liabilities, and current net worth.
    """
    breakdown = get_networth_breakdown(db)
    return breakdown


@router.get("/networth/breakdown")
async def get_networth_breakdown_detail(db: Session = Depends(get_db)):
    """
    Get detailed net worth breakdown by account.

    Returns total assets, total liabilities, net worth, and list of accounts
    with their individual balances.
    """
    return get_networth_breakdown(db)


@router.get("/networth/history")
async def get_networth_history_endpoint(
    start_date: date = Query(..., description="Start date for history"),
    end_date: date = Query(default=date.today(), description="End date for history"),
    db: Session = Depends(get_db)
):
    """
    Get historical net worth data for charting.

    Uses balance snapshots from BalanceHistory table.
    """
    try:
        return get_networth_history(db, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/networth/auto-snapshot")
async def create_balance_snapshot(db: Session = Depends(get_db)):
    """
    Automatically record balance snapshots for all active accounts.

    Records current balances to BalanceHistory table for net worth history tracking.
    Use this endpoint to manually trigger a snapshot, or set up a background task/cron
    to run this periodically (daily or weekly) for tracking net worth over time.

    For periodic snapshots, consider:
    - Using a cron job to call this endpoint daily at a consistent time
    - Setting up a background task that runs on import completion
    - Triggering on manual balance updates

    Example cron entry (daily at 9am):
    0 9 * * * curl -X POST http://localhost:8000/api/v1/networth/auto-snapshot

    Returns:
        Dictionary with total snapshots created and error count
    """
    try:
        result = auto_snapshot_all_balances(db)
        return {
            "message": "Balance snapshots created",
            "total_snapshots": result["total_snapshots"],
            "errors": result["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/balance")
async def update_account_balance(
    account_id: str,
    current_balance: Decimal = Query(..., description="New balance for the account"),
    balance_date: date = Query(default=date.today(), description="Date to record balance"),
    db: Session = Depends(get_db)
):
    """
    Update account balance explicitly.

    This allows setting a balance on an account and recording a snapshot.
    """
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        account.current_balance = Decimal(str(current_balance))
        account.balance_updated_at = datetime.utcnow()

        snapshot = record_balance_snapshot(db, str(account_id), Decimal(str(current_balance)), balance_date)

        db.commit()
        db.refresh(account)

        return {
            "message": "Balance updated successfully",
            "account": AccountResponse.model_validate(account),
            "snapshot_created": True
        }

    except NetWorthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
