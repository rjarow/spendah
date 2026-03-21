"""
Insights schemas for API response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class CategoryMonthlyTotal(BaseModel):
    month: str
    amount: float


class SpendingByCategoryResponse(BaseModel):
    categories: List[Dict]
    months: List[str]
    total_by_category: Dict[str, float]


class MerchantRanking(BaseModel):
    merchant: str
    total: float
    transaction_count: int
    average_amount: float
    category: str
    trend: str
    change_pct: Optional[float] = None


class MerchantRankingResponse(BaseModel):
    merchants: List[MerchantRanking]
    months: int
    total_spending: float


class MonthlySummary(BaseModel):
    month: str
    income: float
    expenses: float
    net: float
    savings_rate: Optional[float] = None
    transaction_count: int


class MonthlySummaryResponse(BaseModel):
    months: List[MonthlySummary]
    total_income: float
    total_expenses: float


class Anomaly(BaseModel):
    type: str
    description: str
    amount: float
    category: str
    severity: str
    transaction_id: Optional[str] = None


class AnomalyResponse(BaseModel):
    anomalies: List[Anomaly]
    total: int
