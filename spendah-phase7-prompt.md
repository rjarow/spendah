# Spendah - Phase 7: Privacy & Tokenization

## Overview

This phase adds a privacy layer that enables cloud AI usage without exposing PII. All existing AI features will continue to work identically, but cloud providers will see only anonymized tokens.

**Key Concepts:**
- Import-time: Structural redaction for format detection, bulk categorization for new merchants only
- Post-import: Full tokenization for all ongoing AI calls (recurring, anomaly, coach)
- Per-provider settings: Local AI (Ollama) can skip tokenization
- Settings persisted in database (like alert_settings)

**Privacy Philosophy:**
- Merchant names alone (without amounts, dates, patterns) are NOT considered PII. Asking "categorize: Whole Foods, Target, Netflix" is equivalent to asking "what category is a grocery store?"
- PII emerges when you COMBINE merchant + amount + date + frequency - that's when spending patterns become identifying
- Therefore: bulk merchant categorization is low-risk, but ongoing AI calls with full transaction context need tokenization

## Progress Tracker

Update this as you complete each step:

- [ ] Step 0: Examine Existing AI Implementation
- [ ] Step 1: Create Token Map Models
- [ ] Step 2: Create Privacy Settings Model
- [ ] Step 3: Create Tokenization Service
- [ ] Step 4: Add Structural Redaction for Format Detection
- [ ] Step 5: Implement Bulk Categorization with Deduplication
- [ ] Step 6: Add Per-Provider Privacy Settings
- [ ] Step 7: Integrate Tokenization with Existing AI Calls
- [ ] Step 8: Create Privacy API Endpoints
- [ ] Step 9: Add Privacy Settings UI
- [ ] Step 10: Add Tests
- [ ] Step 11: Final Testing & Verification

## Files to Create/Modify

**CREATE:**
- `backend/app/models/token_map.py`
- `backend/app/models/privacy_settings.py`
- `backend/app/schemas/privacy.py`
- `backend/app/services/tokenization_service.py`
- `backend/app/api/privacy.py`
- `backend/tests/test_tokenization.py`
- `frontend/src/components/settings/PrivacySettings.tsx`

**MODIFY:**
- `backend/app/models/__init__.py` - Export new models
- `backend/app/ai/client.py` - Wrap calls with tokenization
- `backend/app/ai/prompts/format_detection.py` - Use structural redaction
- `backend/app/services/import_service.py` - Bulk categorization flow
- `backend/app/api/router.py` - Add privacy router
- `backend/app/config.py` - Add privacy defaults
- `frontend/src/lib/api.ts` - Add privacy API functions
- `frontend/src/types/index.ts` - Add privacy types
- `frontend/src/pages/Settings.tsx` - Add privacy section

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `HANDOFF-phase6-complete.md` - Current project state
2. `spendah-spec.md` - Architecture with privacy details

## Known Gotchas (from previous phases)

1. **Account model uses `account_type`** not `type`
2. **Alert model uses `Severity`** not `AlertSeverity`
3. **OpenRouter uses `OPENROUTER_API_KEY`** not `OPENAI_API_KEY`
4. **Always restart after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Step 0: Examine Existing AI Implementation

**CRITICAL: Do this before writing any tokenization code.**

Examine the current AI client and how services call it:

```bash
# Look at the AI client structure
cat backend/app/ai/client.py

# Look at how services call AI
cat backend/app/services/alerts_service.py
cat backend/app/services/recurring_service.py
cat backend/app/services/import_service.py

# Check the prompts structure
ls -la backend/app/ai/prompts/
cat backend/app/ai/prompts/categorization.py
```

**Document your findings:**
1. How does `AIClient.complete()` work? What parameters does it take?
2. How do services pass transaction data to AI calls?
3. Is there a consistent pattern (e.g., `{transactions}` placeholder) or does each service construct prompts differently?

**Adapt Step 7 based on findings:**
- If there's a central `complete()` method all services use → wrap it with tokenization
- If services construct prompts individually → may need to add tokenization at the service level
- If there's an `ai_service.py` → that might be the right place to add the wrapper

---

## Step 1: Create Token Map Models

Create `backend/app/models/token_map.py`:

