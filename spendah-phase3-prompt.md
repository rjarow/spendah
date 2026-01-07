# Spendah - Phase 3: AI Integration

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture, AI prompts, and data models
2. `CLAUDE.md` - Project conventions

## Known Gotchas (from Phase 1 & 2)

1. **After model changes, generate migrations:**
   ```bash
   docker compose exec api alembic revision --autogenerate -m "description"
   docker compose exec api alembic upgrade head
   ```

2. **Never use SQLAlchemy reserved words:** `metadata`, `query`, `registry`, `type`

3. **Test after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   docker compose logs api --tail 30
   curl http://localhost:8000/api/v1/health
   ```

---

## Context

Phase 1 (Foundation) and Phase 2 (Import Pipeline) are complete. The app can:
- Import CSV/OFX files with manual column mapping
- Store transactions with deduplication
- Basic CRUD for accounts, categories, transactions

## Your Task: Phase 3 - AI Integration

Add AI-powered features using LiteLLM with OpenRouter as the default provider. Users should be able to configure their preferred provider/model via settings.

---

## Deliverables

### Step 1: Add Dependencies

Update `backend/requirements.txt`:
```
litellm>=1.0.0
```

Rebuild:
```bash
docker compose build api
```

### Step 2: Update Configuration

Update `backend/app/config.py` to add AI settings:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Existing settings...
    APP_NAME: str = "Spendah"
    DATABASE_URL: str = "sqlite:///./data/db.sqlite"
    
    # Import paths
    IMPORT_INBOX_PATH: str = "./data/imports/inbox"
    IMPORT_PROCESSED_PATH: str = "./data/imports/processed"
    IMPORT_FAILED_PATH: str = "./data/imports/failed"
    
    # AI Configuration
    AI_PROVIDER: str = "openrouter"  # openrouter, ollama, anthropic, openai
    AI_MODEL: str = "anthropic/claude-3-haiku"  # Model identifier
    AI_BASE_URL: Optional[str] = None  # For Ollama: http://localhost:11434
    
    # API Keys (optional based on provider)
    OPENROUTER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # AI Feature Flags
    AI_AUTO_CATEGORIZE: bool = True
    AI_CLEAN_MERCHANTS: bool = True
    AI_DETECT_FORMAT: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
```

Update `.env.example`:
```bash
# App
APP_NAME=Spendah

# Database
DATABASE_URL=sqlite:///./data/db.sqlite

# Import paths
IMPORT_INBOX_PATH=./data/imports/inbox
IMPORT_PROCESSED_PATH=./data/imports/processed
IMPORT_FAILED_PATH=./data/imports/failed

# AI Configuration
AI_PROVIDER=openrouter
AI_MODEL=anthropic/claude-3-haiku

# For Ollama (local)
# AI_PROVIDER=ollama
# AI_MODEL=llama3.1:8b
# AI_BASE_URL=http://localhost:11434

# API Keys (set the one for your provider)
OPENROUTER_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

### Step 3: Create AI Client

Create `backend/app/ai/__init__.py`:
```python
from app.ai.client import AIClient, get_ai_client

__all__ = ['AIClient', 'get_ai_client']
```

Create `backend/app/ai/client.py`:

```python
import litellm
from typing import Optional, Dict, Any, List
import json

from app.config import settings

# Configure LiteLLM
litellm.drop_params = True  # Ignore unsupported params

