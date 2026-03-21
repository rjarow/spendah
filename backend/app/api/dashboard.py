"""
Dashboard API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date
from typing import Optional
from decimal import Decimal

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.dashboard import (
    DashboardSummary,
    CategoryTotal,
    VsLastMonth,
    MonthTrend,
    RecentTransaction,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: Session = Depends(get_db),
):
    """
    Get dashboard summary for a month.
    Returns: total_income, total_expenses, net, by_category, vs_last_month
    """
    if month:
        year, m = map(int, month.split("-"))
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

    total_income_raw = db.query(func.sum(Transaction.amount)).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date,
        Transaction.amount > 0,
    ).scalar() or 0

    total_expenses_raw = db.query(func.sum(func.abs(Transaction.amount))).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date,
        Transaction.amount < 0,
    ).scalar() or 0

    total_income = Decimal(str(float(total_income_raw)))
    total_expenses = Decimal(str(float(total_expenses_raw)))
    net = total_income - total_expenses

    category_results = (
        db.query(
            Transaction.category_id,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.category_id)
        .all()
    )

    categories = {str(c.id): c.name for c in db.query(Category).all()}

    category_totals = {}
    for cat_id, amount in category_results:
        cat_key = str(cat_id) if cat_id else "uncategorized"
        category_totals[cat_key] = amount

    categories["uncategorized"] = "Uncategorized"

    by_category = [
        {
            "category_id": cat_id,
            "category_name": categories.get(cat_id, "Unknown"),
            "amount": float(amount),
            "percent": float(float(amount) / float(total_expenses) * 100)
            if total_expenses > 0
            else 0,
        }
        for cat_id, amount in sorted(
            category_totals.items(), key=lambda x: x[1], reverse=True
        )
    ]

    prev_month = start_date.month - 1 if start_date.month > 1 else 12
    prev_year = start_date.year if start_date.month > 1 else start_date.year - 1
    prev_start = date(prev_year, prev_month, 1)
    prev_end = start_date

    prev_income_raw = db.query(func.sum(Transaction.amount)).filter(
        Transaction.date >= prev_start,
        Transaction.date < prev_end,
        Transaction.amount > 0,
    ).scalar() or 0

    prev_expenses_raw = db.query(func.sum(func.abs(Transaction.amount))).filter(
        Transaction.date >= prev_start,
        Transaction.date < prev_end,
        Transaction.amount < 0,
    ).scalar() or 0

    prev_income = Decimal(str(float(prev_income_raw)))
    prev_expenses = Decimal(str(float(prev_expenses_raw)))

    income_change_pct = (
        ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    )
    expense_change_pct = (
        ((total_expenses - prev_expenses) / prev_expenses * 100)
        if prev_expenses > 0
        else 0
    )

    return DashboardSummary(
        month=start_date.strftime("%Y-%m"),
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        net=float(net),
        by_category=[CategoryTotal(**cat) for cat in by_category],
        vs_last_month=VsLastMonth(
            income_change_pct=round(float(income_change_pct), 1),
            expense_change_pct=round(float(expense_change_pct), 1),
        ),
    )


@router.get("/trends", response_model=list[MonthTrend])
def get_spending_trends(
    months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db)
):
    """
    Get spending trends over multiple months.
    Returns: [{month, income, expenses, net}, ...]
    """
    today = date.today()
    m = today.month - months + 1
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    start_date = date(y, m, 1)

    results = (
        db.query(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                "income"
            ),
            func.sum(
                case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=0)
            ).label("expenses"),
        )
        .filter(Transaction.date >= start_date)
        .group_by(func.strftime("%Y-%m", Transaction.date))
        .all()
    )

    trends_dict = {
        r.month: {"income": float(r.income or 0), "expenses": float(r.expenses or 0)}
        for r in results
    }

    trends = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        month_str = f"{y:04d}-{m:02d}"
        data = trends_dict.get(month_str, {"income": 0, "expenses": 0})

        trends.append(
            MonthTrend(
                month=month_str,
                income=data["income"],
                expenses=data["expenses"],
                net=data["income"] - data["expenses"],
            )
        )

    return trends


@router.get("/recent-transactions", response_model=list[RecentTransaction])
def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
):
    """Get most recent transactions for dashboard widget"""
    transactions = (
        db.query(Transaction).order_by(Transaction.date.desc()).limit(limit).all()
    )

    category_ids = {str(t.category_id) for t in transactions if t.category_id}
    categories = (
        {
            str(c.id): c.name
            for c in db.query(Category).filter(Category.id.in_(category_ids)).all()
        }
        if category_ids
        else {}
    )

    return [
        RecentTransaction(
            id=str(t.id),
            date=t.date.isoformat(),
            merchant=t.clean_merchant or t.raw_description,
            category=categories.get(str(t.category_id), "Uncategorized")
            if t.category_id
            else "Uncategorized",
            amount=float(t.amount),
        )
        for t in transactions
    ]
