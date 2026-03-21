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


class TopMerchant(BaseModel):
    name: str
    amount: float


class DashboardSummary(BaseModel):
    month: str
    total_income: float
    total_expenses: float
    net: float
    by_category: List[CategoryTotal]
    vs_last_month: VsLastMonth
    savings_rate: Optional[float] = None
    daily_average_spend: Optional[float] = None
    projected_spend: Optional[float] = None
    top_merchant: Optional[TopMerchant] = None
    transaction_count: int = 0


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


class AccountBalance(BaseModel):
    id: str
    name: str
    account_type: str
    calculated_balance: float
    is_asset: bool


class AccountBalancesResponse(BaseModel):
    accounts: List[AccountBalance]
    total_assets: float
    total_liabilities: float
    net_worth: float
    change_from_last_month: Optional[float] = None


class CategoryTrend(BaseModel):
    category_id: str
    category_name: str
    monthly_totals: List[dict]
    change_pct: Optional[float] = None
    is_spike: bool = False


class CategoryTrendsResponse(BaseModel):
    categories: List[CategoryTrend]
    months: List[str]
