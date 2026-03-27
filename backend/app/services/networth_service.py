"""
Net worth calculation service.
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.models.account import Account
from app.models.balance_history import BalanceHistory
from app.models.transaction import Transaction


class NetWorthError(Exception):
    """Base exception for net worth errors."""

    pass


def get_current_networth(db: Session) -> Decimal:
    """
    Calculate current net worth from calculated (transaction-derived) balances.

    Assets (bank, debit, cash) contribute positively.
    Liabilities (credit) contribute negatively.

    Args:
        db: Database session

    Returns:
        Total net worth as Decimal
    """
    from app.services.balance_inference import get_calculated_balance

    accounts = db.query(Account).filter(Account.is_active == True).all()

    net_worth = Decimal("0.00")

    for account in accounts:
        calc_bal, _ = get_calculated_balance(db, account)
        balance = Decimal(str(calc_bal))
        if account.is_asset:
            net_worth += balance
        else:
            if balance < 0:
                net_worth -= abs(balance)
            else:
                net_worth -= balance

    return net_worth


def get_networth_breakdown(db: Session) -> Dict[str, Any]:
    """
    Get detailed breakdown of net worth by account type.
    Uses calculated (transaction-derived) balances for totals.

    Returns:
        Dictionary with total_assets, total_liabilities, net_worth, and list of accounts
    """
    from app.services.balance_inference import get_calculated_balance

    accounts = db.query(Account).filter(Account.is_active == True).all()

    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    accounts_data = []

    for account in accounts:
        calc_bal, is_stale = get_calculated_balance(db, account)
        balance = Decimal(str(calc_bal))

        account_info = {
            "id": str(account.id),
            "name": account.name,
            "account_type": account.account_type.value,
            "current_balance": float(account.current_balance)
            if account.current_balance is not None
            else 0.0,
            "calculated_balance": calc_bal,
            "is_stale": is_stale,
            "is_asset": account.is_asset,
            "balance_updated_at": account.balance_updated_at.isoformat()
            if account.balance_updated_at
            else None,
        }

        if account.is_asset:
            total_assets += balance
        else:
            if balance < 0:
                total_liabilities += abs(balance)
            else:
                total_liabilities += balance

        accounts_data.append(account_info)

    net_worth = total_assets - total_liabilities

    return {
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "net_worth": float(net_worth),
        "accounts": accounts_data,
    }


def record_balance_snapshot(
    db: Session, account_id: str, balance: Decimal, recorded_date: date = None
) -> BalanceHistory:
    """
    Record a balance snapshot for an account.

    Args:
        db: Database session
        account_id: Account ID
        balance: Balance to record
        recorded_date: Date to record (defaults to today)

    Returns:
        Created BalanceHistory record

    Raises:
        NetWorthError: If account not found
    """
    from sqlalchemy.exc import SQLAlchemyError

    if recorded_date is None:
        recorded_date = date.today()

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise NetWorthError(f"Account {account_id} not found")

    try:
        snapshot = BalanceHistory(
            account_id=str(account_id),
            balance=float(balance),
            recorded_at=recorded_date,
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return snapshot

    except SQLAlchemyError as e:
        db.rollback()
        raise NetWorthError(f"Failed to record balance snapshot: {str(e)}")


def get_networth_history(
    db: Session, start_date: date, end_date: date = None
) -> List[Dict[str, Any]]:
    """
    Get net worth history from balance snapshots.

    Args:
        db: Database session
        start_date: Start date for query
        end_date: End date for query (defaults to today)

    Returns:
        List of net worth snapshots with date and total net worth
    """
    if end_date is None:
        end_date = date.today()

    accounts = db.query(Account).filter(Account.is_active == True).all()

    asset_accounts = {str(acc.id) for acc in accounts if acc.is_asset}
    liability_accounts = {str(acc.id) for acc in accounts if not acc.is_asset}

    if not asset_accounts and not liability_accounts:
        return []

    snapshots = (
        db.query(BalanceHistory)
        .filter(
            BalanceHistory.recorded_at >= start_date,
            BalanceHistory.recorded_at <= end_date,
            BalanceHistory.account_id.in_(asset_accounts | liability_accounts),
        )
        .order_by(BalanceHistory.recorded_at.asc())
        .all()
    )

    if not snapshots:
        return []

    balance_lookup: Dict[tuple, Decimal] = {}
    for s in snapshots:
        key = (s.recorded_at, s.account_id)
        balance_lookup[key] = (
            Decimal(str(s.balance)) if s.balance is not None else Decimal("0.00")
        )

    unique_dates = sorted(set(s.recorded_at for s in snapshots))

    history = []
    for unique_date in unique_dates:
        total_net_worth = Decimal("0.00")

        for acc_id in asset_accounts:
            balance_value = balance_lookup.get((unique_date, acc_id), Decimal("0.00"))
            total_net_worth += balance_value

        for acc_id in liability_accounts:
            balance_value = balance_lookup.get((unique_date, acc_id), Decimal("0.00"))
            total_net_worth -= abs(balance_value)

        history.append(
            {"date": unique_date.isoformat(), "net_worth": float(total_net_worth)}
        )

    return history


def auto_snapshot_all_balances(db: Session) -> Dict[str, int]:
    """
    Automatically record balance snapshots for all active accounts.

    This is for periodic snapshots to track net worth over time.

    Args:
        db: Database session

    Returns:
        Dictionary with total snapshots created and error count
    """
    from app.services.balance_inference import get_calculated_balance

    accounts = db.query(Account).filter(Account.is_active == True).all()

    created = 0
    errors = 0

    for account in accounts:
        try:
            calc_bal, _ = get_calculated_balance(db, account)
            record_balance_snapshot(db, account.id, Decimal(str(calc_bal)))
            created += 1
        except NetWorthError:
            errors += 1

    return {"total_snapshots": created, "errors": errors}
