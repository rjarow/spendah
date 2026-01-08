# Spendah - Phase 5a: Recurring Detection

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Backend - Recurring Schemas
- [ ] Step 2: Backend - Recurring Detection AI Prompt
- [ ] Step 3: Backend - Recurring Service
- [ ] Step 4: Backend - Recurring API Endpoints
- [ ] Step 5: Backend - Update Router
- [ ] Step 6: Frontend - Update API Client
- [ ] Step 7: Frontend - Update Types
- [ ] Step 8: Frontend - Recurring Page
- [ ] Step 9: Final - Rebuild and Test

## Files to Create/Modify

**CREATE:**
- `backend/app/ai/prompts/recurring_detection.py`
- `backend/app/schemas/recurring.py`
- `backend/app/services/recurring_service.py`
- `backend/app/api/recurring.py`

**MODIFY (add imports/routes):**
- `backend/app/ai/prompts/__init__.py` - Add recurring prompt exports
- `backend/app/api/router.py` - Add recurring router

**MODIFY (replace entirely):**
- `frontend/src/lib/api.ts` - Add recurring API functions
- `frontend/src/types/index.ts` - Add recurring types
- `frontend/src/pages/Recurring.tsx` - Full implementation

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture, AI prompts, and data models
2. `CLAUDE.md` - Project conventions

## Known Gotchas (from Phase 1-4)

1. **After model changes, generate migrations** - But we DON'T need migrations for Phase 5a, tables already exist!

2. **Never use SQLAlchemy reserved words:** `metadata`, `query`, `registry`, `type`

3. **API keys must be in docker-compose.yml environment section**

4. **Test after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   docker compose logs api --tail 30
   curl http://localhost:8000/api/v1/health
   ```

5. **Models already exist:** `RecurringGroup`, `Alert`, `AlertSettings` are defined in `backend/app/models/` - don't recreate them!

---

## Context

Phases 1-4 are complete. The app can:
- Import CSV/OFX files with AI format detection
- AI cleans merchant names and categorizes transactions
- Full transaction management with search, filters, bulk operations
- Dashboard with spending summaries and trends
- Settings page for AI provider configuration

**Database tables exist** for `recurring_groups` but no API endpoints or UI yet.

## Your Task: Phase 5a - Recurring Detection

Build the recurring transaction detection system:
- AI-powered detection of recurring charges from transaction history
- API to manage recurring groups
- UI to view and manage recurring charges

---

## Deliverables

### Step 1: Backend - Recurring Schemas

Create `backend/app/schemas/recurring.py`:

```python
"""Pydantic schemas for recurring groups."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Frequency(str, Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class RecurringGroupBase(BaseModel):
    name: str
    merchant_pattern: str
    expected_amount: Optional[Decimal] = None
    amount_variance: Optional[Decimal] = None
    frequency: Frequency
    category_id: Optional[str] = None


class RecurringGroupCreate(RecurringGroupBase):
    pass


class RecurringGroupUpdate(BaseModel):
    name: Optional[str] = None
    merchant_pattern: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    amount_variance: Optional[Decimal] = None
    frequency: Optional[Frequency] = None
    category_id: Optional[str] = None
    is_active: Optional[bool] = None


class RecurringGroupResponse(RecurringGroupBase):
    id: str
    last_seen_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    
    # Computed fields added by API
    transaction_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class RecurringGroupWithTransactions(RecurringGroupResponse):
    """Extended response with recent transaction IDs."""
    recent_transaction_ids: List[str] = []


class MarkRecurringRequest(BaseModel):
    """Request to mark a transaction as recurring."""
    recurring_group_id: Optional[str] = None  # Link to existing group
    create_new: bool = False  # Or create a new group
    # If create_new is True:
    name: Optional[str] = None
    frequency: Optional[Frequency] = None


class DetectionResult(BaseModel):
    """Result of recurring detection for a single pattern."""
    merchant_pattern: str
    suggested_name: str
    transaction_ids: List[str]
    frequency: Frequency
    average_amount: Decimal
    confidence: float


class DetectionResponse(BaseModel):
    """Response from recurring detection."""
    detected: List[DetectionResult]
    total_found: int
```

**Verify before continuing:**
```bash
docker compose restart api
docker compose logs api --tail 10
# Should show no import errors
```

---

### Step 2: Backend - Recurring Detection AI Prompt

Create `backend/app/ai/prompts/recurring_detection.py`:

```python
"""AI prompt for recurring transaction detection."""

RECURRING_DETECTION_SYSTEM = """You analyze financial transactions to identify recurring payments like subscriptions, bills, and regular charges.

