"""
Import service for file uploads and processing.

Optimized version with:
- Batch deduplication check (single query)
- Pre-fetched categories and corrections
- Pre-fetched alert settings
- Parallel AI calls with asyncio.gather
- Consolidated process_import function
- Proper logging instead of print()
"""

import os
import re
import uuid
import shutil
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.transaction import Transaction
from app.models.import_log import ImportLog
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.user_correction import UserCorrection
from app.schemas.import_file import (
    ImportUploadResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    ImportStatus,
)
from app.parsers.csv_parser import CSVParser
from app.parsers.ofx_parser import OFXParser
from app.services.deduplication_service import (
    generate_transaction_hash,
    get_existing_hashes,
)
from app.services.ai_service import (
    detect_csv_format,
    clean_merchant_name,
    categorize_transaction_with_context,
)


def get_or_create_account(
    db: Session, account_name: str, account_type: str = "checking"
) -> Account:
    """Get existing account by name or create a new one."""
    account = db.query(Account).filter(Account.name == account_name).first()
    if account:
        return account

    try:
        acc_type = AccountType(account_type)
    except ValueError:
        acc_type = AccountType.checking

    account = Account(
        id=str(uuid.uuid4()),
        name=account_name,
        account_type=acc_type,
        is_active=True,
    )
    db.add(account)
    db.flush()
    logger.info(f"Created new account: {account_name} (type: {account_type})")
    return account


from app.services.alerts_service import analyze_transaction_for_alerts_with_settings
from app.services.budget_alerts import check_all_budget_alerts

logger = logging.getLogger(__name__)

PENDING_IMPORTS: Dict[str, Dict[str, Any]] = {}

