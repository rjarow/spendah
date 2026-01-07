"""
Import service for file uploads and processing.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.transaction import Transaction
from app.models.import_log import ImportLog
from app.models.account import Account
from app.schemas.import_file import (
    ImportUploadResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    ImportStatus,
)
from app.parsers.csv_parser import CSVParser
from app.parsers.ofx_parser import OFXParser
from app.services.deduplication_service import generate_transaction_hash, is_duplicate
from app.services.ai_service import detect_csv_format, clean_merchant_name, categorize_transaction

import asyncio

PENDING_IMPORTS: Dict[str, Dict[str, Any]] = {}


def get_parser(file_path: Path):
    """Get appropriate parser for file type"""
    parsers = [CSVParser(), OFXParser()]
    for parser in parsers:
        if parser.can_parse(file_path):
            return parser
    return None


def save_upload(file_content: bytes, filename: str):
    """Save uploaded file and return path and import_id"""
    import_id = str(uuid.uuid4())

    inbox_path = Path(settings.import_inbox_path)
    inbox_path.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{import_id}_{filename}"
    file_path = inbox_path / safe_filename

    with open(file_path, 'wb') as f:
        f.write(file_content)

    return file_path, import_id


def get_preview(file_path: Path, import_id: str, filename: str) -> ImportUploadResponse:
    """Get file preview for confirmation"""
    parser = get_parser(file_path)
    if not parser:
        raise ValueError(f"No parser available for file type: {file_path.suffix}")

    headers, preview_rows = parser.get_preview(file_path)

    if isinstance(parser, CSVParser):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            row_count = sum(1 for _ in f) - 1
    else:
        with open(file_path, 'rb') as f:
            from ofxparse import OfxParser
            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)

    PENDING_IMPORTS[import_id] = {
        'file_path': str(file_path),
        'filename': filename,
        'parser_type': type(parser).__name__
    }

    return ImportUploadResponse(
        import_id=import_id,
        filename=filename,
        row_count=row_count,
        headers=headers,
        preview_rows=preview_rows
    )


async def get_preview_with_ai(
    file_path: Path,
    import_id: str,
    filename: str
) -> ImportUploadResponse:
    """Get file preview with AI-detected column mapping"""
    parser = get_parser(file_path)
    if not parser:
        raise ValueError(f"No parser available for file type: {file_path.suffix}")

    headers, preview_rows = parser.get_preview(file_path)

    detected_format = None
    if isinstance(parser, CSVParser):
        detected_format = await detect_csv_format(headers, preview_rows)

    if isinstance(parser, CSVParser):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            row_count = sum(1 for _ in f) - 1
    else:
        with open(file_path, 'rb') as f:
            from ofxparse import OfxParser
            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)

    PENDING_IMPORTS[import_id] = {
        'file_path': str(file_path),
        'filename': filename,
        'parser_type': type(parser).__name__,
        'detected_format': detected_format
    }

    return ImportUploadResponse(
        import_id=import_id,
        filename=filename,
        row_count=row_count,
        headers=headers,
        preview_rows=preview_rows,
        detected_format=detected_format
    )


def process_import(
    db: Session,
    import_id: str,
    request: ImportConfirmRequest
) -> ImportStatusResponse:

    if import_id not in PENDING_IMPORTS:
        raise ValueError(f"Import {import_id} not found or expired")

    pending = PENDING_IMPORTS[import_id]
    file_path = Path(pending['file_path'])
    filename = pending['filename']

    import_log = ImportLog(
        id=import_id,
        filename=filename,
        account_id=request.account_id,
        status=ImportStatus.PROCESSING
    )
    db.add(import_log)
    db.commit()

    try:
        parser = get_parser(file_path)

        column_mapping = {
            'date_col': request.column_mapping.date_col,
            'amount_col': request.column_mapping.amount_col,
            'description_col': request.column_mapping.description_col,
            'debit_col': request.column_mapping.debit_col,
            'credit_col': request.column_mapping.credit_col,
        }

        transactions = parser.parse(file_path, column_mapping, request.date_format)

        imported = 0
        skipped = 0
        errors = []

        for txn_data in transactions:
            try:
                txn_hash = generate_transaction_hash(
                    txn_data['date'],
                    txn_data['amount'],
                    txn_data['raw_description'],
                    request.account_id
                )

                if is_duplicate(db, txn_hash):
                    skipped += 1
                    continue

                transaction = Transaction(
                    id=str(uuid.uuid4()),
                    hash=txn_hash,
                    date=txn_data['date'],
                    amount=txn_data['amount'],
                    raw_description=txn_data['raw_description'],
                    account_id=request.account_id,
                    ai_categorized=False
                )
                db.add(transaction)
                imported += 1

            except Exception as e:
                errors.append(str(e))

        db.commit()

        import_log.status = ImportStatus.COMPLETED
        import_log.transactions_imported = imported
        import_log.transactions_skipped = skipped
        if errors:
            import_log.error_message = "; ".join(errors[:10])
        db.commit()

        processed_path = Path(settings.import_processed_path)
        processed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(processed_path / file_path.name))

        del PENDING_IMPORTS[import_id]

        return ImportStatusResponse(
            import_id=import_id,
            status=ImportStatus.COMPLETED,
            filename=filename,
            transactions_imported=imported,
            transactions_skipped=skipped,
            errors=errors
        )

    except Exception as e:
        import_log.status = ImportStatus.FAILED
        import_log.error_message = str(e)
        db.commit()

        failed_path = Path(settings.import_failed_path)
        failed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(failed_path / file_path.name))

        if import_id in PENDING_IMPORTS:
            del PENDING_IMPORTS[import_id]

        raise


async def process_import_with_ai(
    db: Session,
    import_id: str,
    request: ImportConfirmRequest
) -> ImportStatusResponse:

    if import_id not in PENDING_IMPORTS:
        raise ValueError(f"Import {import_id} not found or expired")

    pending = PENDING_IMPORTS[import_id]
    file_path = Path(pending['file_path'])
    filename = pending['filename']

    account = db.query(Account).filter(Account.id == request.account_id).first()
    account_type = account.type if account else "bank"

    import_log = ImportLog(
        id=import_id,
        filename=filename,
        account_id=request.account_id,
        status=ImportStatus.PROCESSING
    )
    db.add(import_log)
    db.commit()

    try:
        parser = get_parser(file_path)

        column_mapping = {
            'date_col': request.column_mapping.date_col,
            'amount_col': request.column_mapping.amount_col,
            'description_col': request.column_mapping.description_col,
            'debit_col': request.column_mapping.debit_col,
            'credit_col': request.column_mapping.credit_col,
        }

        transactions_data = parser.parse(file_path, column_mapping, request.date_format)

        imported = 0
        skipped = 0
        errors = []

        for txn_data in transactions_data:
            try:
                txn_hash = generate_transaction_hash(
                    txn_data['date'],
                    txn_data['amount'],
                    txn_data['raw_description'],
                    request.account_id
                )

                if is_duplicate(db, txn_hash):
                    skipped += 1
                    continue

                clean_merchant = await clean_merchant_name(txn_data['raw_description'])

                category_result = await categorize_transaction(
                    db=db,
                    clean_merchant=clean_merchant,
                    raw_description=txn_data['raw_description'],
                    amount=float(txn_data['amount']),
                    date=str(txn_data['date']),
                    account_type=account_type
                )

                category_id = None
                ai_categorized = False
                if category_result and category_result.get('confidence', 0) > 0.5:
                    category_id = category_result.get('category_id')
                    ai_categorized = True

                transaction = Transaction(
                    id=str(uuid.uuid4()),
                    hash=txn_hash,
                    date=txn_data['date'],
                    amount=txn_data['amount'],
                    raw_description=txn_data['raw_description'],
                    clean_merchant=clean_merchant,
                    category_id=category_id,
                    account_id=request.account_id,
                    ai_categorized=ai_categorized
                )
                db.add(transaction)
                imported += 1

            except Exception as e:
                errors.append(str(e))

        db.commit()

        import_log.status = ImportStatus.COMPLETED
        import_log.transactions_imported = imported
        import_log.transactions_skipped = skipped
        if errors:
            import_log.error_message = "; ".join(errors[:10])
        db.commit()

        processed_path = Path(settings.import_processed_path)
        processed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(processed_path / file_path.name))

        del PENDING_IMPORTS[import_id]

        return ImportStatusResponse(
            import_id=import_id,
            status=ImportStatus.COMPLETED,
            filename=filename,
            transactions_imported=imported,
            transactions_skipped=skipped,
            errors=errors
        )

    except Exception as e:
        import_log.status = ImportStatus.FAILED
        import_log.error_message = str(e)
        db.commit()

        failed_path = Path(settings.import_failed_path)
        failed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(failed_path / file_path.name))

        if import_id in PENDING_IMPORTS:
            del PENDING_IMPORTS[import_id]

        raise


def get_import_status(db: Session, import_id: str) -> ImportStatusResponse:
    """Get status of an import"""
    import_log = db.query(ImportLog).filter(ImportLog.id == import_id).first()
    if not import_log:
        raise ValueError(f"Import {import_id} not found")

    return ImportStatusResponse(
        import_id=import_log.id,
        status=import_log.status,
        filename=import_log.filename,
        transactions_imported=import_log.transactions_imported or 0,
        transactions_skipped=import_log.transactions_skipped or 0,
        errors=[import_log.error_message] if import_log.error_message else []
    )


def get_import_history(db: Session, limit: int = 20):
    """Get recent import history"""
    return db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()
