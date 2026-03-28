"""
Budget Pydantic schemas for API validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.budget import BudgetPeriod


class BudgetBase(BaseModel):
    """Base budget schema."""

    amount: Decimal = Field(..., gt=0)
    period: BudgetPeriod
    start_date: Optional[datetime] = Field(None)
    is_active: bool = Field(True)


class BudgetCreate(BudgetBase):
    """Schema for creating a budget."""

    category_id: Optional[str] = Field(None)


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""

    category_id: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: str
    name: str

    class Config:
        from_attributes = True


class BudgetResponse(BudgetBase):
    """Schema for budget response."""

    id: str
    category_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


class BudgetList(BaseModel):
    """Schema for listing budgets."""

    items: list[BudgetResponse]
    total: int


class BudgetProgress(BaseModel):
    """Schema for budget progress calculation."""

    id: str
    category_id: Optional[str]
    category_name: Optional[str] = None
    amount: Decimal
    period: BudgetPeriod
    start_date: datetime
    spent: Decimal
    remaining: Decimal
    percent_used: float
    is_over_budget: bool

    class Config:
        from_attributes = True


class BudgetSuggestionAccept(BaseModel):
    """Schema for accepting a budget suggestion."""

    category_id: str
    amount: float
    period: str = "monthly"