```python
"""Models for PII tokenization."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum

from app.database import Base


class TokenType(str, Enum):
    """Types of tokens we create."""
    merchant = "merchant"
    account = "account"
    person = "person"


class TokenMap(Base):
    """Maps original PII values to anonymized tokens."""
    __tablename__ = "token_maps"
    
    id = Column(Integer, primary_key=True, index=True)
    token_type = Column(SQLEnum(TokenType), nullable=False, index=True)
    original_value = Column(String(500), nullable=False)  # Original: "Whole Foods Market"
    normalized_value = Column(String(500), nullable=False, index=True)  # Uppercase: "WHOLE FOODS MARKET"
    token = Column(String(50), nullable=False, unique=True, index=True)  # "MERCHANT_042"
    metadata_ = Column("metadata", JSON, nullable=True)  # {"category": "Groceries", "subcategory": "Supermarket"}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class DateShift(Base):
    """Singleton table storing the random date shift value."""
    __tablename__ = "date_shifts"
    
    id = Column(Integer, primary_key=True, default=1)
    shift_days = Column(Integer, nullable=False)  # Random value, e.g., 937
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Step 2: Create Privacy Settings Model

Create `backend/app/models/privacy_settings.py`:

```python
"""Privacy settings model - persisted in database like alert_settings."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class PrivacySettings(Base):
    """
    Privacy settings stored in database.
    Singleton pattern - only one row with id=1.
    Similar to AlertSettings model.
    """
    __tablename__ = "privacy_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    
    # Master toggle
    obfuscation_enabled = Column(Boolean, default=True, nullable=False)
    
    # Per-provider settings
    # Local providers default to OFF (no need to obfuscate)
    ollama_obfuscation = Column(Boolean, default=False, nullable=False)
    
    # Cloud providers default to ON
    openrouter_obfuscation = Column(Boolean, default=True, nullable=False)
    anthropic_obfuscation = Column(Boolean, default=True, nullable=False)
    openai_obfuscation = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


def get_or_create_privacy_settings(db) -> PrivacySettings:
    """Get the singleton privacy settings, creating with defaults if needed."""
    settings = db.query(PrivacySettings).filter(PrivacySettings.id == 1).first()
    if not settings:
        settings = PrivacySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
```

Update `backend/app/models/__init__.py` to export new models:

```python
from app.models.token_map import TokenMap, TokenType, DateShift
from app.models.privacy_settings import PrivacySettings, get_or_create_privacy_settings
```

Create Alembic migration:
```bash
docker compose exec api alembic revision --autogenerate -m "add privacy and token map tables"
docker compose exec api alembic upgrade head
```

**Verify:**
```bash
docker compose exec api python -c "from app.models.token_map import TokenMap, DateShift; from app.models.privacy_settings import PrivacySettings; print('Models loaded')"
```

---

## Step 3: Create Tokenization Service

Create `backend/app/services/tokenization_service.py`:

```python
"""Service for tokenizing PII before AI calls and de-tokenizing responses."""

import re
import random
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.token_map import TokenMap, TokenType, DateShift
from app.models.privacy_settings import get_or_create_privacy_settings


class TokenizationService:
    """
    Handles tokenization and de-tokenization of PII.
    
    Tokens are deterministic and persistent - the same input always produces
    the same token across sessions.
    """
    
    # Patterns for extracting person names from descriptions
    PERSON_PATTERNS = [
        (r'VENMO\s+(?:PAYMENT\s+)?([A-Z][A-Z\s]+)', 'VENMO'),
        (r'ZELLE\s+(?:PAYMENT\s+)?(?:TO\s+|FROM\s+)?([A-Z][A-Z\s]+)', 'ZELLE'),
        (r'PAYPAL\s+\*([A-Z][A-Z\s]+)', 'PAYPAL'),
        (r'CASH\s+APP\s+\*([A-Z][A-Z\s]+)', 'CASH APP'),
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[Tuple[TokenType, str], str] = {}
        self._reverse_cache: Dict[str, str] = {}
        self._load_caches()
        self._date_shift: Optional[int] = None
    
    def _load_caches(self):
        """Load existing token mappings into memory."""
        tokens = self.db.query(TokenMap).all()
        for t in tokens:
            key = (t.token_type, t.normalized_value)
            self._cache[key] = t.token
            self._reverse_cache[t.token] = t.original_value
    
    def _get_date_shift(self) -> int:
        """Get or create the date shift value."""
        if self._date_shift is not None:
            return self._date_shift
        
        shift_record = self.db.query(DateShift).first()
        if shift_record:
            self._date_shift = shift_record.shift_days
        else:
            # Generate random shift between 500-1500 days
            self._date_shift = random.randint(500, 1500)
            shift_record = DateShift(id=1, shift_days=self._date_shift)
            self.db.add(shift_record)
            self.db.commit()
        
        return self._date_shift
    
    def _normalize(self, value: str) -> str:
        """Normalize a value for consistent matching."""
        return value.strip().upper()
    
    def _get_next_token_number(self, token_type: TokenType) -> int:
        """Get the next available token number for a type."""
        count = self.db.query(TokenMap).filter(
            TokenMap.token_type == token_type
        ).count()
        return count + 1
    
    def tokenize_merchant(
        self, 
        merchant: str, 
        category: Optional[str] = None,
        subcategory: Optional[str] = None
    ) -> str:
        """
        Tokenize a merchant name.
        
        Returns: Token like "MERCHANT_042"
        """
        normalized = self._normalize(merchant)
        cache_key = (TokenType.merchant, normalized)
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check database
        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.merchant,
            TokenMap.normalized_value == normalized
        ).first()
        
        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token
        
        # Create new token
        token_num = self._get_next_token_number(TokenType.merchant)
        token = f"MERCHANT_{token_num:04d}"
        
        metadata = {}
        if category:
            metadata["category"] = category
        if subcategory:
            metadata["subcategory"] = subcategory
        
        token_map = TokenMap(
            token_type=TokenType.merchant,
            original_value=merchant,
            normalized_value=normalized,
            token=token,
            metadata_=metadata if metadata else None
        )
        self.db.add(token_map)
        self.db.commit()
        
        self._cache[cache_key] = token
        self._reverse_cache[token] = merchant
        
        return token
    
    def tokenize_account(
        self,
        account_name: str,
        account_type: Optional[str] = None
    ) -> str:
        """Tokenize an account identifier."""
        normalized = self._normalize(account_name)
        cache_key = (TokenType.account, normalized)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.account,
            TokenMap.normalized_value == normalized
        ).first()
        
        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token
        
        token_num = self._get_next_token_number(TokenType.account)
        token = f"ACCOUNT_{token_num:03d}"
        
        metadata = {"account_type": account_type} if account_type else None
        
        token_map = TokenMap(
            token_type=TokenType.account,
            original_value=account_name,
            normalized_value=normalized,
            token=token,
            metadata_=metadata
        )
        self.db.add(token_map)
        self.db.commit()
        
        self._cache[cache_key] = token
        self._reverse_cache[token] = account_name
        
        return token
    
    def tokenize_description(self, description: str) -> str:
        """
        Tokenize person names within a description.
        
        Example: "VENMO JOHN SMITH" -> "VENMO PERSON_001"
        """
        result = description
        
        for pattern, service in self.PERSON_PATTERNS:
            match = re.search(pattern, description.upper())
            if match:
                person_name = match.group(1).strip()
                person_token = self._tokenize_person(person_name)
                # Replace the person name portion
                result = re.sub(
                    pattern, 
                    f"{service} {person_token}", 
                    result, 
                    flags=re.IGNORECASE
                )
        
        return result
    
    def _tokenize_person(self, person_name: str) -> str:
        """Tokenize a person's name."""
        normalized = self._normalize(person_name)
        cache_key = (TokenType.person, normalized)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.person,
            TokenMap.normalized_value == normalized
        ).first()
        
        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token
        
        token_num = self._get_next_token_number(TokenType.person)
        token = f"PERSON_{token_num:03d}"
        
        token_map = TokenMap(
            token_type=TokenType.person,
            original_value=person_name,
            normalized_value=normalized,
            token=token,
            metadata_=None
        )
        self.db.add(token_map)
        self.db.commit()
        
        self._cache[cache_key] = token
        self._reverse_cache[token] = person_name
        
        return token
    
    def shift_date(self, original_date: date) -> date:
        """Shift a date by the installation's random offset."""
        shift = self._get_date_shift()
        return original_date + timedelta(days=shift)
    
    def unshift_date(self, shifted_date: date) -> date:
        """Reverse date shift for display."""
        shift = self._get_date_shift()
        return shifted_date - timedelta(days=shift)
    
    def detokenize(self, text: str) -> str:
        """
        Replace all tokens in text with original values.
        
        Used for displaying AI responses to users.
        """
        result = text
        
        # Find all tokens in the text
        token_pattern = r'(MERCHANT_\d{4}|ACCOUNT_\d{3}|PERSON_\d{3})'
        
        for match in re.finditer(token_pattern, text):
            token = match.group(1)
            if token in self._reverse_cache:
                result = result.replace(token, self._reverse_cache[token])
        
        return result
    
    def tokenize_transaction_for_ai(
        self,
        transaction: Dict[str, Any],
        include_category: bool = True
    ) -> Dict[str, Any]:
        """
        Tokenize a transaction dict for sending to AI.
        
        Input: {"merchant": "Whole Foods", "amount": -187.34, "date": "2024-01-15", ...}
        Output: {"merchant": "MERCHANT_042 [Groceries]", "amount": -187.34, "date": "2026-08-09", ...}
        """
        result = dict(transaction)
        
        # Tokenize merchant
        if "merchant" in result or "clean_merchant" in result:
            merchant = result.get("clean_merchant") or result.get("merchant", "")
            category = result.get("category_name") if include_category else None
            token = self.tokenize_merchant(merchant, category)
            
            if include_category and category:
                result["merchant"] = f"{token} [{category}]"
            else:
                result["merchant"] = token
            
            # Remove raw fields
            result.pop("clean_merchant", None)
            result.pop("raw_description", None)
        
        # Tokenize description if present
        if "description" in result:
            result["description"] = self.tokenize_description(result["description"])
        
        # Shift date
        if "date" in result:
            if isinstance(result["date"], str):
                from datetime import datetime
                d = datetime.fromisoformat(result["date"]).date()
            else:
                d = result["date"]
            result["date"] = self.shift_date(d).isoformat()
        
        # Tokenize account if present
        if "account_name" in result:
            account_type = result.get("account_type")
            result["account"] = self.tokenize_account(result["account_name"], account_type)
            result.pop("account_name", None)
            result.pop("account_type", None)
        
        return result
    
    def get_unknown_merchants(self, merchants: List[str]) -> List[str]:
        """
        Filter to only merchants not yet in token map.
        
        Used for bulk categorization - only send new merchants to AI.
        """
        unknown = []
        for merchant in merchants:
            normalized = self._normalize(merchant)
            cache_key = (TokenType.merchant, normalized)
            if cache_key not in self._cache:
                # Double-check database
                existing = self.db.query(TokenMap).filter(
                    TokenMap.token_type == TokenType.merchant,
                    TokenMap.normalized_value == normalized
                ).first()
                if not existing:
                    unknown.append(merchant)
        
        return unknown
    
    def get_token_stats(self) -> Dict[str, int]:
        """Get counts of each token type."""
        stats = {}
        for token_type in TokenType:
            count = self.db.query(TokenMap).filter(
                TokenMap.token_type == token_type
            ).count()
            stats[token_type.value] = count
        
        # Add date shift info
        shift = self.db.query(DateShift).first()
        stats["date_shift_days"] = shift.shift_days if shift else 0
        
        return stats
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 20
```

---

## Step 4: Add Structural Redaction for Format Detection

Modify `backend/app/ai/prompts/format_detection.py` to support structural redaction:

```python
"""Format detection prompt with structural redaction for privacy."""

