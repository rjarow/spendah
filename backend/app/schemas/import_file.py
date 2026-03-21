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
    debit_col: Optional[int] = Field(
        None, description="Column index for debit (if separate)"
    )
    credit_col: Optional[int] = Field(
        None, description="Column index for credit (if separate)"
    )
    balance_col: Optional[int] = Field(
        None, description="Column index for balance (if present)"
    )
    account_col: Optional[int] = Field(
        None, description="Column index for account name (if present)"
    )


class ImportUploadResponse(BaseModel):
    import_id: str
    filename: str
    row_count: int
    headers: List[str]
    preview_rows: List[List[str]]
    detected_format: Optional[Dict[str, Any]] = None
    extracted_balance: Optional[float] = None
    saved_format: Optional["SavedFormatMatch"] = None

    class Config:
        from_attributes = True


class ImportConfirmRequest(BaseModel):
    account_id: Optional[str] = Field(
        None, description="Account ID (required if account_col not set)"
    )
    column_mapping: ColumnMapping
    date_format: str = "%d/%m/%Y"
    save_format: bool = False
    format_name: Optional[str] = None
    update_balance: bool = False
    new_balance: Optional[float] = None
    auto_create_accounts: bool = Field(
        False, description="Auto-create accounts from account_col"
    )
    default_account_type: str = Field(
        "checking", description="Account type for auto-created accounts"
    )


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
    account_id: Optional[str] = None
    status: ImportStatus
    transactions_imported: int
    transactions_skipped: int
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SavedFormatResponse(BaseModel):
    id: str
    name: str
    fingerprint: str
    file_type: str
    column_mapping: Dict[str, Any]
    date_format: str
    amount_style: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SavedFormatListResponse(BaseModel):
    items: List[SavedFormatResponse]
    total: int


class SavedFormatMatch(BaseModel):
    format_id: str
    name: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    column_mapping: Dict[str, Any]
    date_format: str
    amount_style: str
