"""
Rule schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MatchField(str, Enum):
    merchant = "merchant"
    description = "description"
    amount = "amount"


class MatchType(str, Enum):
    contains = "contains"
    exact = "exact"
    starts_with = "starts_with"
    regex = "regex"


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    match_field: MatchField
    match_type: MatchType
    match_value: str = Field(..., min_length=1, max_length=255)
    category_id: str
    priority: int = Field(default=100, ge=1, le=1000)
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    match_field: Optional[MatchField] = None
    match_type: Optional[MatchType] = None
    match_value: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: str
    name: str
    match_field: str
    match_type: str
    match_value: str
    category_id: str
    category_name: str
    priority: int
    is_active: bool
    auto_created: bool
    match_count: int
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    items: List[RuleResponse]
    total: int


class RuleTestRequest(BaseModel):
    text: str = Field(..., min_length=1)
    amount: Optional[float] = None


class RuleTestResponse(BaseModel):
    matched: bool
    rule: Optional[RuleResponse] = None


class RuleSuggestion(BaseModel):
    name: str
    match_field: str
    match_type: str
    match_value: str
    category_id: str
    category_name: str
    occurrence_count: int


class RuleSuggestionsResponse(BaseModel):
    suggestions: List[RuleSuggestion]
    total: int