class AIClient:
    """Wrapper around LiteLLM for AI operations"""
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.model = self._get_model_string()
        self._configure_provider()
    
    def _get_model_string(self) -> str:
        """Get the full model string for LiteLLM"""
        model = settings.AI_MODEL
        
        if self.provider == "openrouter":
            # OpenRouter models need openrouter/ prefix
            if not model.startswith("openrouter/"):
                return f"openrouter/{model}"
            return model
        elif self.provider == "ollama":
            # Ollama models need ollama/ prefix
            if not model.startswith("ollama/"):
                return f"ollama/{model}"
            return model
        elif self.provider == "anthropic":
            return model
        elif self.provider == "openai":
            return model
        else:
            return model
    
    def _configure_provider(self):
        """Set up API keys and base URLs"""
        if self.provider == "openrouter":
            litellm.api_key = settings.OPENROUTER_API_KEY
            # OpenRouter uses OpenAI-compatible endpoint
            litellm.api_base = "https://openrouter.ai/api/v1"
        elif self.provider == "ollama":
            litellm.api_base = settings.AI_BASE_URL or "http://localhost:11434"
        elif self.provider == "anthropic":
            litellm.api_key = settings.ANTHROPIC_API_KEY
        elif self.provider == "openai":
            litellm.api_key = settings.OPENAI_API_KEY
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        json_mode: bool = False
    ) -> str:
        """
        Send a completion request to the AI model.
        
        Args:
            system_prompt: System message setting context
            user_prompt: User message with the actual request
            temperature: Randomness (0.0-1.0), lower = more deterministic
            max_tokens: Maximum response length
            json_mode: If True, request JSON response format
            
        Returns:
            The model's response text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add JSON mode if supported
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        try:
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI completion error: {e}")
            raise
    
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Send a completion request expecting JSON response.
        Parses and returns the JSON.
        """
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        # Clean up response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return json.loads(cleaned.strip())

# Singleton instance
_ai_client: Optional[AIClient] = None

def get_ai_client() -> AIClient:
    """Get or create the AI client singleton"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
```

### Step 4: Create AI Prompts

Create `backend/app/ai/prompts/__init__.py`:
```python
from app.ai.prompts.format_detection import FORMAT_DETECTION_SYSTEM, FORMAT_DETECTION_USER
from app.ai.prompts.categorization import CATEGORIZATION_SYSTEM, CATEGORIZATION_USER
from app.ai.prompts.merchant_cleaning import MERCHANT_CLEANING_SYSTEM, MERCHANT_CLEANING_USER

__all__ = [
    'FORMAT_DETECTION_SYSTEM', 'FORMAT_DETECTION_USER',
    'CATEGORIZATION_SYSTEM', 'CATEGORIZATION_USER', 
    'MERCHANT_CLEANING_SYSTEM', 'MERCHANT_CLEANING_USER'
]
```

Create `backend/app/ai/prompts/format_detection.py`:

```python
FORMAT_DETECTION_SYSTEM = """You are a financial data expert. Analyze CSV file contents and identify column mappings.

Respond with JSON only, no explanation:
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
  "date_format": "<strptime format string>",
  "amount_style": "signed" | "separate_columns" | "parentheses_negative",
  "skip_rows": <number of header rows, usually 0 or 1>,
  "source_guess": "<bank or card name if recognizable, or null>",
  "confidence": <0.0 to 1.0>
}

Column indices are 0-based.

Common date formats:
- %Y-%m-%d (2025-01-15)
- %m/%d/%Y (01/15/2025)
- %m/%d/%y (01/15/25)
- %d/%m/%Y (15/01/2025)
- %m-%d-%Y (01-15-2025)

Amount styles:
- "signed": single column with positive/negative values
- "separate_columns": separate debit and credit columns
- "parentheses_negative": negative amounts shown as (50.00)"""

FORMAT_DETECTION_USER = """Analyze this CSV file and identify the column mapping.

Headers: {headers}

First 5 data rows:
{sample_rows}

Return JSON with the column mapping."""
```

Create `backend/app/ai/prompts/merchant_cleaning.py`:

```python
MERCHANT_CLEANING_SYSTEM = """You clean merchant names from bank transaction descriptions.

Input: Raw bank transaction description
Output: Clean, human-readable merchant name

Rules:
- Remove transaction IDs, reference numbers, asterisks
- Expand abbreviations when obvious
- Keep location info only if it's a well-known chain
- Return just the clean name, no explanation

Examples:
- "AMZN MKTP US*1X2Y3Z" → "Amazon"
- "UBER *EATS PENDING" → "Uber Eats"  
- "SQ *BLUE BOTTLE COF" → "Blue Bottle Coffee"
- "GOOGLE *YOUTUBE MUSIC" → "YouTube Music"
- "TST* SHAKE SHACK 123" → "Shake Shack"
- "PAYPAL *SPOTIFY" → "Spotify"
- "ACH DEPOSIT GUSTO" → "Gusto"
- "VENMO PAYMENT 12345" → "Venmo"
- "CHECK DEP 1234" → "Check Deposit"
- "ATM WITHDRAWAL 5TH AVE" → "ATM Withdrawal"

