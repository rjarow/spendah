"""
Account Pydantic schemas for API validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.account import AccountType


class AccountBase(BaseModel):
    """Base account schema."""
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType


class AccountCreate(AccountBase):
    """Schema for creating an account."""
    pass


class AccountUpdate(BaseModel):
    """Schema for updating an account."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[AccountType] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    """Schema for account response."""
    id: str
    learned_format_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AccountList(BaseModel):
    """Schema for listing accounts."""
    items: list[AccountResponse]
    total: int
