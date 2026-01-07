"""
Dashboard API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from decimal import Decimal

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.dashboard import DashboardSummary, CategoryTotal, VsLastMonth, MonthTrend, RecentTransaction

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary for a month.
    Returns: total_income, total_expenses, net, by_category, vs_last_month
    """
    if month:
        year, m = map(int, month.split('-'))
        start_date = date(year, m, 1)
        if m == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, m + 1, 1)
    else:
        today = date.today()
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1)
        else:
            end_date = date(today.year, today.month + 1, 1)

    transactions = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()

    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    net = total_income - total_expenses

    category_totals = {}
    for t in transactions:
        if t.amount < 0:
            cat_id = str(t.category_id) if t.category_id else 'uncategorized'
            category_totals[cat_id] = category_totals.get(cat_id, Decimal('0')) + abs(t.amount)

    categories = {str(c.id): c.name for c in db.query(Category).all()}
    categories['uncategorized'] = 'Uncategorized'

    by_category = [
        {
            "category_id": cat_id,
            "category_name": categories.get(cat_id, 'Unknown'),
            "amount": float(amount),
            "percent": float(amount / total_expenses * 100) if total_expenses > 0 else 0
        }
        for cat_id, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    prev_month = start_date.month - 1 if start_date.month > 1 else 12
    prev_year = start_date.year if start_date.month > 1 else start_date.year - 1
    prev_start = date(prev_year, prev_month, 1)
    prev_end = start_date

    prev_transactions = db.query(Transaction).filter(
        Transaction.date >= prev_start,
        Transaction.date < prev_end
    ).all()

    prev_income = sum(t.amount for t in prev_transactions if t.amount > 0)
    prev_expenses = abs(sum(t.amount for t in prev_transactions if t.amount < 0))

    income_change_pct = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_change_pct = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0

    return DashboardSummary(
        month=start_date.strftime("%Y-%m"),
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        net=float(net),
        by_category=[CategoryTotal(**cat) for cat in by_category],
        vs_last_month=VsLastMonth(
            income_change_pct=round(float(income_change_pct), 1),
            expense_change_pct=round(float(expense_change_pct), 1)
        )
    )


@router.get("/trends", response_model=list[MonthTrend])
def get_spending_trends(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """
    Get spending trends over multiple months.
    Returns: [{month, income, expenses, net}, ...]
    """
    today = date.today()
    trends = []

    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        start_date = date(y, m, 1)
        if m == 12:
            end_date = date(y + 1, 1, 1)
        else:
            end_date = date(y, m + 1, 1)

        transactions = db.query(Transaction).filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()

        income = sum(t.amount for t in transactions if t.amount > 0)
        expenses = abs(sum(t.amount for t in transactions if t.amount < 0))

        trends.append(MonthTrend(
            month=start_date.strftime("%Y-%m"),
            income=float(income),
            expenses=float(expenses),
            net=float(income - expenses)
        ))

    return trends


@router.get("/recent-transactions", response_model=list[RecentTransaction])
def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get most recent transactions for dashboard widget"""
    transactions = db.query(Transaction).order_by(
        Transaction.date.desc()
    ).limit(limit).all()

    categories = {str(c.id): c.name for c in db.query(Category).all()}

    return [
        RecentTransaction(
            id=str(t.id),
            date=t.date.isoformat(),
            merchant=t.clean_merchant or t.raw_description,
            category=categories.get(str(t.category_id), "Uncategorized") if t.category_id else "Uncategorized",
            amount=float(t.amount)
        )
        for t in transactions
    ]
