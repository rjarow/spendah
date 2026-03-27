"""
Dashboard API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date, datetime, timedelta
from typing import Optional
from decimal import Decimal

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.account import Account
from app.models.balance_history import BalanceHistory
from app.schemas.dashboard import (
    DashboardSummary,
    CategoryTotal,
    VsLastMonth,
    MonthTrend,
    RecentTransaction,
    TopMerchant,
    AccountBalance,
    AccountBalancesResponse,
    CategoryTrend,
    CategoryTrendsResponse,
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

    total_income_raw = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.amount > 0,
        )
        .scalar()
        or 0
    )

    total_expenses_raw = (
        db.query(func.sum(func.abs(Transaction.amount)))
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.amount < 0,
        )
        .scalar()
        or 0
    )

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

    prev_income_raw = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.date >= prev_start,
            Transaction.date < prev_end,
            Transaction.amount > 0,
        )
        .scalar()
        or 0
    )

    prev_expenses_raw = (
        db.query(func.sum(func.abs(Transaction.amount)))
        .filter(
            Transaction.date >= prev_start,
            Transaction.date < prev_end,
            Transaction.amount < 0,
        )
        .scalar()
        or 0
    )

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

    transaction_count_raw = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
        )
        .scalar()
        or 0
    )

    days_elapsed = (date.today() - start_date).days + 1
    days_in_month = (end_date - start_date).days
    daily_average_spend = (
        float(total_expenses) / days_elapsed if days_elapsed > 0 else 0
    )
    projected_spend = daily_average_spend * days_in_month

    savings_rate = None
    if float(total_income) > 0:
        savings_rate = round(
            ((float(total_income) - float(total_expenses)) / float(total_income)) * 100,
            1,
        )

    top_merchant_result = (
        db.query(
            Transaction.clean_merchant,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.clean_merchant)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .first()
    )

    top_merchant = None
    if top_merchant_result and top_merchant_result[0]:
        top_merchant = TopMerchant(
            name=top_merchant_result[0] or "Unknown",
            amount=float(top_merchant_result[1] or 0),
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
        savings_rate=savings_rate,
        daily_average_spend=round(daily_average_spend, 2),
        projected_spend=round(projected_spend, 2),
        top_merchant=top_merchant,
        transaction_count=transaction_count_raw,
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


@router.get("/account-balances", response_model=AccountBalancesResponse)
def get_account_balances(db: Session = Depends(get_db)):
    """Get all account balances grouped by asset/liability."""
    accounts = db.query(Account).filter(Account.is_active == True).all()

    account_balances = []
    total_assets = 0.0
    total_liabilities = 0.0

    for acc in accounts:
        balance = float(acc.current_balance or 0)
        is_asset = acc.is_asset

        if is_asset:
            total_assets += balance
        else:
            total_liabilities += abs(balance)

        account_balances.append(
            AccountBalance(
                id=str(acc.id),
                name=acc.name,
                account_type=acc.account_type.value,
                calculated_balance=balance,
                is_asset=is_asset,
            )
        )

    net_worth = total_assets - total_liabilities

    one_month_ago = date.today() - timedelta(days=30)
    prev_snapshot = (
        db.query(BalanceHistory)
        .filter(BalanceHistory.recorded_at < one_month_ago)
        .order_by(BalanceHistory.recorded_at.desc())
        .first()
    )

    change_from_last_month = None
    if prev_snapshot:
        prev_net = sum(
            float(acc.current_balance or 0)
            for acc in accounts
            if acc.account_type.value in ("checking", "savings", "cash", "investment")
        ) - sum(
            abs(float(acc.current_balance or 0))
            for acc in accounts
            if acc.account_type.value
            not in ("checking", "savings", "cash", "investment")
        )
        change_from_last_month = net_worth - prev_net

    return AccountBalancesResponse(
        accounts=account_balances,
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        net_worth=round(net_worth, 2),
        change_from_last_month=round(change_from_last_month, 2)
        if change_from_last_month
        else None,
    )


@router.get("/category-trends", response_model=CategoryTrendsResponse)
def get_category_trends(
    months: int = Query(3, ge=1, le=12), db: Session = Depends(get_db)
):
    """Get spending trends by category for the last N months."""
    today = date.today()
    m = today.month - months + 1
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    start_date = date(y, m, 1)

    results = (
        db.query(
            Transaction.category_id,
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .filter(
            Transaction.date >= start_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.category_id, func.strftime("%Y-%m", Transaction.date))
        .all()
    )

    categories = {str(c.id): c.name for c in db.query(Category).all()}
    categories["uncategorized"] = "Uncategorized"

    category_data = {}
    month_set = set()

    for r in results:
        cat_id = str(r.category_id) if r.category_id else "uncategorized"
        month_str = r.month
        month_set.add(month_str)

        if cat_id not in category_data:
            category_data[cat_id] = {}

        category_data[cat_id][month_str] = float(r.total or 0)

    months_list = sorted(list(month_set))

    category_trends = []
    for cat_id, monthly_data in category_data.items():
        totals = [{"month": m, "amount": monthly_data.get(m, 0)} for m in months_list]

        if len(totals) >= 2:
            prev_total = (
                totals[-2].get("amount", 0)
                if len(totals) > 1
                else totals[0].get("amount", 0)
            )
            curr_total = totals[-1].get("amount", 0)
            change_pct = (
                ((curr_total - prev_total) / prev_total * 100) if prev_total > 0 else 0
            )
            is_spike = change_pct > 25
        else:
            change_pct = None
            is_spike = False

        category_trends.append(
            CategoryTrend(
                category_id=cat_id,
                category_name=categories.get(cat_id, "Unknown"),
                monthly_totals=totals,
                change_pct=round(change_pct, 1) if change_pct else None,
                is_spike=is_spike,
            )
        )

    category_trends.sort(
        key=lambda x: sum(t.get("amount", 0) for t in x.monthly_totals), reverse=True
    )

    return CategoryTrendsResponse(
        categories=category_trends,
        months=months_list,
    )
