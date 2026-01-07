"""
Import file schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ColumnMapping(BaseModel):
    date_col: int = Field(..., description="Column index for date")
    amount_col: int = Field(..., description="Column index for amount")
    description_col: int = Field(..., description="Column index for description")
    debit_col: Optional[int] = Field(None, description="Column index for debit (if separate)")
    credit_col: Optional[int] = Field(None, description="Column index for credit (if separate)")
    balance_col: Optional[int] = Field(None, description="Column index for balance (if present)")


class ImportUploadResponse(BaseModel):
    import_id: str
    filename: str
    row_count: int
    headers: List[str]
    preview_rows: List[List[str]]
    detected_format: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ImportConfirmRequest(BaseModel):
    account_id: str
    column_mapping: ColumnMapping
    date_format: str = "%Y-%m-%d"
    save_format: bool = False
    format_name: Optional[str] = None


class ImportStatusResponse(BaseModel):
    import_id: str
    status: ImportStatus
    filename: str
    transactions_imported: int = 0
    transactions_skipped: int = 0
    errors: List[str] = []

    class Config:
        from_attributes = True


class ImportLogResponse(BaseModel):
    id: str
    filename: str
    account_id: str
    status: ImportStatus
    transactions_imported: int
    transactions_skipped: int
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