import re
from typing import List, Tuple
from datetime import date, timedelta
import random


def redact_sample_rows(
    headers: List[str],
    rows: List[List[str]],
    date_shift_days: int = 937
) -> Tuple[List[str], List[List[str]]]:
    """
    Redact sample rows while preserving structure for format detection.
    
    - Dates: Shifted by random offset
    - Amounts: Replaced with XXX.XX pattern (preserving sign/format)
    - Descriptions: Replaced with REDACTED_MERCHANT_A, B, C...
    - Other text: Replaced with REDACTED
    """
    redacted_rows = []
    merchant_counter = 0
    merchant_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    for row in rows:
        redacted_row = []
        for i, cell in enumerate(row):
            cell_str = str(cell).strip()
            
            # Try to detect and redact appropriately
            redacted = redact_cell(
                cell_str, 
                headers[i] if i < len(headers) else "",
                date_shift_days,
                merchant_labels[merchant_counter % len(merchant_labels)]
            )
            
            # Track if this looks like a merchant column
            if "REDACTED_MERCHANT" in redacted:
                merchant_counter += 1
            
            redacted_row.append(redacted)
        
        redacted_rows.append(redacted_row)
    
    return headers, redacted_rows


def redact_cell(cell: str, header: str, date_shift: int, merchant_label: str) -> str:
    """Redact a single cell based on its content pattern."""
    
    # Empty cell
    if not cell:
        return ""
    
    # Date patterns
    date_patterns = [
        r'^\d{1,2}/\d{1,2}/\d{2,4}$',  # MM/DD/YYYY
        r'^\d{4}-\d{2}-\d{2}$',         # YYYY-MM-DD
        r'^\d{1,2}-\d{1,2}-\d{2,4}$',   # MM-DD-YYYY
    ]
    for pattern in date_patterns:
        if re.match(pattern, cell):
            # Return a shifted fake date in same format
            try:
                fake_date = date.today() + timedelta(days=date_shift)
                if '/' in cell:
                    return fake_date.strftime("%m/%d/%Y")
                else:
                    return fake_date.isoformat()
            except:
                return "XX/XX/XXXX"
    
    # Amount patterns (preserve format but hide value)
    amount_patterns = [
        (r'^-?\$?[\d,]+\.\d{2}$', lambda m: "-XXX.XX" if m.startswith('-') else "XXX.XX"),
        (r'^\([\d,]+\.\d{2}\)$', lambda m: "(XXX.XX)"),  # Parentheses negative
        (r'^-?[\d,]+\.\d{2}$', lambda m: "-XXX.XX" if m.startswith('-') else "XXX.XX"),
    ]
    for pattern, replacer in amount_patterns:
        if re.match(pattern, cell.replace(',', '').replace('$', '')):
            return replacer(cell)
    
    # Header hints for description/merchant columns
    desc_headers = ['description', 'merchant', 'payee', 'memo', 'details', 'name']
    if any(h in header.lower() for h in desc_headers):
        # Check for person payment patterns
        if any(svc in cell.upper() for svc in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP']):
            service = next(s for s in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP'] if s in cell.upper())
            return f"{service} REDACTED_PERSON"
        return f"REDACTED_MERCHANT_{merchant_label}"
    
    # Check if it looks like a merchant/description anyway
    if len(cell) > 10 and not cell.replace('.','').replace(',','').isdigit():
        if any(svc in cell.upper() for svc in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP']):
            service = next(s for s in ['VENMO', 'ZELLE', 'PAYPAL', 'CASH APP'] if s in cell.upper())
            return f"{service} REDACTED_PERSON"
        return f"REDACTED_MERCHANT_{merchant_label}"
    
    # Account numbers (mask all but format)
    if re.match(r'^[\d\-\*]+$', cell) and len(cell) > 4:
        return "****" + cell[-4:] if len(cell) >= 4 else "****"
    
    # Default: keep short values, redact longer ones
    if len(cell) <= 3:
        return cell
    
    return "REDACTED"


# System prompt for format detection (unchanged but now receives redacted data)
FORMAT_DETECTION_SYSTEM = """You are a financial data expert. Analyze CSV file contents and identify column mappings.

The data has been redacted for privacy. Look at the STRUCTURE, not the values:
- Dates: Shown as shifted dates (still in original format)
- Amounts: Shown as XXX.XX (preserving sign and format)
- Descriptions: Shown as REDACTED_MERCHANT_A, REDACTED_MERCHANT_B, etc.
- Person payments: Shown as VENMO REDACTED_PERSON, etc.

Respond with JSON only:
{
  "columns": {
    "date": <column_index or null>,
    "amount": <column_index or null>,
    "description": <column_index or null>,
    "category": <column_index or null>,
    "debit": <column_index or null>,
    "credit": <column_index or null>,
    "balance": <column_index or null>
  },
  "date_format": "<strptime format>",
  "amount_style": "signed" | "separate_columns" | "parentheses_negative",
  "skip_rows": <number of header rows>,
  "confidence": <0.0-1.0>
}"""
```

---

## Step 5: Implement Bulk Categorization with Deduplication

**Note on Privacy:** Sending a list of merchant names alone (without amounts, dates, or patterns) is NOT a significant privacy concern. "Categorize: Whole Foods, Target, Netflix" reveals nothing about your spending habits - it's the same as asking "what category is a grocery store?" The privacy risk comes from combining merchant + amount + date + frequency.

Modify `backend/app/services/import_service.py` to use bulk categorization:

Add this method to the import service (or create a new categorization flow):

```python
async def categorize_new_merchants_bulk(
    self,
    merchants: List[str],
    db: Session
) -> Dict[str, Dict[str, str]]:
    """
    Categorize only NEW merchants in a single AI call.
    
    Privacy note: Sending merchant names alone (without amounts/dates/patterns)
    is NOT a privacy concern - it reveals nothing about spending behavior.
    
    Returns: {merchant: {"clean": "...", "category": "...", "subcategory": "..."}}
    """
    from app.services.tokenization_service import TokenizationService
    
    token_service = TokenizationService(db)
    
    # Filter to only unknown merchants
    unknown_merchants = token_service.get_unknown_merchants(merchants)
    
    if not unknown_merchants:
        # All merchants already known, return from token map
        return self._get_cached_categorizations(merchants, db)
    
    # Single AI call for all unknown merchants
    # Note: This is merchant names ONLY - no amounts, dates, or patterns
    prompt = f"""Categorize these merchant names from bank transactions.

For each merchant, provide:
1. A clean, human-readable name
2. The category and subcategory

Merchants to categorize:
{json.dumps(unknown_merchants, indent=2)}

Available categories:
{json.dumps(self._get_categories_list(db), indent=2)}

Respond with JSON array:
[
  {{"raw": "WHOLEFDS #1234 SAN FRAN", "clean": "Whole Foods", "category": "Food", "subcategory": "Groceries"}},
  ...
]"""

    response = await self.ai_client.complete(prompt)
    categorizations = json.loads(response)
    
    # Store in token map for future use
    result = {}
    for cat in categorizations:
        raw = cat["raw"]
        token_service.tokenize_merchant(
            raw,
            category=cat.get("category"),
            subcategory=cat.get("subcategory")
        )
        result[raw] = cat
    
    # Merge with already-known merchants
    cached = self._get_cached_categorizations(
        [m for m in merchants if m not in unknown_merchants], 
        db
    )
    result.update(cached)
    
    return result


def _get_cached_categorizations(
    self, 
    merchants: List[str], 
    db: Session
) -> Dict[str, Dict[str, str]]:
    """Get categorizations from token map for known merchants."""
    from app.models.token_map import TokenMap, TokenType
    
    result = {}
    for merchant in merchants:
        normalized = merchant.strip().upper()
        token_map = db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.merchant,
            TokenMap.normalized_value == normalized
        ).first()
        
        if token_map and token_map.metadata_:
            result[merchant] = {
                "raw": merchant,
                "clean": token_map.original_value,
                "category": token_map.metadata_.get("category"),
                "subcategory": token_map.metadata_.get("subcategory"),
            }
    
    return result
```

---

## Step 6: Add Per-Provider Privacy Settings

Create `backend/app/schemas/privacy.py`:

```python
"""Schemas for privacy settings."""

from pydantic import BaseModel
from typing import Optional, List, Dict


class ProviderPrivacyConfig(BaseModel):
    """Privacy settings for a specific AI provider."""
    provider: str
    obfuscation_enabled: bool


class PrivacySettingsResponse(BaseModel):
    """Privacy settings response."""
    obfuscation_enabled: bool
    provider_settings: List[ProviderPrivacyConfig]
    
    class Config:
        from_attributes = True


class PrivacySettingsUpdate(BaseModel):
    """Update privacy settings."""
    obfuscation_enabled: Optional[bool] = None
    provider_settings: Optional[List[ProviderPrivacyConfig]] = None


class TokenStats(BaseModel):
    """Statistics about tokenization."""
    merchants: int
    accounts: int
    people: int
    date_shift_days: int


class PrivacyPreview(BaseModel):
    """Preview of tokenized data."""
    original: str
    tokenized: str


class TokenInfo(BaseModel):
    """Info about a single token."""
    token: str
    original: str
    token_type: str
    metadata: Optional[Dict] = None
    created_at: str


class PrivacyStatusResponse(BaseModel):
    """Full privacy status response."""
    obfuscation_enabled: bool
    provider_settings: List[ProviderPrivacyConfig]
    stats: TokenStats
```

Update `backend/app/config.py` to add privacy defaults (used only for initial DB seeding):

```python
# Add to Settings class:
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Privacy defaults (for initial DB seeding only)
    # Actual values stored in privacy_settings table
    privacy_obfuscation_default: bool = True
    privacy_ollama_default: bool = False  # Local = off by default
    privacy_cloud_default: bool = True    # Cloud = on by default
```

---

## Step 7: Integrate Tokenization with Existing AI Calls

**IMPORTANT:** Adapt this based on your findings from Step 0.

The goal is to wrap AI calls with tokenization when:
1. Privacy settings say obfuscation is enabled
2. The current provider has obfuscation enabled
3. We're not doing initial merchant categorization (which is merchant-names-only)

Modify `backend/app/ai/client.py` (adapt based on existing structure):

```python
"""LiteLLM client with privacy-aware tokenization."""

import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.services.tokenization_service import TokenizationService
from app.models.privacy_settings import get_or_create_privacy_settings
from app.config import get_settings


class AIClient:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._tokenizer: Optional[TokenizationService] = None
    
    @property
    def tokenizer(self) -> TokenizationService:
        if self._tokenizer is None:
            self._tokenizer = TokenizationService(self.db)
        return self._tokenizer
    
    def should_obfuscate(self, provider: Optional[str] = None) -> bool:
        """Check if obfuscation is enabled for the current/specified provider."""
        privacy_settings = get_or_create_privacy_settings(self.db)
        
        if not privacy_settings.obfuscation_enabled:
            return False
        
        provider = provider or self.settings.ai_provider
        
        if provider == "ollama":
            return privacy_settings.ollama_obfuscation
        elif provider == "openrouter":
            return privacy_settings.openrouter_obfuscation
        elif provider == "anthropic":
            return privacy_settings.anthropic_obfuscation
        elif provider == "openai":
            return privacy_settings.openai_obfuscation
        
        # Default to obfuscating unknown providers
        return True
    
    def tokenize_transactions(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Tokenize a list of transactions for AI consumption."""
        if not self.should_obfuscate():
            return transactions
        
        return [
            self.tokenizer.tokenize_transaction_for_ai(t) 
            for t in transactions
        ]
    
    def detokenize_response(self, response: str) -> str:
        """De-tokenize AI response for display to user."""
        if not self.should_obfuscate():
            return response
        
        return self.tokenizer.detokenize(response)
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        transactions: Optional[List[Dict]] = None,
        skip_obfuscation: bool = False,
        **kwargs
    ) -> str:
        """
        Send completion request, handling tokenization automatically.
        
        Args:
            prompt: The prompt to send
            system: Optional system prompt
            transactions: Optional transactions to tokenize and include
            skip_obfuscation: If True, skip tokenization (for merchant-only categorization)
            **kwargs: Additional arguments for LiteLLM
        
        Returns:
            De-tokenized response string
        """
        final_prompt = prompt
        
        # Tokenize transactions if provided (unless skipped)
        if transactions and not skip_obfuscation and self.should_obfuscate():
            tokenized = self.tokenize_transactions(transactions)
            final_prompt = prompt.replace(
                "{transactions}", 
                json.dumps(tokenized, indent=2, default=str)
            )
        elif transactions:
            final_prompt = prompt.replace(
                "{transactions}", 
                json.dumps(transactions, indent=2, default=str)
            )
        
        # Make AI call (existing LiteLLM logic - preserve what's already there)
        response = await self._call_litellm(final_prompt, system, **kwargs)
        
        # De-tokenize response (unless skipped)
        if not skip_obfuscation:
            return self.detokenize_response(response)
        return response
    
    # ... keep existing _call_litellm method and other methods ...
```

---

## Step 8: Create Privacy API Endpoints

Create `backend/app/api/privacy.py`:

```python
"""Privacy settings API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.privacy import (
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
    PrivacyStatusResponse,
    PrivacyPreview,
    TokenInfo,
    TokenStats,
    ProviderPrivacyConfig,
)
from app.services.tokenization_service import TokenizationService
from app.models.token_map import TokenMap, TokenType
from app.models.privacy_settings import get_or_create_privacy_settings

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/settings", response_model=PrivacyStatusResponse)
def get_privacy_settings(db: Session = Depends(get_db)):
    """Get current privacy settings and token statistics."""
    settings = get_or_create_privacy_settings(db)
    token_service = TokenizationService(db)
    stats = token_service.get_token_stats()
    
    provider_settings = [
        ProviderPrivacyConfig(provider="ollama", obfuscation_enabled=settings.ollama_obfuscation),
        ProviderPrivacyConfig(provider="openrouter", obfuscation_enabled=settings.openrouter_obfuscation),
        ProviderPrivacyConfig(provider="anthropic", obfuscation_enabled=settings.anthropic_obfuscation),
        ProviderPrivacyConfig(provider="openai", obfuscation_enabled=settings.openai_obfuscation),
    ]
    
    return PrivacyStatusResponse(
        obfuscation_enabled=settings.obfuscation_enabled,
        provider_settings=provider_settings,
        stats=TokenStats(
            merchants=stats.get("merchant", 0),
            accounts=stats.get("account", 0),
            people=stats.get("person", 0),
            date_shift_days=stats.get("date_shift_days", 0),
        )
    )


@router.patch("/settings", response_model=PrivacyStatusResponse)
def update_privacy_settings(
    updates: PrivacySettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update privacy settings."""
    settings = get_or_create_privacy_settings(db)
    
    if updates.obfuscation_enabled is not None:
        settings.obfuscation_enabled = updates.obfuscation_enabled
    
    if updates.provider_settings:
        for ps in updates.provider_settings:
            if ps.provider == "ollama":
                settings.ollama_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "openrouter":
                settings.openrouter_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "anthropic":
                settings.anthropic_obfuscation = ps.obfuscation_enabled
            elif ps.provider == "openai":
                settings.openai_obfuscation = ps.obfuscation_enabled
    
    db.commit()
    db.refresh(settings)
    
    return get_privacy_settings(db)


@router.get("/preview")
def preview_tokenization(
    text: str,
    db: Session = Depends(get_db)
) -> PrivacyPreview:
    """Preview how text would be tokenized."""
    token_service = TokenizationService(db)
    
    # Try tokenizing as merchant
    tokenized = token_service.tokenize_merchant(text)
    
    return PrivacyPreview(
        original=text,
        tokenized=tokenized
    )


@router.get("/tokens", response_model=List[TokenInfo])
def list_tokens(
    token_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List tokens in the token map."""
    query = db.query(TokenMap)
    
    if token_type:
        query = query.filter(TokenMap.token_type == token_type)
    
    tokens = query.order_by(TokenMap.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        TokenInfo(
            token=t.token,
            original=t.original_value,
            token_type=t.token_type.value,
            metadata=t.metadata_,
            created_at=t.created_at.isoformat() if t.created_at else ""
        )
        for t in tokens
    ]


@router.get("/stats", response_model=TokenStats)
def get_token_stats(db: Session = Depends(get_db)):
    """Get token statistics."""
    token_service = TokenizationService(db)
    stats = token_service.get_token_stats()
    
    return TokenStats(
        merchants=stats.get("merchant", 0),
        accounts=stats.get("account", 0),
        people=stats.get("person", 0),
        date_shift_days=stats.get("date_shift_days", 0),
    )
```

Update `backend/app/api/router.py`:

```python
from app.api.privacy import router as privacy_router

# Add to router includes:
router.include_router(privacy_router)
```

---

## Step 9: Add Privacy Settings UI

Update `frontend/src/types/index.ts`:

```typescript
// Add privacy types
export interface ProviderPrivacyConfig {
  provider: string;
  obfuscation_enabled: boolean;
}

export interface TokenStats {
  merchants: number;
  accounts: number;
  people: number;
  date_shift_days: number;
}

export interface PrivacySettings {
  obfuscation_enabled: boolean;
  provider_settings: ProviderPrivacyConfig[];
  stats: TokenStats;
}
```

Update `frontend/src/lib/api.ts`:

```typescript
// Add privacy API functions
export const privacyApi = {
  getSettings: (): Promise<PrivacySettings> => 
    fetch(`${API_BASE}/privacy/settings`).then(r => r.json()),
  
  updateSettings: (settings: Partial<{
    obfuscation_enabled?: boolean;
    provider_settings?: ProviderPrivacyConfig[];
  }>): Promise<PrivacySettings> =>
    fetch(`${API_BASE}/privacy/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    }).then(r => r.json()),
  
  preview: (text: string): Promise<{ original: string; tokenized: string }> =>
    fetch(`${API_BASE}/privacy/preview?text=${encodeURIComponent(text)}`).then(r => r.json()),
  
  getStats: (): Promise<TokenStats> =>
    fetch(`${API_BASE}/privacy/stats`).then(r => r.json()),
};
```

Create `frontend/src/components/settings/PrivacySettings.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Shield, Server, Cloud } from 'lucide-react';
import { privacyApi } from '@/lib/api';
import type { PrivacySettings } from '@/types';

export function PrivacySettingsPanel() {
  const [settings, setSettings] = useState<PrivacySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await privacyApi.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load privacy settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateMasterToggle = async (enabled: boolean) => {
    if (!settings) return;
    setUpdating(true);
    try {
      const updated = await privacyApi.updateSettings({
        obfuscation_enabled: enabled,
      });
      setSettings(updated);
    } catch (error) {
      console.error('Failed to update settings:', error);
    } finally {
      setUpdating(false);
    }
  };

  const updateProviderSetting = async (provider: string, enabled: boolean) => {
    if (!settings) return;
    setUpdating(true);
    
    const newProviderSettings = settings.provider_settings.map(ps =>
      ps.provider === provider ? { ...ps, obfuscation_enabled: enabled } : ps
    );
    
    try {
      const updated = await privacyApi.updateSettings({
        provider_settings: newProviderSettings,
      });
      setSettings(updated);
    } catch (error) {
      console.error('Failed to update settings:', error);
    } finally {
      setUpdating(false);
    }
  };

  if (loading || !settings) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Privacy Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-muted rounded w-3/4"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Privacy Settings
        </CardTitle>
        <CardDescription>
          Control how your data is anonymized before sending to AI providers
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Master Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="obfuscation-master" className="text-base font-medium">
              Data Obfuscation
            </Label>
            <p className="text-sm text-muted-foreground">
              Anonymize merchant names and dates before sending to AI
            </p>
          </div>
          <Switch
            id="obfuscation-master"
            checked={settings.obfuscation_enabled}
            onCheckedChange={updateMasterToggle}
            disabled={updating}
          />
        </div>

        {/* Per-Provider Settings */}
        {settings.obfuscation_enabled && (
          <div className="space-y-4 pt-4 border-t">
            <h4 className="font-medium">Provider Settings</h4>
            <p className="text-sm text-muted-foreground">
              Configure obfuscation per provider. Local providers (Ollama) typically don't need obfuscation since data never leaves your machine.
            </p>
            {settings.provider_settings.map((ps) => (
              <div key={ps.provider} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  {ps.provider === 'ollama' ? (
                    <Server className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Cloud className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="capitalize font-medium">{ps.provider}</span>
                  {ps.provider === 'ollama' ? (
                    <Badge variant="outline" className="text-xs">Local</Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">Cloud</Badge>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">
                    {ps.obfuscation_enabled ? 'Protected' : 'Raw data'}
                  </span>
                  <Switch
                    checked={ps.obfuscation_enabled}
                    onCheckedChange={(checked) => updateProviderSetting(ps.provider, checked)}
                    disabled={updating}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Token Statistics */}
        <div className="space-y-3 pt-4 border-t">
          <h4 className="font-medium">Token Statistics</h4>
          <p className="text-sm text-muted-foreground">
            Tokens are anonymized identifiers that replace your actual data when sending to AI.
          </p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Merchants tokenized:</span>
              <span className="font-medium">{settings.stats.merchants}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Accounts tokenized:</span>
              <span className="font-medium">{settings.stats.accounts}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">People tokenized:</span>
              <span className="font-medium">{settings.stats.people}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Date shift:</span>
              <span className="font-medium">+{settings.stats.date_shift_days} days</span>
            </div>
          </div>
        </div>

        {/* Preview Example */}
        <div className="space-y-2 rounded-lg bg-muted/50 p-4 border">
          <h4 className="font-medium text-sm">What AI Sees (Example)</h4>
          <div className="font-mono text-sm bg-background rounded p-2">
            MERCHANT_042 [Groceries] $187.34 2026-08-09
          </div>
          <p className="text-xs text-muted-foreground">
            Your actual merchant names, dates, and accounts are replaced with anonymous tokens. 
            The AI can still understand patterns and provide insights without knowing your specific data.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
```

Add to Settings page (`frontend/src/pages/Settings.tsx`):

```tsx
// Add import at top
import { PrivacySettingsPanel } from '@/components/settings/PrivacySettings';

// Add in the settings page JSX, after other settings sections:
<PrivacySettingsPanel />
```

---

## Step 10: Add Tests

Create `backend/tests/test_tokenization.py`:

```python
"""Tests for tokenization service."""

import pytest
from datetime import date
from app.services.tokenization_service import TokenizationService
from app.models.token_map import TokenMap, TokenType, DateShift


class TestMerchantTokenization:
    """Tests for merchant tokenization."""
    
    def test_same_merchant_same_token(self, db_session):
        """Same merchant should always get same token."""
        service = TokenizationService(db_session)
        
        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Whole Foods")
        
        assert token1 == token2
    
    def test_case_insensitive(self, db_session):
        """Tokenization should be case-insensitive."""
        service = TokenizationService(db_session)
        
        token1 = service.tokenize_merchant("whole foods")
        token2 = service.tokenize_merchant("WHOLE FOODS")
        token3 = service.tokenize_merchant("Whole Foods")
        
        assert token1 == token2 == token3
    
    def test_different_merchants_different_tokens(self, db_session):
        """Different merchants should get different tokens."""
        service = TokenizationService(db_session)
        
        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Trader Joes")
        
        assert token1 != token2
    
    def test_token_format(self, db_session):
        """Token should match expected format."""
        service = TokenizationService(db_session)
        
        token = service.tokenize_merchant("Test Merchant")
        
        assert token.startswith("MERCHANT_")
        assert len(token) == 13  # MERCHANT_0001
    
    def test_category_metadata_stored(self, db_session):
        """Category metadata should be stored with token."""
        service = TokenizationService(db_session)
        
        token = service.tokenize_merchant("Whole Foods", category="Groceries", subcategory="Supermarket")
        
        token_map = db_session.query(TokenMap).filter(TokenMap.token == token).first()
        assert token_map.metadata_["category"] == "Groceries"
        assert token_map.metadata_["subcategory"] == "Supermarket"


class TestPersonTokenization:
    """Tests for person name tokenization in descriptions."""
    
    def test_venmo_extraction(self, db_session):
        """Should extract and tokenize Venmo names."""
        service = TokenizationService(db_session)
        
        result = service.tokenize_description("VENMO PAYMENT JOHN SMITH")
        
        assert "VENMO" in result
        assert "PERSON_" in result
        assert "JOHN SMITH" not in result
    
    def test_zelle_extraction(self, db_session):
        """Should extract and tokenize Zelle names."""
        service = TokenizationService(db_session)
        
        result = service.tokenize_description("ZELLE TO JANE DOE")
        
        assert "ZELLE" in result
        assert "PERSON_" in result
        assert "JANE DOE" not in result
    
    def test_same_person_same_token(self, db_session):
        """Same person should get same token."""
        service = TokenizationService(db_session)
        
        result1 = service.tokenize_description("VENMO JOHN SMITH")
        result2 = service.tokenize_description("ZELLE TO JOHN SMITH")
        
        # Extract tokens
        import re
        tokens1 = re.findall(r'PERSON_\d+', result1)
        tokens2 = re.findall(r'PERSON_\d+', result2)
        
        assert tokens1[0] == tokens2[0]


class TestDateShifting:
    """Tests for date shifting."""
    
    def test_date_shifted(self, db_session):
        """Dates should be shifted by random offset."""
        service = TokenizationService(db_session)
        
        original = date(2024, 1, 15)
        shifted = service.shift_date(original)
        
        assert shifted != original
        assert shifted > original  # Shift is always positive (500-1500 days)
    
    def test_consistent_shift(self, db_session):
        """Same date should always shift the same amount."""
        service = TokenizationService(db_session)
        
        original = date(2024, 1, 15)
        shifted1 = service.shift_date(original)
        shifted2 = service.shift_date(original)
        
        assert shifted1 == shifted2
    
    def test_unshift_reverses(self, db_session):
        """Unshift should reverse the shift."""
        service = TokenizationService(db_session)
        
        original = date(2024, 1, 15)
        shifted = service.shift_date(original)
        unshifted = service.unshift_date(shifted)
        
        assert unshifted == original


class TestDetokenization:
    """Tests for de-tokenizing AI responses."""
    
    def test_detokenize_merchant(self, db_session):
        """Should replace merchant tokens with original values."""
        service = TokenizationService(db_session)
        
        # First, create a token
        token = service.tokenize_merchant("Whole Foods")
        
        # Then detokenize text containing it
        text = f"You spent $100 at {token} last month."
        result = service.detokenize(text)
        
        assert "Whole Foods" in result
        assert token not in result
    
    def test_detokenize_multiple_tokens(self, db_session):
        """Should handle multiple tokens in text."""
        service = TokenizationService(db_session)
        
        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Trader Joes")
        
        text = f"Compare {token1} vs {token2}"
        result = service.detokenize(text)
        
        assert "Whole Foods" in result
        assert "Trader Joes" in result


class TestBulkOperations:
    """Tests for bulk tokenization operations."""
    
    def test_get_unknown_merchants(self, db_session):
        """Should filter to only unknown merchants."""
        service = TokenizationService(db_session)
        
        # Create some known merchants
        service.tokenize_merchant("Whole Foods")
        service.tokenize_merchant("Trader Joes")
        
        # Check which are unknown
        merchants = ["Whole Foods", "Target", "Costco", "Trader Joes"]
        unknown = service.get_unknown_merchants(merchants)
        
        assert "Target" in unknown
        assert "Costco" in unknown
        assert "Whole Foods" not in unknown
        assert "Trader Joes" not in unknown
    
    def test_tokenize_transaction(self, db_session):
        """Should tokenize full transaction dict."""
        service = TokenizationService(db_session)
        
        transaction = {
            "clean_merchant": "Whole Foods",
            "amount": -187.34,
            "date": "2024-01-15",
            "category_name": "Groceries",
            "account_name": "Chase Checking",
            "account_type": "checking",
        }
        
        result = service.tokenize_transaction_for_ai(transaction)
        
        assert result["merchant"].startswith("MERCHANT_")
        assert "[Groceries]" in result["merchant"]
        assert result["amount"] == -187.34  # Amount unchanged
        assert "2024-01-15" not in result["date"]  # Date shifted
        assert result.get("account", "").startswith("ACCOUNT_")
        assert "clean_merchant" not in result
        assert "account_name" not in result


class TestPrivacySettings:
    """Tests for privacy settings persistence."""
    
    def test_settings_created_on_first_access(self, db_session):
        """Settings should be created with defaults on first access."""
        from app.models.privacy_settings import get_or_create_privacy_settings
        
        settings = get_or_create_privacy_settings(db_session)
        
        assert settings.obfuscation_enabled == True
        assert settings.ollama_obfuscation == False  # Local = off
        assert settings.openrouter_obfuscation == True  # Cloud = on
    
    def test_settings_persisted(self, db_session):
        """Settings changes should persist."""
        from app.models.privacy_settings import get_or_create_privacy_settings, PrivacySettings
        
        # Get and modify
        settings = get_or_create_privacy_settings(db_session)
        settings.ollama_obfuscation = True
        db_session.commit()
        
        # Fetch fresh
        settings2 = db_session.query(PrivacySettings).filter(PrivacySettings.id == 1).first()
        assert settings2.ollama_obfuscation == True
```

---

## Step 11: Final Testing & Verification

```bash
# Full rebuild
cd ~/projects/spendah
docker compose down
docker compose up -d --build
sleep 5

# Check for errors
docker compose logs api --tail 50

# Run migrations
docker compose exec api alembic upgrade head

# Test new endpoints
curl http://localhost:8000/api/v1/privacy/settings
curl http://localhost:8000/api/v1/privacy/stats
curl "http://localhost:8000/api/v1/privacy/preview?text=Whole%20Foods"

# Run tokenization tests
docker compose exec api pytest tests/test_tokenization.py -v

# Run all tests
docker compose exec api pytest -v --tb=short
```

**Test in UI:**
1. Go to Settings page
2. Should see new "Privacy Settings" section
3. Toggle obfuscation for different providers
4. See token statistics
5. Import a file - verify AI still categorizes correctly
6. Check that existing features work

---

## Verification Checklist

- [ ] `GET /api/v1/privacy/settings` returns settings from DB
- [ ] `PATCH /api/v1/privacy/settings` updates and persists provider toggles
- [ ] `GET /api/v1/privacy/preview` shows tokenization
- [ ] `GET /api/v1/privacy/stats` shows token counts
- [ ] `token_maps` table created and working
- [ ] `privacy_settings` table created with defaults
- [ ] `date_shifts` table created with random value
- [ ] Settings page shows privacy section
- [ ] Provider toggles work (Ollama off, cloud on by default)
- [ ] Settings persist across container restarts
- [ ] Import still works with obfuscation enabled
- [ ] AI categorization still accurate
- [ ] Format detection uses redacted samples
- [ ] Bulk categorization only sends unknown merchants
- [ ] Tokenization tests pass
- [ ] No console errors

---

## Notes

**What this achieves:**
- Cloud AI never sees your actual merchant names (after initial categorization)
- Cloud AI never sees your account numbers
- Cloud AI never sees exact dates (shifted by random offset)
- Cloud AI never sees names of people you pay (Venmo, Zelle, etc.)
- Local AI (Ollama) can bypass obfuscation for full accuracy
- Settings persist in database across restarts

**Privacy exposure summary:**
- Format detection: Zero PII (structural redaction)
- Categorization: Merchant names only (no amounts/dates/patterns) - low risk
- All other AI calls: Fully tokenized, zero PII

**Key changes from v1:**
- Privacy settings now stored in database (like `alert_settings`)
- Added Step 0 to examine existing AI implementation first
- Clarified that merchant-only categorization is low-risk
- Fixed `metadata` column name to `metadata_` (SQLAlchemy reserved word)
- Added `skip_obfuscation` parameter to `complete()` for merchant categorization
