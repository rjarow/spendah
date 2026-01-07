from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import json

from app.ai.client import get_ai_client
from app.ai.prompts import (
    FORMAT_DETECTION_SYSTEM, FORMAT_DETECTION_USER,
    CATEGORIZATION_SYSTEM, CATEGORIZATION_USER,
    MERCHANT_CLEANING_SYSTEM, MERCHANT_CLEANING_USER
)
from app.models.category import Category
from app.models.user_correction import UserCorrection
from app.config import settings


async def detect_csv_format(
    headers: List[str],
    sample_rows: List[List[str]]
) -> Optional[Dict[str, Any]]:
    if not settings.ai_detect_format:
        return None

    client = get_ai_client()

    rows_str = "\n".join([", ".join(row) for row in sample_rows])

    user_prompt = FORMAT_DETECTION_USER.format(
        headers=", ".join(headers),
        sample_rows=rows_str
    )

    try:
        result = await client.complete_json(
            system_prompt=FORMAT_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=500
        )
        return result
    except Exception as e:
        print(f"Format detection failed: {e}")
        return None


async def clean_merchant_name(raw_description: str) -> Optional[str]:
    if not settings.ai_clean_merchants:
        return None

    client = get_ai_client()

    user_prompt = MERCHANT_CLEANING_USER.format(
        raw_description=raw_description
    )

    try:
        result = await client.complete(
            system_prompt=MERCHANT_CLEANING_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=100
        )
        return result.strip()
    except Exception as e:
        print(f"Merchant cleaning failed: {e}")
        return None


async def categorize_transaction(
    db: Session,
    clean_merchant: Optional[str],
    raw_description: str,
    amount: float,
    date: str,
    account_type: str = "bank"
) -> Optional[Dict[str, Any]]:
    if not settings.ai_auto_categorize:
        return None

    client = get_ai_client()

    categories = db.query(Category).all()
    categories_json = json.dumps([
        {"id": str(c.id), "name": c.name, "parent_id": str(c.parent_id) if c.parent_id else None}
        for c in categories
    ], indent=2)

    corrections = db.query(UserCorrection).order_by(
        UserCorrection.created_at.desc()
    ).limit(20).all()

    if corrections:
        corrections_text = "\n".join([
            f"- \"{c.raw_description}\" → Category: {c.category_id}"
            for c in corrections
        ])
    else:
        corrections_text = "No previous corrections yet."

    system_prompt = CATEGORIZATION_SYSTEM.format(
        categories_json=categories_json,
        user_corrections=corrections_text
    )

    user_prompt = CATEGORIZATION_USER.format(
        clean_merchant=clean_merchant or raw_description,
        raw_description=raw_description,
        amount=abs(amount),
        date=date,
        account_type=account_type
    )

    try:
        result = await client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=200
        )
        return result
    except Exception as e:
        print(f"Categorization failed: {e}")
        return None


async def batch_clean_merchants(descriptions: List[str]) -> List[Optional[str]]:
    results = []
    for desc in descriptions:
        cleaned = await clean_merchant_name(desc)
        results.append(cleaned)
    return results


async def batch_categorize(
    db: Session,
    transactions: List[Dict[str, Any]]
) -> List[Optional[Dict[str, Any]]]:
    results = []
    for txn in transactions:
        result = await categorize_transaction(
            db=db,
            clean_merchant=txn.get('clean_merchant'),
            raw_description=txn.get('raw_description', ''),
            amount=float(txn.get('amount', 0)),
            date=str(txn.get('date', '')),
            account_type=txn.get('account_type', 'bank')
        )
        results.append(result)
    return results
