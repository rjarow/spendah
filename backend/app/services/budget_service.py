"""
Budget progress calculation service.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction
from app.models.category import Category


def calculate_period_dates(
    period: BudgetPeriod, start_date: datetime
) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for a budget period.

    Args:
        period: Budget period type (weekly, monthly, yearly)
        start_date: The start date of the budget period

    Returns:
        Tuple of (period_start, period_end) dates
    """
    dt = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == BudgetPeriod.weekly:
        period_start = dt
        period_end = period_start + timedelta(days=6)

    elif period == BudgetPeriod.monthly:
        period_start = dt.replace(day=1)
        if dt.month == 12:
            next_month = period_start.replace(year=dt.year + 1, month=1)
        else:
            next_month = period_start.replace(month=dt.month + 1)
        period_end = next_month - timedelta(days=1)

    elif period == BudgetPeriod.yearly:
        period_start = dt.replace(month=1, day=1)
        period_end = dt.replace(month=12, day=31)

    return period_start, period_end


def get_budget_progress(
    db: Session, budget_id: str, as_of_date: Optional[datetime] = None
) -> Optional[dict]:
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

    if as_of_date is None:
        as_of_date = datetime.utcnow()

    if budget.period == BudgetPeriod.weekly:
        # Find which weekly period as_of_date falls into, aligned to budget start
        budget_start = budget.start_date if isinstance(budget.start_date, datetime) else datetime.combine(budget.start_date, datetime.min.time())
        days_since_start = (as_of_date - budget_start).days
        period_offset = (days_since_start // 7) * 7
        current_period_start = budget_start + timedelta(days=period_offset)
        period_start, period_end = calculate_period_dates(budget.period, current_period_start)
    else:
        period_start, period_end = calculate_period_dates(budget.period, as_of_date)

    if budget.category_id:
        transactions = (
            db.query(Transaction)
            .filter(
                and_(
                    Transaction.date >= period_start.date(),
                    Transaction.date <= period_end.date(),
                    Transaction.category_id == budget.category_id,
                )
            )
            .all()
        )
    else:
        transactions = (
            db.query(Transaction)
            .filter(
                and_(
                    Transaction.date >= period_start.date(),
                    Transaction.date <= period_end.date(),
                )
            )
            .all()
        )

    spent = sum(abs(txn.amount) for txn in transactions)

    remaining = budget.amount - spent
    percent_used = (spent / budget.amount) * 100 if budget.amount > 0 else 0
    is_over_budget = spent > budget.amount

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
        "is_over_budget": is_over_budget,
    }


def get_all_budgets_progress(
    db: Session, as_of_date: Optional[datetime] = None
) -> list[dict]:
    """
    Calculate progress for all active budgets.
    Optimized to use batch queries instead of N+1.

    Args:
        db: Database session
        as_of_date: Date to calculate progress as of (defaults to today)

    Returns:
        List of budget progress dicts
    """
    if as_of_date is None:
        as_of_date = datetime.utcnow()

    budgets = db.query(Budget).filter(Budget.is_active == True).all()

    if not budgets:
        return []

    category_ids = [b.category_id for b in budgets if b.category_id]
    categories_by_id: Dict[str, str] = {}
    if category_ids:
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        categories_by_id = {str(c.id): c.name for c in categories}

    progress_list = []
    for budget in budgets:
        period_start, period_end = calculate_period_dates(
            budget.period, as_of_date if as_of_date else budget.start_date
        )

        if budget.category_id:
            spent_result = (
                db.query(func.sum(func.abs(Transaction.amount)))
                .filter(
                    and_(
                        Transaction.date >= period_start.date(),
                        Transaction.date <= period_end.date(),
                        Transaction.category_id == budget.category_id,
                    )
                )
                .scalar()
            )
            spent = float(spent_result) if spent_result else 0.0
        else:
            spent_result = (
                db.query(func.sum(func.abs(Transaction.amount)))
                .filter(
                    and_(
                        Transaction.date >= period_start.date(),
                        Transaction.date <= period_end.date(),
                    )
                )
                .scalar()
            )
            spent = float(spent_result) if spent_result else 0.0

        remaining = float(budget.amount) - spent
        percent_used = (
            (spent / float(budget.amount)) * 100 if float(budget.amount) > 0 else 0
        )
        is_over_budget = spent > float(budget.amount)

        category_name = (
            categories_by_id.get(str(budget.category_id))
            if budget.category_id
            else None
        )

        progress_list.append(
            {
                "id": budget.id,
                "category_id": budget.category_id,
                "category_name": category_name,
                "amount": budget.amount,
                "period": budget.period,
                "start_date": budget.start_date,
                "spent": spent,
                "remaining": remaining,
                "percent_used": percent_used,
                "is_over_budget": is_over_budget,
            }
        )

    return progress_list
