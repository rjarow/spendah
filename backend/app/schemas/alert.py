"""Pydantic schemas for alerts."""

from pydantic import BaseModel, Field, field_validator
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
    metadata: Optional[Dict[str, Any]] = None
    is_read: bool
    is_dismissed: bool
    action_taken: Optional[str] = None
    created_at: datetime

    @field_validator('metadata', mode='before')
    @classmethod
    def extract_alert_metadata(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        return None

    model_config = {"from_attributes": True}


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
    alerts_enabled: bool = True


class AlertSettingsUpdate(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: Optional[float] = None
    unusual_merchant_threshold: Optional[float] = None
    alerts_enabled: Optional[bool] = None


class AlertSettingsResponse(AlertSettingsBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
