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
    Calculate current net worth from all account balances.

    Assets (bank, debit, cash) contribute positively.
    Liabilities (credit) contribute negatively.

    Args:
        db: Database session

    Returns:
        Total net worth as Decimal
    """
    accounts = db.query(Account).filter(Account.is_active == True).all()

    net_worth = Decimal("0.00")

    for account in accounts:
        if account.is_asset:
            net_worth += account.current_balance
        else:
            # Liabilities should be subtracted as positive value
            if account.current_balance < 0:
                net_worth -= abs(account.current_balance)
            else:
                net_worth -= account.current_balance

    return net_worth


def get_networth_breakdown(db: Session) -> Dict[str, Any]:
    """
    Get detailed breakdown of net worth by account type.

    Returns:
        Dictionary with total_assets, total_liabilities, net_worth, and list of accounts
    """
    accounts = db.query(Account).filter(Account.is_active == True).all()

    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    accounts_data = []

    for account in accounts:
        account_info = {
            "id": str(account.id),
            "name": account.name,
            "account_type": account.account_type.value,
            "current_balance": float(account.current_balance) if account.current_balance is not None else 0.0,
            "is_asset": account.is_asset
        }

        if account.is_asset:
            total_assets += account.current_balance
        else:
            # Liabilities should be added as positive value
            if account.current_balance < 0:
                total_liabilities += abs(account.current_balance)
            else:
                total_liabilities += account.current_balance

        accounts_data.append(account_info)

    net_worth = total_assets - total_liabilities

    return {
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "net_worth": float(net_worth),
        "accounts": accounts_data
    }


def record_balance_snapshot(db: Session, account_id: str, balance: Decimal, recorded_date: date = None) -> BalanceHistory:
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
            recorded_at=recorded_date
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return snapshot

    except SQLAlchemyError as e:
        db.rollback()
        raise NetWorthError(f"Failed to record balance snapshot: {str(e)}")


def get_networth_history(db: Session, start_date: date, end_date: date = None) -> List[Dict[str, Any]]:
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

    asset_accounts = [str(acc.id) for acc in accounts if acc.is_asset]
    liability_accounts = [str(acc.id) for acc in accounts if not acc.is_asset]

    if not asset_accounts and not liability_accounts:
        return []

    snapshots = db.query(BalanceHistory).filter(
        BalanceHistory.recorded_at >= start_date,
        BalanceHistory.recorded_at <= end_date,
        BalanceHistory.account_id.in_(asset_accounts + liability_accounts)
    ).order_by(BalanceHistory.recorded_at.asc()).all()

    history = []

    for snapshot in snapshots:
        total_net_worth = Decimal("0.00")

        for acc_id in asset_accounts:
            balance_value = _get_account_balance_at_date(db, acc_id, snapshot.recorded_at, asset=True)
            total_net_worth += balance_value

        for acc_id in liability_accounts:
            balance_value = _get_account_balance_at_date(db, acc_id, snapshot.recorded_at, asset=False)
            total_net_worth -= balance_value

        history.append({
            "date": snapshot.recorded_at.isoformat(),
            "net_worth": float(total_net_worth)
        })

    return history


def _get_account_balance_at_date(db: Session, account_id: str, record_date: date, asset: bool) -> Decimal:
    """
    Get balance for an account at a specific date.

    Args:
        db: Database session
        account_id: Account ID
        record_date: Date to get balance for
        asset: True if asset account, False if liability

    Returns:
        Balance as Decimal
    """
    balance_result = db.query(BalanceHistory.balance).filter(
        BalanceHistory.account_id == account_id,
        BalanceHistory.recorded_at == record_date
    ).first()

    balance_value = balance_result[0] if balance_result and balance_result[0] is not None else Decimal("0.00")
    return Decimal(str(balance_value))


def auto_snapshot_all_balances(db: Session) -> Dict[str, int]:
    """
    Automatically record balance snapshots for all active accounts.

    This is for periodic snapshots to track net worth over time.

    Args:
        db: Database session

    Returns:
        Dictionary with total snapshots created and error count
    """
    accounts = db.query(Account).filter(Account.is_active == True).all()

    created = 0
    errors = 0

    for account in accounts:
        try:
            record_balance_snapshot(db, account.id, account.current_balance)
            created += 1
        except NetWorthError:
            errors += 1

    return {
        "total_snapshots": created,
        "errors": errors
    }
