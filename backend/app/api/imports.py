"""
Import API endpoints.
"""

import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.import_file import (
    ImportUploadResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    ImportLogResponse,
)
from app.services import import_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_ROWS = 100000  # Maximum rows per import


@router.post("/upload", response_model=ImportUploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

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
async def confirm_import(
    import_id: str, request: ImportConfirmRequest, db: Session = Depends(get_db)
):
    """Confirm and process import with AI categorization"""
    try:
        return await import_service.process_import_with_ai(db, import_id, request)
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
