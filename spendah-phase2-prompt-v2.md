# Spendah - Phase 2: Import Pipeline

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture and data models
2. `CLAUDE.md` - Project conventions

## Known Gotchas (Learn from Phase 1)

These mistakes were made in Phase 1. Do NOT repeat them:

1. **Always generate Alembic migrations after model changes:**
   ```bash
   docker compose exec api alembic revision --autogenerate -m "description"
   docker compose exec api alembic upgrade head
   ```

2. **Never use SQLAlchemy reserved words as column names:**
   - BAD: `metadata`, `query`, `registry`, `type`
   - GOOD: `alert_metadata`, `file_type`, `query_string`

3. **Circular foreign keys need explicit foreign_keys parameter:**
   ```python
   # BAD
   learned_format = relationship("LearnedFormat", back_populates="accounts")
   
   # GOOD
   learned_format = relationship("LearnedFormat", back_populates="accounts", foreign_keys=[learned_format_id])
   ```

4. **Use `npm install` not `npm ci` in Dockerfiles** (no package-lock.json)

5. **Always test after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   docker compose logs api --tail 20
   curl http://localhost:8000/api/v1/health
   ```

---

## Context

Phase 1 is complete. The project has:
- All database models (transactions, accounts, categories, etc.)
- Basic CRUD APIs for accounts and categories  
- React frontend with routing and placeholder pages
- Docker setup working
- Alembic migrations working

## Your Task: Phase 2 - Import Pipeline

Build the file import system. Users will upload CSV/OFX files, and the system will parse and store transactions.

**Do NOT implement AI features yet.** No LLM calls. Just file parsing and storage.

---

## Deliverables (Complete in Order)

### Step 1: Add Dependencies

Add to `backend/requirements.txt`:
```
ofxparse>=0.21
python-multipart>=0.0.6
```

Rebuild after:
```bash
docker compose build api
```

### Step 2: Backend - Pydantic Schemas

Create `backend/app/schemas/import_file.py`:

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ColumnMapping(BaseModel):
    date_col: int
    amount_col: int
    description_col: int
    debit_col: Optional[int] = None
    credit_col: Optional[int] = None
    balance_col: Optional[int] = None

class ImportUploadResponse(BaseModel):
    import_id: str
    filename: str
    row_count: int
    headers: List[str]
    preview_rows: List[List[str]]
    
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
```

Create `backend/app/schemas/transaction.py`:

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class TransactionBase(BaseModel):
    date: date
    amount: Decimal
    raw_description: str
    clean_merchant: Optional[str] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False

class TransactionCreate(TransactionBase):
    account_id: str
    hash: str

class TransactionUpdate(BaseModel):
    clean_merchant: Optional[str] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None

class TransactionResponse(BaseModel):
    id: str
    hash: str
    date: date
    amount: Decimal
    raw_description: str
    clean_merchant: Optional[str]
    category_id: Optional[str]
    account_id: str
    is_recurring: bool
    recurring_group_id: Optional[str]
    notes: Optional[str]
    ai_categorized: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    pages: int
```

Update `backend/app/schemas/__init__.py` to export new schemas.

### Step 3: Backend - Parser Base Class

Create `backend/app/parsers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from pathlib import Path

class BaseParser(ABC):
    """Base class for file parsers"""
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file"""
        pass
    
    @abstractmethod
    def parse(
        self, 
        file_path: Path, 
        column_mapping: Dict[str, int],
        date_format: str = "%Y-%m-%d"
    ) -> List[Dict[str, Any]]:
        """
        Parse file and return list of transaction dicts.
        Each dict should have: date, amount, raw_description
        """
        pass
    
    @abstractmethod
    def get_preview(
        self, 
        file_path: Path, 
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return (headers, preview_rows) for format confirmation"""
        pass
```

### Step 4: Backend - CSV Parser

Create `backend/app/parsers/csv_parser.py`:

```python
import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from app.parsers.base import BaseParser

