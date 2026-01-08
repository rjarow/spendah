"""Pydantic schemas for recurring groups."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class Frequency(str):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class RecurringGroupBase(BaseModel):
    name: str
    merchant_pattern: str
    expected_amount: Optional[Decimal] = None
    amount_variance: Optional[Decimal] = None
    frequency: str
    category_id: Optional[str] = None


class RecurringGroupCreate(RecurringGroupBase):
    pass


class RecurringGroupUpdate(BaseModel):
    name: Optional[str] = None
    merchant_pattern: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    amount_variance: Optional[Decimal] = None
    frequency: Optional[str] = None
    category_id: Optional[str] = None
    is_active: Optional[bool] = None


class RecurringGroupResponse(RecurringGroupBase):
    id: str
    last_seen_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    # Computed fields added by API
    transaction_count: Optional[int] = None

    class Config:
        from_attributes = True


class RecurringGroupWithTransactions(RecurringGroupResponse):
    """Extended response with recent transaction IDs."""
    recent_transaction_ids: List[str] = []


class MarkRecurringRequest(BaseModel):
    """Request to mark a transaction as recurring."""
    recurring_group_id: Optional[str] = None  # Link to existing group
    create_new: bool = False  # Or create a new group
    # If create_new is True:
    name: Optional[str] = None
    frequency: Optional[str] = None


class DetectionResult(BaseModel):
    """Result of recurring detection for a single pattern."""
    merchant_pattern: str
    suggested_name: str
    transaction_ids: List[str]
    frequency: str
    average_amount: Decimal
    confidence: float


class DetectionResponse(BaseModel):
    """Response from recurring detection."""
    detected: List[DetectionResult]
    total_found: int
