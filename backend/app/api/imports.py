"""
Import API endpoints.
"""

import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_db

limiter = Limiter(key_func=get_remote_address)
from app.schemas.import_file import (
    ImportUploadResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    ImportLogResponse,
    SavedFormatResponse,
    SavedFormatListResponse,
    SavedFormatMatch,
)
from app.services import import_service
from app.models.learned_format import LearnedFormat, FileType
from app.models.account import Account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_ROWS = 100000  # Maximum rows per import


@router.post("/upload", response_model=ImportUploadResponse)
@limiter.limit("10/minute")
async def upload_file(
    request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Upload a file for import with AI format detection"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_extensions = [".csv", ".ofx", ".qfx"]
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        chunks = []
        total_size = 0
        while chunk := await file.read(8192):
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit",
                )
            chunks.append(chunk)
        content = b"".join(chunks)

        file_path, import_id = import_service.save_upload(content, file.filename)
        return await import_service.get_preview_with_ai(
            db, file_path, import_id, file.filename
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@router.post("/{import_id}/confirm", response_model=ImportStatusResponse)
@limiter.limit("5/minute")
async def confirm_import(
    request: Request,
    import_id: str,
    confirm_request: ImportConfirmRequest,
    db: Session = Depends(get_db),
):
    """Confirm and process import with AI categorization"""
    try:
        return await import_service.process_import_with_ai(
            db, import_id, confirm_request
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Import confirm error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process import")


@router.get("/{import_id}/status", response_model=ImportStatusResponse)
def get_import_status(import_id: str, db: Session = Depends(get_db)):
    """Get status of an import"""
    try:
        return import_service.get_import_status(db, import_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history", response_model=list[ImportLogResponse])
def get_import_history(limit: int = 20, db: Session = Depends(get_db)):
    """Get import history"""
    logs = import_service.get_import_history(db, limit)
    return [ImportLogResponse.model_validate(log) for log in logs]


@router.get("/formats", response_model=SavedFormatListResponse)
def list_formats(db: Session = Depends(get_db)):
    """List all saved import formats"""
    formats = db.query(LearnedFormat).order_by(LearnedFormat.created_at.desc()).all()

    items = []
    for fmt in formats:
        account_name = None
        if fmt.account_id:
            account = db.query(Account).filter(Account.id == fmt.account_id).first()
            account_name = account.name if account else None

        items.append(
            SavedFormatResponse(
                id=str(fmt.id),
                name=fmt.name,
                fingerprint=fmt.fingerprint,
                file_type=fmt.file_type.value
                if hasattr(fmt.file_type, "value")
                else fmt.file_type,
                column_mapping=fmt.column_mapping,
                date_format=fmt.date_format,
                amount_style=fmt.amount_style.value
                if hasattr(fmt.amount_style, "value")
                else fmt.amount_style,
                account_id=str(fmt.account_id) if fmt.account_id else None,
                account_name=account_name,
                created_at=fmt.created_at,
            )
        )

    return SavedFormatListResponse(items=items, total=len(items))


@router.get("/formats/match", response_model=SavedFormatMatch)
def match_format(fingerprint: str = Query(...), db: Session = Depends(get_db)):
    """Find a saved format matching a header fingerprint"""
    fmt = (
        db.query(LearnedFormat).filter(LearnedFormat.fingerprint == fingerprint).first()
    )

    if not fmt:
        raise HTTPException(status_code=404, detail="No matching format found")

    account_name = None
    if fmt.account_id:
        account = db.query(Account).filter(Account.id == fmt.account_id).first()
        account_name = account.name if account else None

    return SavedFormatMatch(
        format_id=str(fmt.id),
        name=fmt.name,
        account_id=str(fmt.account_id) if fmt.account_id else None,
        account_name=account_name,
        column_mapping=fmt.column_mapping,
        date_format=fmt.date_format,
        amount_style=fmt.amount_style.value
        if hasattr(fmt.amount_style, "value")
        else fmt.amount_style,
    )


@router.post("/formats", response_model=SavedFormatResponse)
def save_format(
    name: str,
    fingerprint: str,
    file_type: str,
    column_mapping: dict,
    date_format: str,
    amount_style: str,
    account_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Save a new import format"""
    from app.models.learned_format import FileType, AmountStyle

    try:
        ft = FileType(file_type)
        as_ = AmountStyle(amount_style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")

    existing = (
        db.query(LearnedFormat)
        .filter(
            LearnedFormat.fingerprint == fingerprint,
            LearnedFormat.account_id == account_id,
        )
        .first()
    )

    if existing:
        existing.name = name
        existing.column_mapping = column_mapping
        existing.date_format = date_format
        existing.amount_style = as_
        db.commit()
        db.refresh(existing)
        fmt = existing
    else:
        fmt = LearnedFormat(
            name=name,
            fingerprint=fingerprint,
            file_type=ft,
            column_mapping=column_mapping,
            date_format=date_format,
            amount_style=as_,
            account_id=account_id,
        )
        db.add(fmt)
        db.commit()
        db.refresh(fmt)

    account_name = None
    if fmt.account_id:
        account = db.query(Account).filter(Account.id == fmt.account_id).first()
        account_name = account.name if account else None

    return SavedFormatResponse(
        id=str(fmt.id),
        name=fmt.name,
        fingerprint=fmt.fingerprint,
        file_type=fmt.file_type.value,
        column_mapping=fmt.column_mapping,
        date_format=fmt.date_format,
        amount_style=fmt.amount_style.value,
        account_id=str(fmt.account_id) if fmt.account_id else None,
        account_name=account_name,
        created_at=fmt.created_at,
    )


@router.delete("/formats/{format_id}")
def delete_format(format_id: str, db: Session = Depends(get_db)):
    """Delete a saved format"""
    fmt = db.query(LearnedFormat).filter(LearnedFormat.id == format_id).first()
    if not fmt:
        raise HTTPException(status_code=404, detail="Format not found")

    db.delete(fmt)
    db.commit()
    return {"status": "deleted"}