MAX_ROWS = 100000  # Maximum rows per import


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and remove dangerous characters."""
    name = os.path.basename(filename)
    safe_name = re.sub(r"[^\w\-_\.]", "_", name)
    safe_name = re.sub(r"_+", "_", safe_name)
    safe_name = safe_name.strip("_")
    if not safe_name or safe_name.startswith("."):
        safe_name = "upload"
    max_len = 200
    if len(safe_name) > max_len:
        name_part = safe_name[: max_len - 10]
        ext_part = safe_name[-10:] if "." in safe_name[-10:] else ""
        safe_name = name_part + ext_part
    return safe_name


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

    safe_name = sanitize_filename(filename)
    safe_filename = f"{import_id}_{safe_name}"
    file_path = inbox_path / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path, import_id


def get_preview(file_path: Path, import_id: str, filename: str) -> ImportUploadResponse:
    """Get file preview for confirmation"""
    parser = get_parser(file_path)
    if not parser:
        raise ValueError(f"No parser available for file type: {file_path.suffix}")

    headers, preview_rows = parser.get_preview(file_path)

    row_count = 0
    if isinstance(parser, CSVParser):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            row_count = sum(1 for _ in f) - 1
    else:
        with open(file_path, "rb") as f:
            from ofxparse import OfxParser

            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)

    PENDING_IMPORTS[import_id] = {
        "file_path": str(file_path),
        "filename": filename,
        "parser_type": type(parser).__name__,
    }

    return ImportUploadResponse(
        import_id=import_id,
        filename=filename,
        row_count=row_count,
        headers=headers,
        preview_rows=preview_rows,
    )


async def get_preview_with_ai(
    db: Session, file_path: Path, import_id: str, filename: str
) -> ImportUploadResponse:
    """Get file preview with AI-detected column mapping"""
    parser = get_parser(file_path)
    if not parser:
        raise ValueError(f"No parser available for file type: {file_path.suffix}")

    headers, preview_rows = parser.get_preview(file_path)

    detected_format = None
    balance = None
    row_count = 0

    if isinstance(parser, CSVParser):
        detected_format = await detect_csv_format(db, headers, preview_rows)
        with open(file_path, "r", encoding="utf-8-sig") as f:
            row_count = sum(1 for _ in f) - 1
    else:
        balance = parser.extract_balance(file_path)
        with open(file_path, "rb") as f:
            from ofxparse import OfxParser

            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)

    PENDING_IMPORTS[import_id] = {
        "file_path": str(file_path),
        "filename": filename,
        "parser_type": type(parser).__name__,
        "detected_format": detected_format,
        "extracted_balance": float(balance) if balance else None,
    }

    return ImportUploadResponse(
        import_id=import_id,
        filename=filename,
        row_count=row_count if row_count else len(preview_rows),
        headers=headers,
        preview_rows=preview_rows,
        detected_format=detected_format,
        extracted_balance=float(balance) if balance else None,
    )


async def process_import(
    db: Session, import_id: str, request: ImportConfirmRequest, use_ai: bool = True
) -> ImportStatusResponse:
    """
    Process an import with optional AI categorization.

    Supports two modes:
    1. Single account: account_id provided, all transactions go to that account
    2. Multi-account: account_col provided, auto-create accounts from CSV

    Optimizations:
    - Batch deduplication check (single query)
    - Pre-fetched categories and corrections
    - Pre-fetched alert settings
    - Parallel AI calls with asyncio.gather
    """
    if import_id not in PENDING_IMPORTS:
        raise ValueError(f"Import {import_id} not found or expired")

    pending = PENDING_IMPORTS[import_id]
    file_path = Path(pending["file_path"])
    filename = pending["filename"]

    has_account_col = request.column_mapping.account_col is not None
    multi_account_mode = has_account_col and request.auto_create_accounts

    if not multi_account_mode and not request.account_id:
        raise ValueError("account_id is required when not using multi-account import")

    default_account = None
    if request.account_id:
        default_account = (
            db.query(Account).filter(Account.id == request.account_id).first()
        )
        if not default_account:
            raise ValueError(f"Account {request.account_id} not found")

    import_log = ImportLog(
        id=import_id,
        filename=filename,
        account_id=request.account_id,
        status=ImportStatus.PROCESSING,
    )
    db.add(import_log)
    db.commit()

    try:
        parser = get_parser(file_path)

        column_mapping = {
            "date_col": request.column_mapping.date_col,
            "amount_col": request.column_mapping.amount_col,
            "description_col": request.column_mapping.description_col,
            "debit_col": request.column_mapping.debit_col,
            "credit_col": request.column_mapping.credit_col,
            "account_col": request.column_mapping.account_col,
        }

        transactions_data = parser.parse(file_path, column_mapping, request.date_format)

        if len(transactions_data) > MAX_ROWS:
            logger.warning(
                f"Import has {len(transactions_data)} rows, limiting to {MAX_ROWS}"
            )
            transactions_data = transactions_data[:MAX_ROWS]

        account_cache: Dict[str, Account] = {}
        if multi_account_mode:
            unique_account_names = set(
                txn.get("account_name", "Unknown Account")
                for txn in transactions_data
                if txn.get("account_name")
            )
            for name in unique_account_names:
                account_cache[name] = get_or_create_account(
                    db, name, request.default_account_type
                )
            db.flush()
        elif default_account:
            account_cache["default"] = default_account

        for txn_data in transactions_data:
            if multi_account_mode:
                account_name = txn_data.get("account_name", "Unknown Account")
                account = account_cache.get(account_name)
                if not account:
                    account = get_or_create_account(
                        db, account_name, request.default_account_type
                    )
                    account_cache[account_name] = account
                txn_data["_account_id"] = account.id
                txn_data["_account_type"] = account.account_type.value
            else:
                txn_data["_account_id"] = request.account_id
                txn_data["_account_type"] = (
                    default_account.account_type.value
                    if default_account
                    else "checking"
                )

            txn_hash = generate_transaction_hash(
                txn_data["date"],
                txn_data["amount"],
                txn_data["raw_description"],
                txn_data["_account_id"],
            )
            txn_data["_hash"] = txn_hash

        all_hashes = [txn["_hash"] for txn in transactions_data]
        existing_hashes = get_existing_hashes(db, all_hashes)
        logger.info(
            f"Batch dedup: {len(existing_hashes)} of {len(all_hashes)} already exist"
        )

        categories = None
        corrections = None
        alert_settings = None

        if use_ai:
            categories = db.query(Category).all()
            corrections = (
                db.query(UserCorrection)
                .order_by(UserCorrection.created_at.desc())
                .limit(20)
                .all()
            )
            logger.debug(
                f"Pre-fetched {len(categories)} categories and {len(corrections)} corrections"
            )

        from app.models.alert import AlertSettings

        alert_settings = db.query(AlertSettings).first()

        imported = 0
        skipped = 0
        errors = []
        transactions_to_alert = []

        if use_ai and settings.ai_auto_categorize:
            new_txns = [
                t for t in transactions_data if t["_hash"] not in existing_hashes
            ]

            if new_txns:
                unique_descriptions = list(set(t["raw_description"] for t in new_txns))
                merchant_tasks = [
                    clean_merchant_name(db, desc) for desc in unique_descriptions
                ]
                clean_merchants = await asyncio.gather(
                    *merchant_tasks, return_exceptions=True
                )

                merchant_map = {}
                for desc, result in zip(unique_descriptions, clean_merchants):
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Merchant cleaning failed for {desc[:30]}: {result}"
                        )
                        merchant_map[desc] = None
                    else:
                        merchant_map[desc] = result

                categorize_tasks = []
                for txn_data in new_txns:
                    clean_merchant = merchant_map.get(txn_data["raw_description"])
                    categorize_tasks.append(
                        categorize_transaction_with_context(
                            db=db,
                            clean_merchant=clean_merchant,
                            raw_description=txn_data["raw_description"],
                            amount=float(txn_data["amount"]),
                            date=str(txn_data["date"]),
                            account_type=txn_data["_account_type"],
                            categories=categories,
                            corrections=corrections,
                        )
                    )

                category_results = await asyncio.gather(
                    *categorize_tasks, return_exceptions=True
                )

                for txn_data, cat_result in zip(new_txns, category_results):
                    txn_hash = txn_data["_hash"]

                    if txn_hash in existing_hashes:
                        skipped += 1
                        continue

                    try:
                        clean_merchant = merchant_map.get(txn_data["raw_description"])

                        category_id = None
                        ai_categorized = False
                        if cat_result and not isinstance(cat_result, Exception):
                            if cat_result.get("confidence", 0) > 0.5:
                                category_id = cat_result.get("category_id")
                                ai_categorized = True
                        elif isinstance(cat_result, Exception):
                            logger.warning(f"Categorization failed: {cat_result}")

                        transaction = Transaction(
                            id=str(uuid.uuid4()),
                            hash=txn_hash,
                            date=txn_data["date"],
                            amount=txn_data["amount"],
                            raw_description=txn_data["raw_description"],
                            clean_merchant=clean_merchant,
                            category_id=category_id,
                            account_id=txn_data["_account_id"],
                            ai_categorized=ai_categorized,
                        )
                        db.add(transaction)
                        transactions_to_alert.append(transaction)
                        imported += 1

                    except Exception as e:
                        logger.error(f"Error creating transaction: {e}")
                        errors.append(str(e))
            else:
                skipped = len(existing_hashes)
        else:
            for txn_data in transactions_data:
                txn_hash = txn_data["_hash"]

                if txn_hash in existing_hashes:
                    skipped += 1
                    continue

                try:
                    transaction = Transaction(
                        id=str(uuid.uuid4()),
                        hash=txn_hash,
                        date=txn_data["date"],
                        amount=txn_data["amount"],
                        raw_description=txn_data["raw_description"],
                        account_id=txn_data["_account_id"],
                        ai_categorized=False,
                    )
                    db.add(transaction)
                    transactions_to_alert.append(transaction)
                    imported += 1
                except Exception as e:
                    logger.error(f"Error creating transaction: {e}")
                    errors.append(str(e))

        db.commit()

        for transaction in transactions_to_alert:
            try:
                analyze_transaction_for_alerts_with_settings(
                    db, transaction, alert_settings
                )
            except Exception as e:
                logger.warning(
                    f"Alert analysis failed for transaction {transaction.id}: {e}"
                )

        db.commit()

        if (
            not multi_account_mode
            and request.update_balance
            and request.new_balance is not None
            and request.account_id
        ):
            account = db.query(Account).filter(Account.id == request.account_id).first()
            if account:
                account.current_balance = Decimal(str(request.new_balance))
                account.balance_updated_at = datetime.utcnow()
                db.commit()
                logger.info(
                    f"Updated balance for account {account.name} to {request.new_balance}"
                )

        if multi_account_mode:
            from app.services.balance_inference import (
                calculate_balance_from_transactions,
            )

            for account_id in set(
                txn_data["_account_id"] for txn_data in transactions_data
            ):
                try:
                    balance = calculate_balance_from_transactions(db, account_id)
                    account = db.query(Account).filter(Account.id == account_id).first()
                    if account:
                        account.current_balance = balance
                        account.balance_updated_at = datetime.utcnow()
                        logger.info(f"Calculated balance for {account.name}: {balance}")
                except Exception as e:
                    logger.warning(
                        f"Failed to calculate balance for account {account_id}: {e}"
                    )
            db.commit()
        elif request.account_id:
            from app.services.balance_inference import (
                calculate_balance_from_transactions,
            )

            try:
                balance = calculate_balance_from_transactions(db, request.account_id)
                account = (
                    db.query(Account).filter(Account.id == request.account_id).first()
                )
                if account:
                    account.current_balance = balance
                    account.balance_updated_at = datetime.utcnow()
                    logger.info(f"Calculated balance for {account.name}: {balance}")
            except Exception as e:
                logger.warning(
                    f"Failed to calculate balance for account {request.account_id}: {e}"
                )
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

        try:
            check_all_budget_alerts(db)
        except Exception as e:
            logger.warning(f"Budget alert check failed after import: {e}")

        logger.info(
            f"Import complete: {imported} imported, {skipped} skipped, {len(errors)} errors"
        )

        return ImportStatusResponse(
            import_id=import_id,
            status=ImportStatus.COMPLETED,
            filename=filename,
            transactions_imported=imported,
            transactions_skipped=skipped,
            errors=errors,
        )

    except Exception as e:
        logger.error(f"Import failed: {e}")
        import_log.status = ImportStatus.FAILED
        import_log.error_message = str(e)
        db.commit()

        failed_path = Path(settings.import_failed_path)
        failed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(failed_path / file_path.name))

        if import_id in PENDING_IMPORTS:
            del PENDING_IMPORTS[import_id]

        raise


def process_import_sync(
    db: Session, import_id: str, request: ImportConfirmRequest
) -> ImportStatusResponse:
    """Synchronous wrapper for process_import without AI."""
    return asyncio.run(process_import(db, import_id, request, use_ai=False))


async def process_import_with_ai(
    db: Session, import_id: str, request: ImportConfirmRequest
) -> ImportStatusResponse:
    """Async import with AI - delegates to unified process_import."""
    return await process_import(db, import_id, request, use_ai=True)


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
        errors=[import_log.error_message] if import_log.error_message else [],
    )


async def categorize_new_merchants_bulk(
    merchants: List[str], db: Session
) -> Dict[str, Dict[str, str]]:
    """
    Categorize only NEW merchants in a single AI call.

    Privacy note: Sending merchant names alone (without amounts/dates/patterns)
    is NOT a privacy concern - it reveals nothing about spending behavior.

    Returns: {merchant: {"clean": "...", "category": "...", "subcategory": "..."}}
    """
    from app.services.tokenization_service import TokenizationService
    from app.models.token_map import TokenMap, TokenType
    from app.ai.client import get_ai_client

    token_service = TokenizationService(db)

    unknown_merchants = token_service.get_unknown_merchants(merchants)

    if not unknown_merchants:
        return _get_cached_categorizations(merchants, db)

    client = get_ai_client()

    categories = db.query(Category).all()
    categories_json = json.dumps(
        [
            {
                "id": str(c.id),
                "name": c.name,
                "parent_id": str(c.parent_id) if c.parent_id else None,
            }
            for c in categories
        ],
        indent=2,
    )

    prompt = f"""Categorize these merchant names from bank transactions.

