"""Pydantic schemas for alerts."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.alert import AlertType, Severity


class AlertBase(BaseModel):
    type: AlertType
    severity: Severity
    title: str
    description: str
    transaction_id: Optional[str] = None
    recurring_group_id: Optional[str] = None
    budget_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None
    action_taken: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    type: AlertType
    severity: Severity
    title: str
    description: str
    transaction_id: Optional[str] = None
    recurring_group_id: Optional[str] = None
    budget_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="alert_metadata")
    is_read: bool
    is_dismissed: bool
    action_taken: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AlertsListResponse(BaseModel):
    items: List[AlertResponse]
    unread_count: int
    total: int


class UnreadCountResponse(BaseModel):
    count: int


class AlertSettingsBase(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: float = 3.0
    unusual_merchant_threshold: float = 200.0
    subscription_review_days: int = 90
    annual_charge_warning_days: int = 14
    budget_warning_threshold: int = 80
    budget_alerts_enabled: bool = True
    alerts_enabled: bool = True


class AlertSettingsUpdate(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: Optional[float] = None
    unusual_merchant_threshold: Optional[float] = None
    subscription_review_days: Optional[int] = None
    annual_charge_warning_days: Optional[int] = None
    budget_warning_threshold: Optional[int] = None
    budget_alerts_enabled: Optional[bool] = None
    alerts_enabled: Optional[bool] = None


class SubscriptionInsight(BaseModel):
    type: str
    recurring_group_id: str
    merchant: str
    amount: float
    frequency: str
    insight: str
    recommendation: str


class SubscriptionReviewResponse(BaseModel):
    total_monthly_cost: float
    total_yearly_cost: float
    subscription_count: int
    insights: List[SubscriptionInsight]
    summary: str
    alert_id: Optional[str] = None


class UpcomingRenewal(BaseModel):
    recurring_group_id: str
    merchant: str
    amount: float
    frequency: str
    next_date: str
    days_until: int


class UpcomingRenewalsResponse(BaseModel):
    renewals: List[UpcomingRenewal]
    total_upcoming_30_days: float


class AlertSettingsResponse(AlertSettingsBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
