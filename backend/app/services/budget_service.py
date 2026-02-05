"""
Budget progress calculation service.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction
from app.models.category import Category


def calculate_period_dates(period: BudgetPeriod, start_date: datetime) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for a budget period.

    Args:
        period: Budget period type (weekly, monthly, yearly)
        start_date: The start date of the budget period

    Returns:
        Tuple of (period_start, period_end) dates
    """
    period_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == BudgetPeriod.weekly:
        period_end = period_start + timedelta(days=6)

    elif period == BudgetPeriod.monthly:
        # Get first day of current month
        first_day = period_start.replace(day=1)
        # Get first day of next month
        if period_start.month == 12:
            next_month = first_day.replace(year=period_start.year + 1, month=1)
        else:
            next_month = first_day.replace(month=period_start.month + 1)
        period_end = next_month - timedelta(days=1)

    elif period == BudgetPeriod.yearly:
        # First day of the year
        first_day = period_start.replace(month=1, day=1)
        # Last day of the year
        last_day = period_start.replace(month=12, day=31)
        period_end = last_day

    return period_start, period_end


def get_budget_progress(db: Session, budget_id: str, as_of_date: Optional[datetime] = None) -> Optional[dict]:
    """
    Calculate budget progress for a specific budget.

    Args:
        db: Database session
        budget_id: ID of the budget to calculate progress for
        as_of_date: Date to calculate progress as of (defaults to today for current period,
                   or allows viewing historical periods by passing a date in the past)

    Returns:
        BudgetProgress dict with calculation results, or None if budget not found
    """
    budget = db.query(Budget).filter(Budget.id == budget_id).first()

    if not budget:
        return None

    # If as_of_date is provided (for historical views), use it to calculate dates
    # Otherwise use budget start_date for current period
    if as_of_date:
        period_start, period_end = calculate_period_dates(budget.period, as_of_date)
    else:
        period_start, period_end = calculate_period_dates(budget.period, budget.start_date)

    # Get transactions within the period
    if budget.category_id:
        # Budget for a specific category
        transactions = db.query(Transaction).filter(
            and_(
                Transaction.date >= period_start.date(),
                Transaction.date <= period_end.date(),
                Transaction.category_id == budget.category_id
            )
        ).all()
    else:
        # Overall budget (no category) - sum all expenses
        transactions = db.query(Transaction).filter(
            and_(
                Transaction.date >= period_start.date(),
                Transaction.date <= period_end.date()
            )
        ).all()

    # Calculate total spent (subtract amount to get expenses, not income)
    spent = sum(abs(txn.amount) for txn in transactions)

    # Calculate remaining and percent used
    remaining = budget.amount - spent
    percent_used = (spent / budget.amount) * 100 if budget.amount > 0 else 0
    is_over_budget = spent > budget.amount

    # Get category name if applicable
    category_name = None
    if budget.category_id:
        category = db.query(Category).filter(Category.id == budget.category_id).first()
        if category:
            category_name = category.name

    return {
        "id": budget.id,
        "category_id": budget.category_id,
        "category_name": category_name,
        "amount": budget.amount,
        "period": budget.period,
        "start_date": budget.start_date,
        "spent": spent,
        "remaining": remaining,
        "percent_used": percent_used,
        "is_over_budget": is_over_budget
    }


def get_all_budgets_progress(db: Session, as_of_date: Optional[datetime] = None) -> list[dict]:
    """
    Calculate progress for all active budgets.

    Args:
        db: Database session
        as_of_date: Date to calculate progress as of (defaults to today)

    Returns:
        List of budget progress dicts
    """
    if as_of_date is None:
        as_of_date = datetime.utcnow()

    budgets = db.query(Budget).filter(Budget.is_active == True).all()

    progress_list = []
    for budget in budgets:
        progress = get_budget_progress(db, budget.id)
        if progress:
            progress_list.append(progress)

    return progress_list