class CSVParser(BaseParser):
    """Parser for CSV bank/card exports"""
    
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.csv'
    
    def get_preview(
        self, 
        file_path: Path, 
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return headers and preview rows"""
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Detect dialect
            sample = f.read(8192)
            f.seek(0)
            
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel
            
            reader = csv.reader(f, dialect)
            headers = next(reader, [])
            
            preview_rows = []
            for i, row in enumerate(reader):
                if i >= rows:
                    break
                preview_rows.append(row)
            
            return headers, preview_rows
    
    def parse(
        self, 
        file_path: Path, 
        column_mapping: Dict[str, int],
        date_format: str = "%Y-%m-%d"
    ) -> List[Dict[str, Any]]:
        """Parse CSV and return transaction dicts"""
        transactions = []
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            try:
                dialect = csv.Sniffer().sniff(f.read(8192))
                f.seek(0)
            except csv.Error:
                dialect = csv.excel
                f.seek(0)
            
            reader = csv.reader(f, dialect)
            next(reader)  # Skip header
            
            for row in reader:
                if not row or all(cell.strip() == '' for cell in row):
                    continue
                    
                try:
                    txn = self._parse_row(row, column_mapping, date_format)
                    if txn:
                        transactions.append(txn)
                except Exception as e:
                    # Log but continue
                    print(f"Error parsing row {row}: {e}")
                    continue
        
        return transactions
    
    def _parse_row(
        self, 
        row: List[str], 
        mapping: Dict[str, int],
        date_format: str
    ) -> Dict[str, Any]:
        """Parse a single row into a transaction dict"""
        
        # Parse date
        date_str = row[mapping['date_col']].strip()
        txn_date = datetime.strptime(date_str, date_format).date()
        
        # Parse amount
        amount = self._parse_amount(row, mapping)
        if amount is None:
            return None
        
        # Get description
        description = row[mapping['description_col']].strip()
        
        return {
            'date': txn_date,
            'amount': amount,
            'raw_description': description
        }
    
    def _parse_amount(
        self, 
        row: List[str], 
        mapping: Dict[str, int]
    ) -> Decimal:
        """Parse amount handling various formats"""
        
        # Check for separate debit/credit columns
        if mapping.get('debit_col') is not None and mapping.get('credit_col') is not None:
            debit = self._clean_amount(row[mapping['debit_col']])
            credit = self._clean_amount(row[mapping['credit_col']])
            
            if debit and debit > 0:
                return -debit  # Debits are expenses (negative)
            elif credit and credit > 0:
                return credit  # Credits are income (positive)
            return Decimal('0')
        
        # Single amount column
        amount_str = row[mapping['amount_col']]
        return self._clean_amount(amount_str)
    
    def _clean_amount(self, amount_str: str) -> Decimal:
        """Clean and parse amount string"""
        if not amount_str or not amount_str.strip():
            return None
            
        amount_str = amount_str.strip()
        
        # Handle parentheses for negative: (50.00) -> -50.00
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]
        
        # Remove currency symbols and commas
        amount_str = re.sub(r'[$,]', '', amount_str)
        
        try:
            return Decimal(amount_str)
        except InvalidOperation:
            return None
```

### Step 5: Backend - OFX Parser

Create `backend/app/parsers/ofx_parser.py`:

```python
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal

from ofxparse import OfxParser as OFXParseLib

from app.parsers.base import BaseParser

class OFXParser(BaseParser):
    """Parser for OFX/QFX bank exports"""
    
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.ofx', '.qfx']
    
    def get_preview(
        self, 
        file_path: Path, 
        rows: int = 5
    ) -> Tuple[List[str], List[List[str]]]:
        """Return headers and preview rows for OFX"""
        headers = ['Date', 'Amount', 'Description', 'Type', 'ID']
        
        with open(file_path, 'rb') as f:
            ofx = OFXParseLib.parse(f)
        
        preview_rows = []
        for account in ofx.accounts:
            for txn in account.statement.transactions[:rows]:
                preview_rows.append([
                    txn.date.strftime('%Y-%m-%d'),
                    str(txn.amount),
                    txn.memo or txn.payee or '',
                    txn.type,
                    txn.id
                ])
                if len(preview_rows) >= rows:
                    break
            if len(preview_rows) >= rows:
                break
        
        return headers, preview_rows
    
    def parse(
        self, 
        file_path: Path, 
        column_mapping: Dict[str, int] = None,  # Ignored for OFX
        date_format: str = None  # Ignored for OFX
    ) -> List[Dict[str, Any]]:
        """Parse OFX and return transaction dicts"""
        transactions = []
        
        with open(file_path, 'rb') as f:
            ofx = OFXParseLib.parse(f)
        
        for account in ofx.accounts:
            for txn in account.statement.transactions:
                # Use memo or payee as description
                description = txn.memo or txn.payee or f"Transaction {txn.id}"
                
                transactions.append({
                    'date': txn.date.date() if hasattr(txn.date, 'date') else txn.date,
                    'amount': Decimal(str(txn.amount)),
                    'raw_description': description.strip()
                })
        
        return transactions
```

Create `backend/app/parsers/__init__.py`:

```python
from app.parsers.base import BaseParser
from app.parsers.csv_parser import CSVParser
from app.parsers.ofx_parser import OFXParser

__all__ = ['BaseParser', 'CSVParser', 'OFXParser']
```

### Step 6: Backend - Deduplication Service

Create `backend/app/services/deduplication_service.py`:

```python
import hashlib
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction

def generate_transaction_hash(
    txn_date: date,
    amount: Decimal,
    raw_description: str,
    account_id: str
) -> str:
    """
    Generate SHA256 hash for deduplication.
    Uses date|amount|description|account_id
    """
    components = [
        txn_date.isoformat(),
        str(amount),
        raw_description.strip().lower(),
        str(account_id)
    ]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode()).hexdigest()

def is_duplicate(db: Session, txn_hash: str) -> bool:
    """Check if transaction with this hash already exists"""
    return db.query(Transaction).filter(Transaction.hash == txn_hash).first() is not None
```

### Step 7: Backend - Import Service

Create `backend/app/services/import_service.py`:

```python
import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.transaction import Transaction
from app.models.import_log import ImportLog
from app.schemas.import_file import (
    ImportUploadResponse, 
    ImportConfirmRequest, 
    ImportStatusResponse,
    ImportStatus,
    ColumnMapping
)
from app.parsers.csv_parser import CSVParser
from app.parsers.ofx_parser import OFXParser
from app.services.deduplication_service import generate_transaction_hash, is_duplicate

# Store pending imports in memory (in production, use Redis or DB)
PENDING_IMPORTS: Dict[str, Dict[str, Any]] = {}

def get_parser(file_path: Path):
    """Get appropriate parser for file type"""
    parsers = [CSVParser(), OFXParser()]
    for parser in parsers:
        if parser.can_parse(file_path):
            return parser
    return None

def save_upload(file_content: bytes, filename: str) -> Tuple[Path, str]:
    """Save uploaded file and return path and import_id"""
    import_id = str(uuid.uuid4())
    
    # Ensure inbox directory exists
    inbox_path = Path(settings.IMPORT_INBOX_PATH)
    inbox_path.mkdir(parents=True, exist_ok=True)
    
    # Save with import_id prefix to avoid collisions
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
    
    # Count total rows
    if isinstance(parser, CSVParser):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            row_count = sum(1 for _ in f) - 1  # Subtract header
    else:
        # For OFX, count transactions
        with open(file_path, 'rb') as f:
            from ofxparse import OfxParser
            ofx = OfxParser.parse(f)
            row_count = sum(len(acc.statement.transactions) for acc in ofx.accounts)
    
    # Store pending import info
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

def process_import(
    db: Session,
    import_id: str,
    request: ImportConfirmRequest
) -> ImportStatusResponse:
    """Process the import after user confirmation"""
    
    if import_id not in PENDING_IMPORTS:
        raise ValueError(f"Import {import_id} not found or expired")
    
    pending = PENDING_IMPORTS[import_id]
    file_path = Path(pending['file_path'])
    filename = pending['filename']
    
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
        
        # Convert ColumnMapping to dict for parser
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
                
                # Create transaction
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
        
        # Update import log
        import_log.status = ImportStatus.COMPLETED
        import_log.transactions_imported = imported
        import_log.transactions_skipped = skipped
        if errors:
            import_log.error_message = "; ".join(errors[:10])  # First 10 errors
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
        # Update import log with failure
        import_log.status = ImportStatus.FAILED
        import_log.error_message = str(e)
        db.commit()
        
        # Move to failed
        failed_path = Path(settings.IMPORT_FAILED_PATH)
        failed_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(failed_path / file_path.name))
        
        # Clean up pending
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
```

### Step 8: Backend - Import API Routes

Create `backend/app/api/imports.py`:

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
    """Upload a file for import"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
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
        return import_service.get_preview(file_path, import_id, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{import_id}/confirm", response_model=ImportStatusResponse)
def confirm_import(
    import_id: str,
    request: ImportConfirmRequest,
    db: Session = Depends(get_db)
):
    """Confirm and process an import"""
    try:
        return import_service.process_import(db, import_id, request)
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

### Step 9: Backend - Transaction API Routes

Create `backend/app/api/transactions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionResponse,
    TransactionUpdate,
    TransactionListResponse
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("", response_model=TransactionListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    is_recurring: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List transactions with filtering and pagination"""
    query = db.query(Transaction)
    
    # Apply filters
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if is_recurring is not None:
        query = query.filter(Transaction.is_recurring == is_recurring)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.raw_description.ilike(search_term),
                Transaction.clean_merchant.ilike(search_term)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Transaction.date.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    transactions = query.all()
    pages = (total + per_page - 1) // per_page  # Ceiling division
    
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        pages=pages
    )

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Get a single transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)

@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    db.commit()
    db.refresh(transaction)
    
    return TransactionResponse.model_validate(transaction)
```

### Step 10: Register Routes

Update `backend/app/api/router.py` to include new routes:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router
from app.api.imports import router as imports_router
from app.api.transactions import router as transactions_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(imports_router)
api_router.include_router(transactions_router)

@api_router.get("/health")
def health_check():
    from app.config import settings
    return {"status": "ok", "app_name": settings.APP_NAME}
```

### Step 11: Frontend - API Functions

Update `frontend/src/lib/api.ts` to add import functions:

```typescript
// Add these types to frontend/src/types/index.ts first, then import them

// Add to api.ts:

// Import functions
export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/imports/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function confirmImport(importId: string, data: {
  account_id: string
  column_mapping: {
    date_col: number
    amount_col: number
    description_col: number
    debit_col?: number
    credit_col?: number
  }
  date_format: string
  save_format?: boolean
  format_name?: string
}) {
  const response = await api.post(`/imports/${importId}/confirm`, data)
  return response.data
}

export async function getImportStatus(importId: string) {
  const response = await api.get(`/imports/${importId}/status`)
  return response.data
}

export async function getImportHistory() {
  const response = await api.get('/imports/history')
  return response.data
}

// Transaction functions
export async function getTransactions(params: {
  page?: number
  per_page?: number
  account_id?: string
  category_id?: string
  start_date?: string
  end_date?: string
  search?: string
  is_recurring?: boolean
}) {
  const response = await api.get('/transactions', { params })
  return response.data
}

export async function getTransaction(id: string) {
  const response = await api.get(`/transactions/${id}`)
  return response.data
}

export async function updateTransaction(id: string, data: {
  clean_merchant?: string
  category_id?: string
  notes?: string
  is_recurring?: boolean
}) {
  const response = await api.patch(`/transactions/${id}`, data)
  return response.data
}
```

### Step 12: Frontend - File Upload Component

Create `frontend/src/components/imports/FileDropZone.tsx`:

```tsx
import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface FileDropZoneProps {
  onFileSelect: (file: File) => void
  isUploading?: boolean
}

export function FileDropZone({ onFileSelect, isUploading }: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      const file = files[0]
      setSelectedFile(file)
    }
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setSelectedFile(files[0])
    }
  }, [])

  const handleUpload = () => {
    if (selectedFile) {
      onFileSelect(selectedFile)
    }
  }

  return (
    <div className="space-y-4">
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragging ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-gray-400'}
        `}
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          className="hidden"
          accept=".csv,.ofx,.qfx"
          onChange={handleFileInput}
        />
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          Drop CSV, OFX, or QFX file here, or click to browse
        </p>
        {selectedFile && (
          <p className="mt-2 text-sm font-medium text-primary">
            Selected: {selectedFile.name}
          </p>
        )}
      </div>
      
      {selectedFile && (
        <Button 
          onClick={handleUpload} 
          disabled={isUploading}
          className="w-full"
        >
          {isUploading ? 'Uploading...' : 'Upload File'}
        </Button>
      )}
    </div>
  )
}
```

### Step 13: Frontend - Import Page

Update `frontend/src/pages/Import.tsx`:

```tsx
import { useState } from 'react'
import { FileDropZone } from '@/components/imports/FileDropZone'
import { uploadFile, confirmImport, getImportHistory } from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { getAccounts } from '@/lib/api'

export default function Import() {
  const queryClient = useQueryClient()
  const [uploadResponse, setUploadResponse] = useState<any>(null)
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [dateFormat, setDateFormat] = useState('%Y-%m-%d')
  const [columnMapping, setColumnMapping] = useState({
    date_col: 0,
    amount_col: 1,
    description_col: 2,
  })

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const { data: importHistory } = useQuery({
    queryKey: ['importHistory'],
    queryFn: getImportHistory,
  })

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (data) => {
      setUploadResponse(data)
    },
  })

  const confirmMutation = useMutation({
    mutationFn: ({ importId, data }: { importId: string; data: any }) =>
      confirmImport(importId, data),
    onSuccess: () => {
      setUploadResponse(null)
      queryClient.invalidateQueries({ queryKey: ['importHistory'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  const handleFileSelect = (file: File) => {
    uploadMutation.mutate(file)
  }

  const handleConfirm = () => {
    if (!uploadResponse || !selectedAccount) return

    confirmMutation.mutate({
      importId: uploadResponse.import_id,
      data: {
        account_id: selectedAccount,
        column_mapping: columnMapping,
        date_format: dateFormat,
      },
    })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Import Transactions</h1>

      {!uploadResponse ? (
        <FileDropZone
          onFileSelect={handleFileSelect}
          isUploading={uploadMutation.isPending}
        />
      ) : (
        <div className="space-y-4 p-4 border rounded-lg">
          <h2 className="text-lg font-semibold">Confirm Import</h2>
          <p className="text-sm text-gray-600">
            File: {uploadResponse.filename} ({uploadResponse.row_count} rows)
          </p>

          {/* Account Selection */}
          <div>
            <label className="block text-sm font-medium mb-1">Account</label>
            <select
              className="w-full border rounded p-2"
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
            >
              <option value="">Select account...</option>
              {accounts?.map((acc: any) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name}
                </option>
              ))}
            </select>
          </div>

          {/* Column Mapping */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Date Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.date_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, date_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.amount_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, amount_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.description_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, description_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Date Format */}
          <div>
            <label className="block text-sm font-medium mb-1">Date Format</label>
            <select
              className="w-full border rounded p-2"
              value={dateFormat}
              onChange={(e) => setDateFormat(e.target.value)}
            >
              <option value="%Y-%m-%d">YYYY-MM-DD</option>
              <option value="%m/%d/%Y">MM/DD/YYYY</option>
              <option value="%d/%m/%Y">DD/MM/YYYY</option>
              <option value="%m-%d-%Y">MM-DD-YYYY</option>
            </select>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium mb-1">Preview</label>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border">
                <thead>
                  <tr className="bg-gray-50">
                    {uploadResponse.headers.map((h: string, i: number) => (
                      <th key={i} className="px-2 py-1 border text-left">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uploadResponse.preview_rows.map((row: string[], i: number) => (
                    <tr key={i}>
                      {row.map((cell: string, j: number) => (
                        <td key={j} className="px-2 py-1 border">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setUploadResponse(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!selectedAccount || confirmMutation.isPending}
            >
              {confirmMutation.isPending ? 'Importing...' : `Import ${uploadResponse.row_count} Transactions`}
            </Button>
          </div>

          {confirmMutation.isSuccess && (
            <p className="text-green-600">Import successful!</p>
          )}
          {confirmMutation.isError && (
            <p className="text-red-600">Import failed. Please try again.</p>
          )}
        </div>
      )}

      {/* Import History */}
      <div>
        <h2 className="text-lg font-semibold mb-2">Recent Imports</h2>
        {importHistory && importHistory.length > 0 ? (
          <div className="space-y-2">
            {importHistory.map((log: any) => (
              <div key={log.id} className="p-3 border rounded flex justify-between items-center">
                <div>
                  <p className="font-medium">{log.filename}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(log.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-sm ${log.status === 'completed' ? 'text-green-600' : 'text-red-600'}`}>
                    {log.status}
                  </p>
                  <p className="text-sm text-gray-500">
                    {log.transactions_imported} imported, {log.transactions_skipped} skipped
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No imports yet</p>
        )}
      </div>
    </div>
  )
}
```

---

## Final Steps

After implementing all steps:

1. **Rebuild and restart:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

2. **Check for errors:**
   ```bash
   docker compose logs api --tail 50
   ```

3. **Test the endpoints:**
   ```bash
   # Health check
   curl http://localhost:8000/api/v1/health
   
   # Create a test account first
   curl -X POST http://localhost:8000/api/v1/accounts \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Checking","type":"bank"}'
   
   # Then test file upload (create a test.csv first)
   echo "Date,Amount,Description
   2025-01-01,-50.00,AMAZON PURCHASE
   2025-01-02,-25.00,STARBUCKS
   2025-01-03,1000.00,PAYROLL" > test.csv
   
   curl -X POST http://localhost:8000/api/v1/imports/upload \
     -F "file=@test.csv"
   ```

4. **Test the frontend:**
   - Go to http://localhost:5173
   - Navigate to Import page
   - Try uploading a file

---

## Do NOT Implement

- AI/LLM format detection (Phase 3)
- AI categorization (Phase 3)  
- Merchant name cleaning (Phase 3)
- learned_formats table population (Phase 3)

Just manual column mapping for now. AI comes later.
