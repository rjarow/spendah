"""
Spending Insights API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc
from datetime import date, timedelta
from typing import Optional, List
from decimal import Decimal
import statistics

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.insights import (
    SpendingByCategoryResponse,
    CategoryMonthlyTotal,
    MerchantRankingResponse,
    MerchantRanking,
    MonthlySummaryResponse,
    MonthlySummary,
    AnomalyResponse,
    Anomaly,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/spending-by-category", response_model=SpendingByCategoryResponse)
def get_spending_by_category(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """Get per-category monthly spending totals for the last N months."""
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

    category_data = {}
    month_set = set()

    for r in results:
        cat_id = str(r.category_id) if r.category_id else "uncategorized"
        month_str = r.month
        month_set.add(month_str)

        if cat_id not in category_data:
            category_data[cat_id] = {
                "category_name": categories.get(cat_id, "Uncategorized"),
                "monthly_totals": {},
            }

        category_data[cat_id]["monthly_totals"][month_str] = float(r.total or 0)

    months_list = sorted(list(month_set))

    category_totals = []
    for cat_id, data in category_data.items():
        monthly = [
            CategoryMonthlyTotal(
                month=m,
                amount=data["monthly_totals"].get(m, 0),
            )
            for m in months_list
        ]

        total_amount = sum(m.amount for m in monthly)
        if len(monthly) >= 2:
            prev = monthly[-2].amount if len(monthly) > 1 else monthly[-1].amount
            curr = monthly[-1].amount
            change_pct = ((curr - prev) / prev * 100) if prev > 0 else None
        else:
            change_pct = None

        category_totals.append(
            {
                "category_id": cat_id,
                "category_name": data["category_name"],
                "monthly_totals": monthly,
                "total_amount": total_amount,
                "change_pct": round(change_pct, 1) if change_pct else None,
            }
        )

    category_totals.sort(key=lambda x: x["total_amount"], reverse=True)

    return SpendingByCategoryResponse(
        categories=category_totals,
        months=months_list,
        total_by_category={
            c["category_name"]: c["total_amount"] for c in category_totals
        },
    )


@router.get("/merchant-ranking", response_model=MerchantRankingResponse)
def get_merchant_ranking(
    months: int = Query(3, ge=1, le=12),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get top merchants by total spending."""
    today = date.today()
    m = today.month - months + 1
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    start_date = date(y, m, 1)

    prev_m = start_date.month - months
    prev_y = start_date.year
    while prev_m <= 0:
        prev_m += 12
        prev_y -= 1
    prev_start = date(prev_y, prev_m, 1)

    results = (
        db.query(
            Transaction.clean_merchant,
            func.sum(func.abs(Transaction.amount)).label("total"),
            func.count(Transaction.id).label("count"),
            func.avg(func.abs(Transaction.amount)).label("avg_amount"),
            Transaction.category_id,
        )
        .filter(
            Transaction.date >= start_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.clean_merchant, Transaction.category_id)
        .order_by(desc(func.sum(func.abs(Transaction.amount))))
        .limit(limit)
        .all()
    )

    categories = {str(c.id): c.name for c in db.query(Category).all()}

    prev_results = (
        db.query(
            Transaction.clean_merchant,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .filter(
            Transaction.date >= prev_start,
            Transaction.date < start_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.clean_merchant)
        .all()
    )

    prev_totals = {
        r.clean_merchant: float(r.total or 0) for r in prev_results if r.clean_merchant
    }

    merchants = []
    for r in results:
        merchant_name = r.clean_merchant or "Unknown"
        curr_total = float(r.total or 0)
        prev_total = prev_totals.get(merchant_name, 0)

        if prev_total > 0:
            change_pct = ((curr_total - prev_total) / prev_total) * 100
            trend = "up" if change_pct > 5 else "down" if change_pct < -5 else "flat"
        else:
            change_pct = None
            trend = "new"

        merchants.append(
            MerchantRanking(
                merchant=merchant_name,
                total=round(curr_total, 2),
                transaction_count=r.count,
                average_amount=round(float(r.avg_amount or 0), 2),
                category=categories.get(str(r.category_id), "Uncategorized")
                if r.category_id
                else "Uncategorized",
                trend=trend,
                change_pct=round(change_pct, 1) if change_pct else None,
            )
        )

    return MerchantRankingResponse(
        merchants=merchants,
        months=months,
        total_spending=sum(m.total for m in merchants),
    )


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    months: int = Query(12, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """Get monthly income/expense summary for the last N months."""
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
            func.count(Transaction.id).label("transaction_count"),
        )
        .filter(Transaction.date >= start_date)
        .group_by(func.strftime("%Y-%m", Transaction.date))
        .all()
    )

    data_by_month = {r.month: r for r in results}

    summaries = []
    for i in range(months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        month_str = f"{y:04d}-{m:02d}"
        r = data_by_month.get(month_str)

        income = float(r.income or 0) if r else 0
        expenses = float(r.expenses or 0) if r else 0
        net = income - expenses
        txn_count = r.transaction_count if r else 0

        savings_rate = round((net / income) * 100, 1) if income > 0 else None

        summaries.append(
            MonthlySummary(
                month=month_str,
                income=round(income, 2),
                expenses=round(expenses, 2),
                net=round(net, 2),
                savings_rate=savings_rate,
                transaction_count=txn_count,
            )
        )

    summaries.reverse()

    return MonthlySummaryResponse(
        months=summaries,
        total_income=sum(s.income for s in summaries),
        total_expenses=sum(s.expenses for s in summaries),
    )


@router.get("/anomalies", response_model=AnomalyResponse)
def get_anomalies(
    months: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Detect spending anomalies - unusual transactions and category spikes."""
    today = date.today()
    m = today.month - months + 1
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    start_date = date(y, m, 1)

    anomalies = []

    category_results = (
        db.query(
            Transaction.category_id,
            func.avg(func.abs(Transaction.amount)).label("avg"),
            func.stddev(func.abs(Transaction.amount)).label("stddev"),
        )
        .filter(
            Transaction.date >= start_date,
            Transaction.amount < 0,
        )
        .group_by(Transaction.category_id)
        .all()
    )

    category_stats = {
        str(r.category_id): {"avg": float(r.avg or 0), "stddev": float(r.stddev or 0)}
        for r in category_results
    }

    high_transactions = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start_date,
            Transaction.amount < 0,
        )
        .all()
    )

    for t in high_transactions:
        cat_id = str(t.category_id) if t.category_id else None
        stats = category_stats.get(cat_id, {"avg": 0, "stddev": 0})
        amount = abs(float(t.amount))

        if stats["stddev"] > 0 and amount > stats["avg"] + 2 * stats["stddev"]:
            anomalies.append(
                Anomaly(
                    type="unusual_transaction",
                    description=f"Unusual charge: ${t.clean_merchant or t.raw_description[:50]}",
                    amount=round(amount, 2),
                    category=t.category.name if t.category else "Uncategorized",
                    severity="high"
                    if amount > stats["avg"] + 3 * stats["stddev"]
                    else "medium",
                    transaction_id=str(t.id),
                )
            )

    category_totals = (
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

    category_monthly = {}
    for r in category_totals:
        cat_id = str(r.category_id) if r.category_id else "uncategorized"
        month = r.month
        if cat_id not in category_monthly:
            category_monthly[cat_id] = {}
        category_monthly[cat_id][month] = float(r.total or 0)

    categories = {str(c.id): c.name for c in db.query(Category).all()}

    for cat_id, monthly in category_monthly.items():
        values = list(monthly.values())
        if len(values) >= 2:
            avg = statistics.mean(values[:-1])
            curr = values[-1]
            if avg > 0:
                change_pct = ((curr - avg) / avg) * 100
                if change_pct > 50:
                    anomalies.append(
                        Anomaly(
                            type="category_spike",
                            description=f"{categories.get(cat_id, 'Unknown')} spending is {round(change_pct)}% above your {months}-month average",
                            amount=round(curr, 2),
                            category=categories.get(cat_id, "Unknown"),
                            severity="high" if change_pct > 100 else "medium",
                        )
                    )

    anomalies.sort(key=lambda x: x.amount, reverse=True)

    return AnomalyResponse(
        anomalies=anomalies[:20],
        total=len(anomalies),
    )