Look for:
- Regular intervals (weekly, monthly, yearly)
- Similar amounts (within 15% variance)
- Same or similar merchant names
- Patterns suggesting subscriptions (streaming, software, utilities, memberships)

Respond with JSON only:
{
  "recurring_patterns": [
    {
      "merchant_pattern": "<merchant name or pattern to match>",
      "suggested_name": "<clean display name>",
      "transaction_ids": ["<uuid>", ...],
      "frequency": "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly",
      "average_amount": <number>,
      "confidence": <0.0 to 1.0>
    }
  ]
}

Guidelines:
- Only include patterns with 2+ transactions
- Confidence should reflect how certain the pattern is (consistent timing + amount = higher)
- Monthly is most common for subscriptions
- Yearly patterns need at least 2 occurrences roughly 12 months apart
- Include the transaction IDs that belong to this recurring group
- merchant_pattern should be specific enough to match future transactions"""

RECURRING_DETECTION_USER = """Analyze these transactions for recurring payment patterns:

{transactions_json}

Look for subscriptions, bills, and regular charges. Return patterns with confidence > 0.5 only."""
```

Update `backend/app/ai/prompts/__init__.py` to add the export:

```python
from app.ai.prompts.format_detection import FORMAT_DETECTION_SYSTEM, FORMAT_DETECTION_USER
from app.ai.prompts.categorization import CATEGORIZATION_SYSTEM, CATEGORIZATION_USER
from app.ai.prompts.merchant_cleaning import MERCHANT_CLEANING_SYSTEM, MERCHANT_CLEANING_USER
from app.ai.prompts.recurring_detection import RECURRING_DETECTION_SYSTEM, RECURRING_DETECTION_USER

__all__ = [
    'FORMAT_DETECTION_SYSTEM', 'FORMAT_DETECTION_USER',
    'CATEGORIZATION_SYSTEM', 'CATEGORIZATION_USER', 
    'MERCHANT_CLEANING_SYSTEM', 'MERCHANT_CLEANING_USER',
    'RECURRING_DETECTION_SYSTEM', 'RECURRING_DETECTION_USER',
]
```

**Verify before continuing:**
```bash
docker compose restart api
docker compose logs api --tail 10
# Should show no import errors
```

---

### Step 3: Backend - Recurring Service

Create `backend/app/services/recurring_service.py`:

```python
"""Service for recurring transaction detection and management."""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import uuid

from app.models.recurring import RecurringGroup, Frequency
from app.models.transaction import Transaction
from app.ai.client import get_ai_client
from app.ai.prompts import RECURRING_DETECTION_SYSTEM, RECURRING_DETECTION_USER
from app.config import settings


async def detect_recurring_patterns(db: Session) -> List[Dict[str, Any]]:
    """
    Use AI to detect recurring patterns in transaction history.
    Returns list of detected patterns with transaction IDs.
    """
    # Get transactions from last 12 months for analysis
    cutoff_date = date.today() - timedelta(days=365)
    
    transactions = db.query(Transaction).filter(
        Transaction.date >= cutoff_date,
        Transaction.amount < 0,  # Only expenses
        Transaction.recurring_group_id.is_(None)  # Not already marked as recurring
    ).order_by(Transaction.date.desc()).all()
    
    if len(transactions) < 5:
        return []
    
    # Prepare transaction data for AI
    txn_data = [
        {
            "id": str(t.id),
            "date": t.date.isoformat(),
            "amount": float(t.amount),
            "merchant": t.clean_merchant or t.raw_description,
            "raw_description": t.raw_description,
        }
        for t in transactions
    ]
    
    # Call AI for detection
    client = get_ai_client()
    
    user_prompt = RECURRING_DETECTION_USER.format(
        transactions_json=json.dumps(txn_data, indent=2)
    )
    
    try:
        result = await client.complete_json(
            system_prompt=RECURRING_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        patterns = result.get("recurring_patterns", [])
        # Filter to confidence > 0.5
        return [p for p in patterns if p.get("confidence", 0) > 0.5]
        
    except Exception as e:
        print(f"Recurring detection failed: {e}")
        return []


def create_recurring_group_from_detection(
    db: Session,
    detection: Dict[str, Any]
) -> RecurringGroup:
    """
    Create a recurring group from a detection result and link transactions.
    """
    # Create the group
    group = RecurringGroup(
        id=str(uuid.uuid4()),
        name=detection["suggested_name"],
        merchant_pattern=detection["merchant_pattern"],
        expected_amount=Decimal(str(abs(detection["average_amount"]))),
        amount_variance=Decimal("15.0"),  # Default 15% variance
        frequency=Frequency(detection["frequency"]),
        is_active=True,
    )
    db.add(group)
    
    # Link transactions to this group
    transaction_ids = detection.get("transaction_ids", [])
    if transaction_ids:
        db.query(Transaction).filter(
            Transaction.id.in_(transaction_ids)
        ).update(
            {Transaction.recurring_group_id: group.id, Transaction.is_recurring: True},
            synchronize_session=False
        )
        
        # Set last_seen_date from most recent transaction
        most_recent = db.query(func.max(Transaction.date)).filter(
            Transaction.id.in_(transaction_ids)
        ).scalar()
        if most_recent:
            group.last_seen_date = most_recent
            group.next_expected_date = calculate_next_expected(most_recent, group.frequency)
    
    db.commit()
    db.refresh(group)
    return group


def calculate_next_expected(last_date: date, frequency: Frequency) -> date:
    """Calculate the next expected date based on frequency."""
    if frequency == Frequency.weekly:
        return last_date + timedelta(days=7)
    elif frequency == Frequency.biweekly:
        return last_date + timedelta(days=14)
    elif frequency == Frequency.monthly:
        # Add roughly one month
        if last_date.month == 12:
            return date(last_date.year + 1, 1, last_date.day)
        else:
            try:
                return date(last_date.year, last_date.month + 1, last_date.day)
            except ValueError:
                # Handle months with fewer days
                return date(last_date.year, last_date.month + 1, 28)
    elif frequency == Frequency.quarterly:
        # Add 3 months
        new_month = last_date.month + 3
        new_year = last_date.year
        if new_month > 12:
            new_month -= 12
            new_year += 1
        try:
            return date(new_year, new_month, last_date.day)
        except ValueError:
            return date(new_year, new_month, 28)
    elif frequency == Frequency.yearly:
        return date(last_date.year + 1, last_date.month, last_date.day)
    else:
        return last_date + timedelta(days=30)


def get_recurring_groups(
    db: Session,
    include_inactive: bool = False
) -> List[RecurringGroup]:
    """Get all recurring groups with transaction counts."""
    query = db.query(RecurringGroup)
    
    if not include_inactive:
        query = query.filter(RecurringGroup.is_active == True)
    
    return query.order_by(RecurringGroup.name).all()


def get_group_transaction_count(db: Session, group_id: str) -> int:
    """Get count of transactions in a recurring group."""
    return db.query(Transaction).filter(
        Transaction.recurring_group_id == group_id
    ).count()


def mark_transaction_recurring(
    db: Session,
    transaction_id: str,
    recurring_group_id: Optional[str] = None,
    create_new: bool = False,
    new_name: Optional[str] = None,
    new_frequency: Optional[Frequency] = None
) -> RecurringGroup:
    """
    Mark a transaction as recurring, either linking to existing group or creating new.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")
    
    if recurring_group_id:
        # Link to existing group
        group = db.query(RecurringGroup).filter(RecurringGroup.id == recurring_group_id).first()
        if not group:
            raise ValueError(f"Recurring group {recurring_group_id} not found")
    elif create_new:
        # Create new group
        if not new_name:
            new_name = transaction.clean_merchant or transaction.raw_description
        if not new_frequency:
            new_frequency = Frequency.monthly
        
        group = RecurringGroup(
            id=str(uuid.uuid4()),
            name=new_name,
            merchant_pattern=transaction.clean_merchant or transaction.raw_description,
            expected_amount=abs(transaction.amount),
            amount_variance=Decimal("15.0"),
            frequency=new_frequency,
            is_active=True,
            last_seen_date=transaction.date,
            next_expected_date=calculate_next_expected(transaction.date, new_frequency),
        )
        db.add(group)
    else:
        raise ValueError("Must provide recurring_group_id or set create_new=True")
    
    # Link transaction
    transaction.recurring_group_id = group.id
    transaction.is_recurring = True
    
    # Update group's last_seen_date if this transaction is more recent
    if group.last_seen_date is None or transaction.date > group.last_seen_date:
        group.last_seen_date = transaction.date
        group.next_expected_date = calculate_next_expected(transaction.date, group.frequency)
    
    db.commit()
    db.refresh(group)
    return group