Respond with just the clean merchant name, nothing else."""

MERCHANT_CLEANING_USER = """Clean this merchant name:

{raw_description}"""
```

Create `backend/app/ai/prompts/categorization.py`:

```python
CATEGORIZATION_SYSTEM = """You categorize financial transactions into the correct category.

Available categories:
{categories_json}

User's previous corrections (learn from these patterns):
{user_corrections}

For each transaction, respond with JSON only:
{{"category_id": "<uuid>", "confidence": <0.0-1.0>}}

Guidelines:
- Match based on merchant name and transaction patterns
- Use user corrections as strong signals for similar merchants
- If uncertain, use "Other" category
- Subscriptions go in "Subscriptions" not the service type (e.g., Netflix = Subscriptions, not Entertainment)
- Grocery stores = Groceries, not Food
- Restaurants = Restaurants (under Food), not Groceries"""

CATEGORIZATION_USER = """Categorize this transaction:

Merchant: {clean_merchant}
Raw Description: {raw_description}
Amount: ${amount}
Date: {date}
Account Type: {account_type}

Return JSON with category_id and confidence."""
```

### Step 5: Create AI Services

Create `backend/app/services/ai_service.py`:

```python
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
) -> Dict[str, Any]:
    """
    Use AI to detect CSV column mapping and format.
    
    Returns dict with columns, date_format, amount_style, etc.
    """
    if not settings.AI_DETECT_FORMAT:
        return None
    
    client = get_ai_client()
    
    # Format sample rows for prompt
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
    """
    Use AI to clean a raw bank description into a readable merchant name.
    
    Returns cleaned merchant name or None on failure.
    """
    if not settings.AI_CLEAN_MERCHANTS:
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
    clean_merchant: str,
    raw_description: str,
    amount: float,
    date: str,
    account_type: str = "bank"
) -> Optional[Dict[str, Any]]:
    """
    Use AI to categorize a transaction.
    
    Returns dict with category_id and confidence, or None on failure.
    """
    if not settings.AI_AUTO_CATEGORIZE:
        return None
    
    client = get_ai_client()
    
    # Get categories for context
    categories = db.query(Category).all()
    categories_json = json.dumps([
        {"id": str(c.id), "name": c.name, "parent_id": str(c.parent_id) if c.parent_id else None}
        for c in categories
    ], indent=2)
    
    # Get user corrections for few-shot learning
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
    """
    Clean multiple merchant names. 
    For efficiency, could batch into single request in future.
    """
    results = []
    for desc in descriptions:
        cleaned = await clean_merchant_name(desc)
        results.append(cleaned)
    return results


async def batch_categorize(
    db: Session,
    transactions: List[Dict[str, Any]]
) -> List[Optional[Dict[str, Any]]]:
    """
    Categorize multiple transactions.
    For efficiency, could batch into single request in future.
    """
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
```

### Step 6: Update Import Service for AI

Update `backend/app/services/import_service.py` to integrate AI:

Add these imports at the top:
```python
from app.services.ai_service import detect_csv_format, clean_merchant_name, categorize_transaction
from app.models.account import Account
import asyncio
```

Add a new function for AI-enhanced preview:
```python
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
    
    # Try AI format detection for CSV files
    detected_format = None
    if isinstance(parser, CSVParser):
        detected_format = await detect_csv_format(headers, preview_rows)
    
    # Count total rows
    if isinstance(parser, CSVParser):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            row_count = sum(1 for _ in f) - 1
    else:
        with open(file_path, 'rb') as f:
            from ofxparse import OfxParser
            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)
    
    # Store pending import info with detected format
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
        detected_format=detected_format  # Add this field
    )
```

Update the `process_import` function to clean merchants and categorize:
```python
async def process_import_with_ai(
    db: Session,
    import_id: str,
    request: ImportConfirmRequest
) -> ImportStatusResponse:
    """Process import with AI merchant cleaning and categorization"""
    
    if import_id not in PENDING_IMPORTS:
        raise ValueError(f"Import {import_id} not found or expired")
    
    pending = PENDING_IMPORTS[import_id]
    file_path = Path(pending['file_path'])
    filename = pending['filename']
    
    # Get account for context
    account = db.query(Account).filter(Account.id == request.account_id).first()
    account_type = account.account_type if account else "bank"
    
    # Create import log
    import_log = ImportLog(
        id=import_id,
        filename=filename,
        account_id=request.account_id,
        status=ImportStatus.PROCESSING
    )
    db.add(import_log)
    db.commit()
    
    try:
        # Get parser and parse file
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
                # Generate hash for deduplication
                txn_hash = generate_transaction_hash(
                    txn_data['date'],
                    txn_data['amount'],
                    txn_data['raw_description'],
                    request.account_id
                )
                
                # Check for duplicate
                if is_duplicate(db, txn_hash):
                    skipped += 1
                    continue
                
                # AI: Clean merchant name
                clean_merchant = await clean_merchant_name(txn_data['raw_description'])
                
                # AI: Categorize transaction
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
                
                # Create transaction
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
        
        # Update import log
        import_log.status = ImportStatus.COMPLETED
        import_log.transactions_imported = imported
        import_log.transactions_skipped = skipped
        if errors:
            import_log.error_message = "; ".join(errors[:10])
        db.commit()
        
        # Move file to processed
        processed_path = Path(settings.IMPORT_PROCESSED_PATH)
        processed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(processed_path / file_path.name))
        
        # Clean up pending
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
        
        failed_path = Path(settings.IMPORT_FAILED_PATH)
        failed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(failed_path / file_path.name))
        
        if import_id in PENDING_IMPORTS:
            del PENDING_IMPORTS[import_id]
        
        raise
```

### Step 7: Update Import Schema for AI Detection

Update `backend/app/schemas/import_file.py` to include detected format:

Add to `ImportUploadResponse`:
```python
class ImportUploadResponse(BaseModel):
    import_id: str
    filename: str
    row_count: int
    headers: List[str]
    preview_rows: List[List[str]]
    detected_format: Optional[Dict[str, Any]] = None  # AI-detected column mapping
    
    class Config:
        from_attributes = True
```

### Step 8: Update Import API Routes

Update `backend/app/api/imports.py` to use async AI functions:

```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.import_file import (
    ImportUploadResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    ImportLogResponse
)
from app.services import import_service

router = APIRouter(prefix="/imports", tags=["imports"])

@router.post("/upload", response_model=ImportUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file for import with AI format detection"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    allowed_extensions = ['.csv', '.ofx', '.qfx']
    ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        content = await file.read()
        file_path, import_id = import_service.save_upload(content, file.filename)
        # Use AI-enhanced preview
        return await import_service.get_preview_with_ai(file_path, import_id, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{import_id}/confirm", response_model=ImportStatusResponse)
async def confirm_import(
    import_id: str,
    request: ImportConfirmRequest,
    db: Session = Depends(get_db)
):
    """Confirm and process import with AI categorization"""
    try:
        # Use AI-enhanced import processing
        return await import_service.process_import_with_ai(db, import_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{import_id}/status", response_model=ImportStatusResponse)
def get_import_status(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Get status of an import"""
    try:
        return import_service.get_import_status(db, import_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/history", response_model=list[ImportLogResponse])
def get_import_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get import history"""
    logs = import_service.get_import_history(db, limit)
    return [ImportLogResponse.model_validate(log) for log in logs]
```

### Step 9: Create Settings API

Create `backend/app/schemas/settings.py`:

```python
from pydantic import BaseModel
from typing import Optional, List

class AISettings(BaseModel):
    provider: str
    model: str
    auto_categorize: bool
    clean_merchants: bool
    detect_format: bool

class AISettingsUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    auto_categorize: Optional[bool] = None
    clean_merchants: Optional[bool] = None
    detect_format: Optional[bool] = None

class AvailableProvider(BaseModel):
    id: str
    name: str
    requires_key: bool
    models: List[str]

class SettingsResponse(BaseModel):
    ai: AISettings
    available_providers: List[AvailableProvider]
```

Create `backend/app/api/settings.py`:

```python
from fastapi import APIRouter, HTTPException
from app.schemas.settings import (
    AISettings, 
    AISettingsUpdate, 
    SettingsResponse,
    AvailableProvider
)
from app.config import settings
import os

router = APIRouter(prefix="/settings", tags=["settings"])

# Available providers and their models
AVAILABLE_PROVIDERS = [
    AvailableProvider(
        id="openrouter",
        name="OpenRouter",
        requires_key=True,
        models=[
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-8b-instruct",
        ]
    ),
    AvailableProvider(
        id="ollama",
        name="Ollama (Local)",
        requires_key=False,
        models=[
            "llama3.1:8b",
            "llama3.1:70b",
            "mistral:7b",
            "codellama:7b",
        ]
    ),
    AvailableProvider(
        id="anthropic",
        name="Anthropic",
        requires_key=True,
        models=[
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
    ),
    AvailableProvider(
        id="openai",
        name="OpenAI",
        requires_key=True,
        models=[
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
        ]
    ),
]

@router.get("", response_model=SettingsResponse)
def get_settings():
    """Get current settings"""
    return SettingsResponse(
        ai=AISettings(
            provider=settings.AI_PROVIDER,
            model=settings.AI_MODEL,
            auto_categorize=settings.AI_AUTO_CATEGORIZE,
            clean_merchants=settings.AI_CLEAN_MERCHANTS,
            detect_format=settings.AI_DETECT_FORMAT,
        ),
        available_providers=AVAILABLE_PROVIDERS
    )

@router.patch("/ai", response_model=AISettings)
def update_ai_settings(update: AISettingsUpdate):
    """
    Update AI settings.
    
    Note: In a real app, this would persist to DB or config file.
    For MVP, this updates the in-memory settings (resets on restart).
    """
    if update.provider is not None:
        settings.AI_PROVIDER = update.provider
    if update.model is not None:
        settings.AI_MODEL = update.model
    if update.auto_categorize is not None:
        settings.AI_AUTO_CATEGORIZE = update.auto_categorize
    if update.clean_merchants is not None:
        settings.AI_CLEAN_MERCHANTS = update.clean_merchants
    if update.detect_format is not None:
        settings.AI_DETECT_FORMAT = update.detect_format
    
    # Reinitialize AI client with new settings
    from app.ai.client import _ai_client
    global _ai_client
    _ai_client = None  # Will be recreated on next use
    
    return AISettings(
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
        auto_categorize=settings.AI_AUTO_CATEGORIZE,
        clean_merchants=settings.AI_CLEAN_MERCHANTS,
        detect_format=settings.AI_DETECT_FORMAT,
    )

@router.post("/ai/test")
async def test_ai_connection():
    """Test the AI connection with current settings"""
    from app.ai.client import get_ai_client
    
    try:
        client = get_ai_client()
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'OK' if you can hear me.",
            max_tokens=10
        )
        return {"status": "ok", "response": response.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI connection failed: {str(e)}")
```

Update `backend/app/api/router.py` to include settings:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router
from app.api.imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.api.settings import router as settings_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(imports_router)
api_router.include_router(transactions_router)
api_router.include_router(settings_router)

@api_router.get("/health")
def health_check():
    from app.config import settings
    return {"status": "ok", "app_name": settings.APP_NAME}
```

### Step 10: Create User Corrections Endpoint

When user changes a category, store it for future AI learning.

Update `backend/app/api/transactions.py` to record corrections:

```python
from app.models.user_correction import UserCorrection

@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction and record user corrections for AI learning"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If category changed and was AI-categorized, record correction
    if update.category_id and transaction.ai_categorized and update.category_id != transaction.category_id:
        correction = UserCorrection(
            id=str(uuid.uuid4()),
            raw_description=transaction.raw_description,
            clean_merchant=update.clean_merchant or transaction.clean_merchant,
            category_id=update.category_id
        )
        db.add(correction)
    
    # If merchant name changed, record correction
    if update.clean_merchant and update.clean_merchant != transaction.clean_merchant:
        # Update or create correction
        existing = db.query(UserCorrection).filter(
            UserCorrection.raw_description == transaction.raw_description
        ).first()
        if existing:
            existing.clean_merchant = update.clean_merchant
        else:
            correction = UserCorrection(
                id=str(uuid.uuid4()),
                raw_description=transaction.raw_description,
                clean_merchant=update.clean_merchant,
                category_id=update.category_id or transaction.category_id
            )
            db.add(correction)
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    # Mark as no longer AI-categorized if user changed it
    if update.category_id:
        transaction.ai_categorized = False
    
    db.commit()
    db.refresh(transaction)
    
    return TransactionResponse.model_validate(transaction)
```

Add import at top:
```python
import uuid
```

### Step 11: Frontend - Update Types

Update `frontend/src/types/index.ts`:

```typescript
// Add these types

export interface AISettings {
  provider: string
  model: string
  auto_categorize: boolean
  clean_merchants: boolean
  detect_format: boolean
}

export interface AvailableProvider {
  id: string
  name: string
  requires_key: boolean
  models: string[]
}

export interface SettingsResponse {
  ai: AISettings
  available_providers: AvailableProvider[]
}

export interface DetectedFormat {
  columns: {
    date: number | null
    amount: number | null
    description: number | null
    category: number | null
    debit: number | null
    credit: number | null
    balance: number | null
  }
  date_format: string
  amount_style: 'signed' | 'separate_columns' | 'parentheses_negative'
  skip_rows: number
  source_guess: string | null
  confidence: number
}

// Update ImportUploadResponse
export interface ImportUploadResponse {
  import_id: string
  filename: string
  row_count: number
  headers: string[]
  preview_rows: string[][]
  detected_format?: DetectedFormat | null
}
```

### Step 12: Frontend - Add Settings API Functions

Add to `frontend/src/lib/api.ts`:

```typescript
// Settings functions
export async function getSettings() {
  const response = await api.get('/settings')
  return response.data
}

export async function updateAISettings(data: {
  provider?: string
  model?: string
  auto_categorize?: boolean
  clean_merchants?: boolean
  detect_format?: boolean
}) {
  const response = await api.patch('/settings/ai', data)
  return response.data
}

export async function testAIConnection() {
  const response = await api.post('/settings/ai/test')
  return response.data
}
```

### Step 13: Frontend - Update Import Page for AI Detection

Update the Import page to use AI-detected format as defaults.

Update `frontend/src/pages/Import.tsx` - in the `uploadMutation.onSuccess`:

```typescript
const uploadMutation = useMutation({
  mutationFn: uploadFile,
  onSuccess: (data) => {
    setUploadResponse(data)
    
    // If AI detected format, use it as defaults
    if (data.detected_format && data.detected_format.confidence > 0.5) {
      const detected = data.detected_format
      setColumnMapping({
        date_col: detected.columns.date ?? 0,
        amount_col: detected.columns.amount ?? 1,
        description_col: detected.columns.description ?? 2,
      })
      if (detected.date_format) {
        // Map Python strptime to our select options
        const formatMap: Record<string, string> = {
          '%Y-%m-%d': '%Y-%m-%d',
          '%m/%d/%Y': '%m/%d/%Y',
          '%d/%m/%Y': '%d/%m/%Y',
          '%m-%d-%Y': '%m-%d-%Y',
        }
        setDateFormat(formatMap[detected.date_format] || '%Y-%m-%d')
      }
    }
  },
})
```

Add a banner showing AI detection:

```tsx
{uploadResponse.detected_format && uploadResponse.detected_format.confidence > 0.5 && (
  <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
    ✨ AI detected format: {uploadResponse.detected_format.source_guess || 'Unknown source'} 
    ({Math.round(uploadResponse.detected_format.confidence * 100)}% confidence)
  </div>
)}
```

### Step 14: Frontend - Create Settings Page

Update `frontend/src/pages/Settings.tsx`:

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateAISettings, testAIConnection } from '@/lib/api'
import { Button } from '@/components/ui/button'

export default function Settings() {
  const queryClient = useQueryClient()
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testError, setTestError] = useState<string | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  })

  const updateMutation = useMutation({
    mutationFn: updateAISettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: testAIConnection,
    onSuccess: (data) => {
      setTestResult(data.response)
      setTestError(null)
    },
    onError: (error: any) => {
      setTestError(error.response?.data?.detail || 'Connection failed')
      setTestResult(null)
    },
  })

  if (isLoading) {
    return <div>Loading...</div>
  }

  const currentProvider = settings?.available_providers?.find(
    (p: any) => p.id === settings?.ai?.provider
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* AI Configuration */}
      <div className="border rounded-lg p-4 space-y-4">
        <h2 className="text-lg font-semibold">AI Configuration</h2>

        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium mb-1">AI Provider</label>
          <select
            className="w-full border rounded p-2"
            value={settings?.ai?.provider || ''}
            onChange={(e) => updateMutation.mutate({ provider: e.target.value })}
          >
            {settings?.available_providers?.map((provider: any) => (
              <option key={provider.id} value={provider.id}>
                {provider.name} {provider.requires_key ? '(API key required)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium mb-1">Model</label>
          <select
            className="w-full border rounded p-2"
            value={settings?.ai?.model || ''}
            onChange={(e) => updateMutation.mutate({ model: e.target.value })}
          >
            {currentProvider?.models?.map((model: string) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>

        {/* Feature Toggles */}
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.auto_categorize ?? true}
              onChange={(e) => updateMutation.mutate({ auto_categorize: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">Auto-categorize transactions</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.clean_merchants ?? true}
              onChange={(e) => updateMutation.mutate({ clean_merchants: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">Clean merchant names</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.detect_format ?? true}
              onChange={(e) => updateMutation.mutate({ detect_format: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">AI format detection for CSV files</span>
          </label>
        </div>

        {/* Test Connection */}
        <div className="pt-4 border-t">
          <Button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            variant="outline"
          >
            {testMutation.isPending ? 'Testing...' : 'Test AI Connection'}
          </Button>
          
          {testResult && (
            <p className="mt-2 text-sm text-green-600">
              ✓ Connection successful: {testResult}
            </p>
          )}
          
          {testError && (
            <p className="mt-2 text-sm text-red-600">
              ✗ {testError}
            </p>
          )}
        </div>
      </div>

      {/* API Key Notice */}
      <div className="bg-yellow-50 border border-yellow-200 rounded p-4 text-sm">
        <p className="font-medium text-yellow-800">API Key Configuration</p>
        <p className="text-yellow-700 mt-1">
          API keys are configured via environment variables for security. 
          Set <code className="bg-yellow-100 px-1">OPENROUTER_API_KEY</code>, 
          <code className="bg-yellow-100 px-1">ANTHROPIC_API_KEY</code>, or 
          <code className="bg-yellow-100 px-1">OPENAI_API_KEY</code> in your 
          <code className="bg-yellow-100 px-1">.env</code> file.
        </p>
      </div>
    </div>
  )
}
```

---

## Final Steps

1. **Rebuild and restart:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

2. **Check for errors:**
   ```bash
   docker compose logs api --tail 50
   ```

3. **Set your API key:**
   ```bash
   # Edit .env file
   nano .env
   # Add: OPENROUTER_API_KEY=sk-or-your-key-here
   
   # Restart to pick up new env
   docker compose restart api
   ```

4. **Test AI connection:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/settings/ai/test
   ```

5. **Test full import with AI:**
   - Go to http://localhost:5173/import
   - Upload a CSV file
   - Should see AI-detected format
   - Confirm import
   - Check transactions have clean merchant names and categories

---

## Verification Commands

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get settings
curl http://localhost:8000/api/v1/settings

# Test AI
curl -X POST http://localhost:8000/api/v1/settings/ai/test

# Upload and import a file (full flow in UI)
```

---

## Do NOT Implement Yet

- Learned formats storage (Phase 4+)
- Recurring detection (Phase 5)
- Alerts system (Phase 5-6)
- Subscription review (Phase 6)

Focus on getting AI categorization and merchant cleaning working reliably first.