For each merchant, provide:
1. A clean, human-readable name
2. The category and subcategory

Merchants to categorize:
{json.dumps(unknown_merchants, indent=2)}

Available categories:
{categories_json}

Respond with JSON array:
[
  {{"raw": "WHOLEFDS #1234 SAN FRAN", "clean": "Whole Foods", "category": "Food", "subcategory": "Groceries"}},
  ...
]"""

    try:
        result = await client.complete_json(
            system_prompt="You are a financial data expert. Categorize merchant names.",
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=2000,
        )
        categorizations = (
            result if isinstance(result, list) else result.get("merchants", [])
        )

        token_map_result = {}
        for cat in categorizations:
            raw = cat.get("raw")
            token_service.tokenize_merchant(
                raw, category=cat.get("category"), subcategory=cat.get("subcategory")
            )
            token_map_result[raw] = cat

        cached = _get_cached_categorizations(
            [m for m in merchants if m not in unknown_merchants], db
        )
        token_map_result.update(cached)

        return token_map_result
    except Exception as e:
        logger.warning(f"Bulk merchant categorization failed: {e}")
        return _get_cached_categorizations(merchants, db)


def _get_cached_categorizations(
    merchants: List[str], db: Session
) -> Dict[str, Dict[str, str]]:
    """Get categorizations from token map for known merchants."""
    from app.models.token_map import TokenMap, TokenType

    result = {}
    for merchant in merchants:
        normalized = merchant.strip().upper()
        token_map = (
            db.query(TokenMap)
            .filter(
                TokenMap.token_type == TokenType.merchant,
                TokenMap.normalized_value == normalized,
            )
            .first()
        )

        if token_map and token_map.metadata_:
            result[merchant] = {
                "raw": merchant,
                "clean": token_map.original_value,
                "category": token_map.metadata_.get("category"),
                "subcategory": token_map.metadata_.get("subcategory"),
            }

    return result


def get_import_history(db: Session, limit: int = 20):
    """Get recent import history"""
    return db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()