def unmark_transaction_recurring(db: Session, transaction_id: str) -> None:
    """Remove a transaction from its recurring group."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction:
        transaction.recurring_group_id = None
        transaction.is_recurring = False
        db.commit()
```

**Verify before continuing:**
```bash
docker compose restart api
docker compose logs api --tail 10
# Should show no import errors
```

---

### Step 4: Backend - Recurring API Endpoints

Create `backend/app/api/recurring.py`:

```python
"""API endpoints for recurring transaction management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.recurring import RecurringGroup
from app.schemas.recurring import (
    RecurringGroupResponse,
    RecurringGroupUpdate,
    RecurringGroupCreate,
    MarkRecurringRequest,
    DetectionResponse,
    DetectionResult,
)
from app.services import recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=List[RecurringGroupResponse])
def get_recurring_groups(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all recurring groups."""
    groups = recurring_service.get_recurring_groups(db, include_inactive)
    
    # Add transaction counts
    result = []
    for group in groups:
        response = RecurringGroupResponse.model_validate(group)
        response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
        result.append(response)
    
    return result


@router.get("/{group_id}", response_model=RecurringGroupResponse)
def get_recurring_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Get a single recurring group."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")
    
    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = recurring_service.get_group_transaction_count(db, group_id)
    return response


@router.post("", response_model=RecurringGroupResponse)
def create_recurring_group(
    data: RecurringGroupCreate,
    db: Session = Depends(get_db)
):
    """Manually create a recurring group."""
    import uuid
    
    group = RecurringGroup(
        id=str(uuid.uuid4()),
        name=data.name,
        merchant_pattern=data.merchant_pattern,
        expected_amount=data.expected_amount,
        amount_variance=data.amount_variance,
        frequency=data.frequency,
        category_id=data.category_id,
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = 0
    return response


@router.patch("/{group_id}", response_model=RecurringGroupResponse)
def update_recurring_group(
    group_id: str,
    update: RecurringGroupUpdate,
    db: Session = Depends(get_db)
):
    """Update a recurring group."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    
    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = recurring_service.get_group_transaction_count(db, group_id)
    return response


@router.delete("/{group_id}")
def delete_recurring_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Delete a recurring group (unlinks transactions but doesn't delete them)."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")
    
    # Unlink all transactions
    from app.models.transaction import Transaction
    db.query(Transaction).filter(
        Transaction.recurring_group_id == group_id
    ).update(
        {Transaction.recurring_group_id: None, Transaction.is_recurring: False},
        synchronize_session=False
    )
    
    db.delete(group)
    db.commit()
    
    return {"deleted": True}


@router.post("/detect", response_model=DetectionResponse)
async def detect_recurring(
    db: Session = Depends(get_db)
):
    """
    Use AI to detect recurring patterns in transaction history.
    Returns detected patterns without creating groups yet.
    """
    patterns = await recurring_service.detect_recurring_patterns(db)
    
    detected = [
        DetectionResult(
            merchant_pattern=p["merchant_pattern"],
            suggested_name=p["suggested_name"],
            transaction_ids=p.get("transaction_ids", []),
            frequency=p["frequency"],
            average_amount=abs(p["average_amount"]),
            confidence=p["confidence"],
        )
        for p in patterns
    ]
    
    return DetectionResponse(
        detected=detected,
        total_found=len(detected)
    )


@router.post("/detect/apply")
async def apply_detection(
    detection_index: int = Query(..., description="Index of detection to apply"),
    db: Session = Depends(get_db)
):
    """
    Apply a specific detection result - create the recurring group and link transactions.
    Run /detect first, then call this with the index of the pattern to apply.
    """
    # Re-run detection to get fresh results
    patterns = await recurring_service.detect_recurring_patterns(db)
    
    if detection_index < 0 or detection_index >= len(patterns):
        raise HTTPException(status_code=400, detail="Invalid detection index")
    
    detection = patterns[detection_index]
    group = recurring_service.create_recurring_group_from_detection(db, detection)
    
    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = len(detection.get("transaction_ids", []))
    return response


@router.post("/transactions/{transaction_id}/mark")
def mark_transaction_recurring(
    transaction_id: str,
    request: MarkRecurringRequest,
    db: Session = Depends(get_db)
):
    """Mark a transaction as recurring."""
    try:
        group = recurring_service.mark_transaction_recurring(
            db=db,
            transaction_id=transaction_id,
            recurring_group_id=request.recurring_group_id,
            create_new=request.create_new,
            new_name=request.name,
            new_frequency=request.frequency,
        )
        response = RecurringGroupResponse.model_validate(group)
        response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transactions/{transaction_id}/unmark")
def unmark_transaction_recurring(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Remove a transaction from its recurring group."""
    recurring_service.unmark_transaction_recurring(db, transaction_id)
    return {"success": True}
```

**Verify before continuing:**
```bash
docker compose restart api
docker compose logs api --tail 20
# Should show no import errors
```

---

### Step 5: Backend - Update Router

Update `backend/app/api/router.py` to include the recurring router:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router
from app.api.imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.recurring import router as recurring_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(imports_router)
api_router.include_router(transactions_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)
api_router.include_router(recurring_router)

@api_router.get("/health")
def health_check():
    from app.config import settings
    return {"status": "ok", "app_name": settings.APP_NAME}
```

**Verify before continuing:**
```bash
docker compose down
docker compose up -d --build
docker compose logs api --tail 30
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/recurring
# Should return empty array []
```

---

### Step 6: Frontend - Update API Client

Add the recurring functions to `frontend/src/lib/api.ts`. Add these to the existing file:

```typescript
// Recurring
export interface RecurringGroup {
  id: string
  name: string
  merchant_pattern: string
  expected_amount: number | null
  amount_variance: number | null
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'yearly'
  category_id: string | null
  last_seen_date: string | null
  next_expected_date: string | null
  is_active: boolean
  created_at: string
  transaction_count: number | null
}

export interface DetectionResult {
  merchant_pattern: string
  suggested_name: string
  transaction_ids: string[]
  frequency: string
  average_amount: number
  confidence: number
}

export interface DetectionResponse {
  detected: DetectionResult[]
  total_found: number
}

export async function getRecurringGroups(includeInactive: boolean = false) {
  const response = await api.get('/recurring', { params: { include_inactive: includeInactive } })
  return response.data as RecurringGroup[]
}

export async function getRecurringGroup(id: string) {
  const response = await api.get(`/recurring/${id}`)
  return response.data as RecurringGroup
}

export async function createRecurringGroup(data: {
  name: string
  merchant_pattern: string
  frequency: string
  expected_amount?: number
  category_id?: string
}) {
  const response = await api.post('/recurring', data)
  return response.data as RecurringGroup
}

export async function updateRecurringGroup(id: string, data: {
  name?: string
  merchant_pattern?: string
  frequency?: string
  expected_amount?: number
  is_active?: boolean
}) {
  const response = await api.patch(`/recurring/${id}`, data)
  return response.data as RecurringGroup
}

export async function deleteRecurringGroup(id: string) {
  const response = await api.delete(`/recurring/${id}`)
  return response.data
}

export async function detectRecurring() {
  const response = await api.post('/recurring/detect')
  return response.data as DetectionResponse
}

export async function applyDetection(detectionIndex: number) {
  const response = await api.post('/recurring/detect/apply', null, {
    params: { detection_index: detectionIndex }
  })
  return response.data as RecurringGroup
}

export async function markTransactionRecurring(transactionId: string, data: {
  recurring_group_id?: string
  create_new?: boolean
  name?: string
  frequency?: string
}) {
  const response = await api.post(`/recurring/transactions/${transactionId}/mark`, data)
  return response.data as RecurringGroup
}

export async function unmarkTransactionRecurring(transactionId: string) {
  const response = await api.post(`/recurring/transactions/${transactionId}/unmark`)
  return response.data
}
```

---

### Step 7: Frontend - Update Types

Add to `frontend/src/types/index.ts`:

```typescript
// Recurring types
export type Frequency = 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'yearly'

export interface RecurringGroup {
  id: string
  name: string
  merchant_pattern: string
  expected_amount: number | null
  amount_variance: number | null
  frequency: Frequency
  category_id: string | null
  last_seen_date: string | null
  next_expected_date: string | null
  is_active: boolean
  created_at: string
  transaction_count: number | null
}

export interface DetectionResult {
  merchant_pattern: string
  suggested_name: string
  transaction_ids: string[]
  frequency: Frequency
  average_amount: number
  confidence: number
}

export interface DetectionResponse {
  detected: DetectionResult[]
  total_found: number
}
```

---

### Step 8: Frontend - Recurring Page

Replace `frontend/src/pages/Recurring.tsx` entirely:

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRecurringGroups,
  detectRecurring,
  applyDetection,
  updateRecurringGroup,
  deleteRecurringGroup,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatDate } from '@/lib/formatters'

const FREQUENCY_LABELS: Record<string, string> = {
  weekly: 'Weekly',
  biweekly: 'Every 2 weeks',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
}

export default function Recurring() {
  const queryClient = useQueryClient()
  const [showInactive, setShowInactive] = useState(false)
  const [showDetection, setShowDetection] = useState(false)

  const { data: groups, isLoading } = useQuery({
    queryKey: ['recurring-groups', showInactive],
    queryFn: () => getRecurringGroups(showInactive),
  })

  const detectMutation = useMutation({
    mutationFn: detectRecurring,
    onSuccess: () => {
      setShowDetection(true)
    },
  })

  const applyMutation = useMutation({
    mutationFn: (index: number) => applyDetection(index),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
      detectMutation.reset()
      setShowDetection(false)
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateRecurringGroup(id, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRecurringGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
    },
  })

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Recurring Charges</h1>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
          <Button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
          >
            {detectMutation.isPending ? 'Detecting...' : '🔍 Detect Recurring'}
          </Button>
        </div>
      </div>

      {/* Detection Results */}
      {showDetection && detectMutation.data && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold">
              Detected {detectMutation.data.total_found} Recurring Pattern(s)
            </h2>
            <Button variant="outline" size="sm" onClick={() => setShowDetection(false)}>
              Dismiss
            </Button>
          </div>
          
          {detectMutation.data.detected.length === 0 ? (
            <p className="text-sm text-gray-600">No new recurring patterns found.</p>
          ) : (
            <div className="space-y-3">
              {detectMutation.data.detected.map((detection, index) => (
                <div
                  key={index}
                  className="bg-white rounded p-3 flex justify-between items-center"
                >
                  <div>
                    <div className="font-medium">{detection.suggested_name}</div>
                    <div className="text-sm text-gray-500">
                      {formatCurrency(detection.average_amount)} • {FREQUENCY_LABELS[detection.frequency]}
                      • {detection.transaction_ids.length} transactions
                      • {Math.round(detection.confidence * 100)}% confidence
                    </div>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyMutation.mutate(index)}
                    disabled={applyMutation.isPending}
                  >
                    Add
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary */}
      {groups && groups.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">{groups.filter(g => g.is_active).length}</div>
              <div className="text-sm text-gray-500">Active Subscriptions</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {formatCurrency(
                  groups
                    .filter(g => g.is_active && g.frequency === 'monthly')
                    .reduce((sum, g) => sum + (g.expected_amount || 0), 0)
                )}
              </div>
              <div className="text-sm text-gray-500">Monthly Total</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {formatCurrency(
                  groups
                    .filter(g => g.is_active)
                    .reduce((sum, g) => {
                      const amount = g.expected_amount || 0
                      switch (g.frequency) {
                        case 'weekly': return sum + amount * 52
                        case 'biweekly': return sum + amount * 26
                        case 'monthly': return sum + amount * 12
                        case 'quarterly': return sum + amount * 4
                        case 'yearly': return sum + amount
                        default: return sum + amount * 12
                      }
                    }, 0)
                )}
              </div>
              <div className="text-sm text-gray-500">Yearly Total</div>
            </div>
          </div>
        </div>
      )}

      {/* Recurring Groups List */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Name</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Amount</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Frequency</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Last Seen</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Next Expected</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Transactions</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {groups?.map((group) => (
              <tr
                key={group.id}
                className={`border-t ${!group.is_active ? 'opacity-50 bg-gray-50' : ''}`}
              >
                <td className="px-4 py-3">
                  <div className="font-medium">{group.name}</div>
                  <div className="text-xs text-gray-500">{group.merchant_pattern}</div>
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.expected_amount ? formatCurrency(group.expected_amount) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {FREQUENCY_LABELS[group.frequency] || group.frequency}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.last_seen_date ? formatDate(group.last_seen_date) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.next_expected_date ? formatDate(group.next_expected_date) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.transaction_count || 0}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex gap-1 justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        toggleActiveMutation.mutate({
                          id: group.id,
                          isActive: !group.is_active,
                        })
                      }
                    >
                      {group.is_active ? 'Pause' : 'Resume'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (confirm('Delete this recurring group? Transactions will be unlinked.')) {
                          deleteMutation.mutate(group.id)
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {(!groups || groups.length === 0) && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  No recurring charges yet. Click "Detect Recurring" to find patterns in your transactions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

---

### Step 9: Final - Rebuild and Test

```bash
# Rebuild everything
docker compose down
docker compose up -d --build

# Check for errors
docker compose logs api --tail 50
docker compose logs frontend --tail 20

# Test the API endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/recurring

# Test detection (requires transactions in DB)
curl -X POST http://localhost:8000/api/v1/recurring/detect
```

**Test the UI:**
1. Go to http://localhost:5173/recurring
2. Should see empty state with "Detect Recurring" button
3. Click "Detect Recurring" - should call AI and show results
4. Click "Add" on a detection to create the group
5. Group should appear in the table with transaction count

---

## Verification Checklist

- [ ] `GET /api/v1/recurring` returns empty array (or list if groups exist)
- [ ] `POST /api/v1/recurring/detect` calls AI and returns detected patterns
- [ ] Detection results show merchant, amount, frequency, confidence
- [ ] "Add" button creates group and links transactions
- [ ] Groups list shows name, amount, frequency, dates, transaction count
- [ ] "Pause" button toggles is_active
- [ ] "Delete" button removes group (with confirmation)
- [ ] "Show inactive" checkbox toggles inactive groups visibility
- [ ] Summary shows active count, monthly total, yearly total
- [ ] No console errors in browser
- [ ] No errors in API logs

---

## Do NOT Implement Yet (Phase 5b)

- Alerts system
- Alert bell UI component
- Insights page
- Large purchase detection
- Price increase detection
- Anomaly detection on import

Focus on getting recurring detection working first.
