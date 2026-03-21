"""
Balance inference service for calculating account balances from transactions.
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import date

from app.models.account import Account, AccountType
from app.models.transaction import Transaction


class BalanceInferenceError(Exception):
    """Base exception for balance inference errors."""
    pass


def calculate_balance_from_transactions(db: Session, account_id: str) -> Decimal:
    """
    Calculate balance from all transactions for an account.

    For asset accounts (bank, debit, cash):
        calculated_balance = starting_balance + sum_of_transactions
        (sum of transactions = total debits - total credits)

    For liability accounts (credit):
        calculated_balance = sum_of_transactions (sum of transactions = amount owed)

    Args:
        db: Database session
        account_id: Account ID

    Returns:
        Calculated balance as Decimal

    Raises:
        BalanceInferenceError: If account not found
    """
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise BalanceInferenceError(f"Account {account_id} not found")

    if not account.is_asset:
        # For liabilities (credit accounts), sum of transactions = amount owed
        # Transactions are stored as negative for expenses, positive for income
        total_transactions = db.query(Transaction.amount).filter(
            Transaction.account_id == account_id
        ).all()

        calculated_balance = Decimal("0.00")
        for (amount,) in total_transactions:
            calculated_balance += Decimal(str(amount))

        return calculated_balance
    else:
        # For assets (bank, debit, cash):
        # Calculate what the balance SHOULD be based on transactions
        # This requires knowing if we have a starting balance

        total_transactions = db.query(Transaction.amount).filter(
            Transaction.account_id == account_id
        ).all()

        # Sum all transactions (expenses are negative, income is positive)
        total_transactions_sum = Decimal("0.00")
        for (amount,) in total_transactions:
            total_transactions_sum += Decimal(str(amount))

        # If we have a current_balance, that's our reference point
        # If not, we assume 0 and use transaction sums directly
        if account.current_balance is not None:
            calculated_balance = account.current_balance + total_transactions_sum
        else:
            calculated_balance = total_transactions_sum

        return calculated_balance


def calculate_all_account_balances(db: Session) -> dict:
    """
    Calculate balances for all accounts from their transactions.

    Args:
        db: Database session

    Returns:
        Dictionary mapping account IDs to calculated balances
    """
    accounts = db.query(Account).filter(Account.is_active == True).all()

    balances = {}
    for account in accounts:
        try:
            balances[str(account.id)] = calculate_balance_from_transactions(db, str(account.id))
        except BalanceInferenceError:
            balances[str(account.id)] = None

    return balances


def get_calculated_balance(db: Session, account: "Account") -> tuple:
    """
    Return (calculated_balance, is_stale) for an account.

    Args:
        db: Database session
        account: Account model instance

    Returns:
        Tuple of (float, bool) — calculated balance and whether it differs from current_balance
    """
    try:
        calculated = calculate_balance_from_transactions(db, str(account.id))
        manual = account.current_balance if account.current_balance is not None else Decimal("0.00")
        is_stale = calculated != manual
        return (float(calculated), is_stale)
    except BalanceInferenceError:
        return (float(account.current_balance or 0), False)


def get_balance_difference(db: Session, account_id: str) -> dict:
    """
    Get the difference between manual balance and calculated balance.

    Args:
        db: Database session
        account_id: Account ID

    Returns:
        Dictionary with:
            - account_id
            - manual_balance
            - calculated_balance
            - difference
            - is_stale (bool indicating if manual balance is different from calculated)
    """
    from app.services.networth_service import get_networth_breakdown

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise BalanceInferenceError(f"Account {account_id} not found")

    manual_balance = account.current_balance if account.current_balance is not None else Decimal("0.00")
    calculated_balance = calculate_balance_from_transactions(db, account_id)
    difference = calculated_balance - manual_balance

    is_stale = difference != Decimal("0.00")

    return {
        "account_id": account_id,
        "name": account.name,
        "account_type": account.account_type.value,
        "manual_balance": float(manual_balance) if manual_balance is not None else 0.0,
        "calculated_balance": float(calculated_balance),
        "difference": float(difference),
        "is_stale": is_stale
    }


def get_accounts_with_stale_balances(db: Session) -> list:
    """
    Get all accounts where manual balance differs from calculated balance.

    Args:
        db: Database session

    Returns:
        List of account balance difference info dictionaries
    """
    accounts = db.query(Account).filter(Account.is_active == True).all()

    stale_accounts = []
    for account in accounts:
        try:
            diff_info = get_balance_difference(db, str(account.id))
            if diff_info["is_stale"]:
                stale_accounts.append(diff_info)
        except BalanceInferenceError:
            pass

    return stale_accounts


def infer_balance_from_transactions(db: Session, account_id: str) -> Decimal:
    """
    Inferred the balance for an account and update it.

    This is useful when user wants to sync calculated balance to manual.

    Args:
        db: Database session
        account_id: Account ID

    Returns:
        Updated balance as Decimal

    Raises:
        BalanceInferenceError: If account not found
    """
    calculated_balance = calculate_balance_from_transactions(db, account_id)

    from app.models.account import Account
    from sqlalchemy import func

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise BalanceInferenceError(f"Account {account_id} not found")

    account.current_balance = calculated_balance
    account.balance_updated_at = func.now()

    db.commit()
    db.refresh(account)

    return calculated_balance
