"""
AI service for categorization, merchant cleaning, and format detection.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import json
import logging

from app.ai.client import get_ai_client_with_db
from app.ai.prompts import (
    FORMAT_DETECTION_SYSTEM,
    FORMAT_DETECTION_USER,
    CATEGORIZATION_SYSTEM,
    CATEGORIZATION_USER,
    MERCHANT_CLEANING_SYSTEM,
    MERCHANT_CLEANING_USER,
)
from app.ai.sanitization import sanitize_merchant_name, sanitize_description
from app.models.category import Category
from app.models.user_correction import UserCorrection
from app.config import settings
from app.ai.prompts.format_detection import redact_sample_rows

logger = logging.getLogger(__name__)


async def detect_csv_format(
    db: Session, headers: List[str], sample_rows: List[List[str]]
) -> Optional[Dict[str, Any]]:
    if not settings.ai_detect_format:
        return None

    client = get_ai_client_with_db(db, task="format_detect")

    redacted_headers, redacted_rows = redact_sample_rows(headers, sample_rows)
    rows_str = "\n".join([", ".join(row) for row in redacted_rows])

    user_prompt = FORMAT_DETECTION_USER.format(
        headers=", ".join(redacted_headers), sample_rows=rows_str
    )

    try:
        result = await client.complete_json(
            system_prompt=FORMAT_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=500,
        )
        return result
    except Exception as e:
        logger.warning(f"Format detection failed: {e}")
        return None


async def clean_merchant_name(db: Session, raw_description: str) -> Optional[str]:
    if not settings.ai_clean_merchants:
        return None

    client = get_ai_client_with_db(db, task="merchant_clean")

    safe_description = sanitize_description(raw_description)
    user_prompt = MERCHANT_CLEANING_USER.format(raw_description=safe_description)

    try:
        result = await client.complete(
            system_prompt=MERCHANT_CLEANING_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=100,
        )
        return result.strip()
    except Exception as e:
        logger.warning(f"Merchant cleaning failed: {e}")
        return None


async def categorize_transaction_with_context(
    db: Session,
    clean_merchant: Optional[str],
    raw_description: str,
    amount: float,
    date: str,
    account_type: str = "bank",
    categories: Optional[List[Category]] = None,
    corrections: Optional[List[UserCorrection]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Categorize a transaction using pre-fetched categories and corrections.
    This avoids N queries per transaction during bulk import.
    """
    if not settings.ai_auto_categorize:
        return None

    client = get_ai_client_with_db(db, task="categorize")

    if categories is None:
        categories = db.query(Category).all()

    categories_json = json.dumps(
        [
            {
                "id": str(c.id),
                "name": c.name,
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "hint": c.llm_prompt,
            }
            for c in categories
        ],
        indent=2,
    )

    if corrections is None:
        corrections = (
            db.query(UserCorrection)
            .order_by(UserCorrection.created_at.desc())
            .limit(20)
            .all()
        )

    if corrections:
        corrections_text = "\n".join(
            [
                f'- "{c.raw_description}" -> Category: {c.category_id}'
                for c in corrections
            ]
        )
    else:
        corrections_text = "No previous corrections yet."

    system_prompt = CATEGORIZATION_SYSTEM.format(
        categories_json=categories_json, user_corrections=corrections_text
    )

    safe_merchant = sanitize_merchant_name(clean_merchant or raw_description)
    safe_description = sanitize_description(raw_description)

    user_prompt = CATEGORIZATION_USER.format(
        clean_merchant=safe_merchant,
        raw_description=safe_description,
        amount=abs(amount),
        date=date,
        account_type=account_type,
    )

    try:
        result = await client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=200,
        )
        return result
    except Exception as e:
        logger.warning(f"Categorization failed: {e}")
        return None
