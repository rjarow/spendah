"""
Dashboard schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class CategoryTotal(BaseModel):
    category_id: str
    category_name: str
    amount: float
    percent: float


class VsLastMonth(BaseModel):
    income_change_pct: float
    expense_change_pct: float


class DashboardSummary(BaseModel):
    month: str
    total_income: float
    total_expenses: float
    net: float
    by_category: List[CategoryTotal]
    vs_last_month: VsLastMonth


class MonthTrend(BaseModel):
    month: str
    income: float
    expenses: float
    net: float


class RecentTransaction(BaseModel):
    id: str
    date: str
    merchant: str
    category: str
    amount: float
