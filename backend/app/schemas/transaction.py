"""
Transaction schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class TransactionBase(BaseModel):
    date: date
    amount: Decimal
    raw_description: str
    clean_merchant: Optional[str] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False


class TransactionCreate(TransactionBase):
    account_id: str
    hash: str


class TransactionUpdate(BaseModel):
    clean_merchant: Optional[str] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None


class TransactionResponse(BaseModel):
    id: str
    hash: str
    date: date
    amount: Decimal
    raw_description: str
    clean_merchant: Optional[str]
    category_id: Optional[str]
    account_id: str
    is_recurring: bool
    recurring_group_id: Optional[str]
    notes: Optional[str]
    ai_categorized: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    pages: int
