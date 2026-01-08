# Spendah - Phase 5b: Alerts System

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Backend - Alert Schemas
- [ ] Step 2: Backend - Alert Detection Prompts
- [ ] Step 3: Backend - Alerts Service
- [ ] Step 4: Backend - Alerts API Endpoints
- [ ] Step 5: Backend - Integrate Alerts into Import Flow
- [ ] Step 6: Backend - Update Router
- [ ] Step 7: Frontend - Update API Client
- [ ] Step 8: Frontend - Update Types
- [ ] Step 9: Frontend - Alert Bell Component
- [ ] Step 10: Frontend - Alerts/Insights Page
- [ ] Step 11: Frontend - Add Alert Bell to Layout
- [ ] Step 12: Final - Rebuild and Test

## Files to Create/Modify

**CREATE:**
- `backend/app/schemas/alert.py`
- `backend/app/ai/prompts/anomaly_detection.py`
- `backend/app/services/alerts_service.py`
- `backend/app/api/alerts.py`
- `frontend/src/components/alerts/AlertBell.tsx`
- `frontend/src/pages/Insights.tsx` (replace placeholder)

**MODIFY:**
- `backend/app/ai/prompts/__init__.py` - Add anomaly prompt exports
- `backend/app/api/router.py` - Add alerts router
- `backend/app/services/import_service.py` - Add alert creation on import
- `frontend/src/lib/api.ts` - Add alert API functions
- `frontend/src/types/index.ts` - Add alert types
- `frontend/src/components/layout/Layout.tsx` - Add AlertBell to header

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture, alert types, and data models
2. `HANDOFF.md` - Current project state
3. `backend/app/models/alert.py` - Existing alert model

## Known Gotchas (from Phase 1-5a)

1. **Tables already exist:** `alerts` and `alert_settings` tables exist - don't recreate
2. **Use `OPENROUTER_API_KEY`** not `OPENAI_API_KEY` for OpenRouter
3. **Test data is from 2024** - detection lookback extended to 3 years
4. **Always restart after code changes:**
   ```bash
   cd ~/projects/spendah
   docker compose down
   docker compose up -d --build
   ```

---

## Context

Phase 5a (Recurring Detection) is complete. The app can:
- Import CSV/OFX files with AI categorization
- Detect and manage recurring charges
- Full transaction and dashboard functionality

**Alert tables exist** but no API endpoints or UI yet.

## Your Task: Phase 5b - Alerts System

Build the alerts and insights system:
- Detect anomalies during import (large purchases, price increases)
- Alert bell UI with unread count
- Alerts/Insights page to view and manage alerts
- Alert settings for thresholds

---

## Deliverables

### Step 1: Backend - Alert Schemas

Create `backend/app/schemas/alert.py`:

```python
"""Pydantic schemas for alerts."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AlertType(str, Enum):
    large_purchase = "large_purchase"
    price_increase = "price_increase"
    new_recurring = "new_recurring"
    unusual_merchant = "unusual_merchant"
    annual_charge = "annual_charge"


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    attention = "attention"


class AlertBase(BaseModel):
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    transaction_id: Optional[str] = None
    recurring_group_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None
    action_taken: Optional[str] = None


class AlertResponse(AlertBase):
    id: str
    is_read: bool
    is_dismissed: bool
    action_taken: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertsListResponse(BaseModel):
    items: List[AlertResponse]
    unread_count: int
    total: int


class UnreadCountResponse(BaseModel):
    count: int


class AlertSettingsBase(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: float = 3.0
    unusual_merchant_threshold: float = 200.0
    alerts_enabled: bool = True


class AlertSettingsUpdate(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: Optional[float] = None
    unusual_merchant_threshold: Optional[float] = None
    alerts_enabled: Optional[bool] = None


class AlertSettingsResponse(AlertSettingsBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 2: Backend - Anomaly Detection Prompt

Create `backend/app/ai/prompts/anomaly_detection.py`:

```python
"""AI prompt for anomaly detection in transactions."""

ANOMALY_DETECTION_SYSTEM = """You analyze financial transactions to detect anomalies and unusual spending patterns.

You will receive:
1. A new transaction to analyze
2. Historical spending averages by category
3. Known recurring charges and their typical amounts

Flag the transaction if ANY of these apply:
- Amount is significantly higher than category average (use the multiplier threshold provided)
- First-time merchant with amount over the unusual merchant threshold
- Price increase on a known recurring charge (compare to previous amount)

Respond with JSON only:
{
  "is_anomaly": true/false,
  "anomaly_type": "large_purchase" | "unusual_merchant" | "price_increase" | null,
  "severity": "info" | "warning" | "attention",
  "title": "<short headline, max 50 chars>",
  "explanation": "<human readable explanation, 1-2 sentences>",
  "comparisons": {
    "category_avg": <number or null>,
    "multiplier": <number or null>,
    "previous_amount": <number or null>,
    "price_change": <number or null>
  }
}

Severity guidelines:
- "info": Minor anomaly, FYI only (e.g., slightly above average)
- "warning": Notable anomaly, worth reviewing (e.g., 2-3x average)
- "attention": Significant anomaly, needs attention (e.g., 5x+ average, large price increase)

If not an anomaly, return:
{"is_anomaly": false}"""

ANOMALY_DETECTION_USER = """Analyze this transaction for anomalies:

Transaction:
- Merchant: {merchant}
- Amount: ${amount}
- Category: {category}
- Date: {date}

Category spending average (last 3 months): ${category_avg}
Large purchase multiplier threshold: {multiplier}x
Unusual merchant threshold: ${unusual_threshold}

Known recurring charges for similar merchant:
{recurring_info}

First time seeing this merchant: {is_first_time}

Is this transaction anomalous?"""
```

Update `backend/app/ai/prompts/__init__.py`:

```python
from app.ai.prompts.format_detection import FORMAT_DETECTION_SYSTEM, FORMAT_DETECTION_USER
from app.ai.prompts.categorization import CATEGORIZATION_SYSTEM, CATEGORIZATION_USER
from app.ai.prompts.merchant_cleaning import MERCHANT_CLEANING_SYSTEM, MERCHANT_CLEANING_USER
from app.ai.prompts.recurring_detection import RECURRING_DETECTION_SYSTEM, RECURRING_DETECTION_USER
from app.ai.prompts.anomaly_detection import ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER

__all__ = [
    'FORMAT_DETECTION_SYSTEM', 'FORMAT_DETECTION_USER',
    'CATEGORIZATION_SYSTEM', 'CATEGORIZATION_USER',
    'MERCHANT_CLEANING_SYSTEM', 'MERCHANT_CLEANING_USER',
    'RECURRING_DETECTION_SYSTEM', 'RECURRING_DETECTION_USER',
    'ANOMALY_DETECTION_SYSTEM', 'ANOMALY_DETECTION_USER',
]
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 3: Backend - Alerts Service

Create `backend/app/services/alerts_service.py`:

```python
"""Service for alert detection and management."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from app.models.alert import Alert, AlertType, AlertSeverity, AlertSettings
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup
from app.models.category import Category
from app.ai.client import get_ai_client
from app.ai.prompts import ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER


def get_or_create_settings(db: Session) -> AlertSettings:
    """Get alert settings, creating default if none exist."""
    settings = db.query(AlertSettings).first()
    if not settings:
        settings = AlertSettings(
            id=str(uuid.uuid4()),
            large_purchase_multiplier=Decimal("3.0"),
            unusual_merchant_threshold=Decimal("200.0"),
            alerts_enabled=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_category_average(db: Session, category_id: str, months: int = 3) -> float:
    """Get average spending for a category over the last N months."""
    cutoff = datetime.now() - timedelta(days=months * 30)
    
    result = db.query(func.avg(func.abs(Transaction.amount))).filter(
        Transaction.category_id == category_id,
        Transaction.amount < 0,
        Transaction.date >= cutoff.date()
    ).scalar()
    
    return float(result) if result else 0.0


def is_first_time_merchant(db: Session, merchant: str, exclude_txn_id: str = None) -> bool:
    """Check if this is the first transaction from this merchant."""
    query = db.query(Transaction).filter(
        Transaction.clean_merchant == merchant
    )
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    return query.count() == 0


def get_recurring_for_merchant(db: Session, merchant: str) -> Optional[RecurringGroup]:
    """Find recurring group matching this merchant."""
    # Simple pattern match - could be improved with fuzzy matching
    return db.query(RecurringGroup).filter(
        RecurringGroup.merchant_pattern.ilike(f"%{merchant}%"),
        RecurringGroup.is_active == True
    ).first()


def check_price_increase(
    db: Session, 
    merchant: str, 
    new_amount: float,
    recurring_group: Optional[RecurringGroup]
) -> Optional[Dict[str, Any]]:
    """Check if this transaction represents a price increase from a recurring charge."""
    if not recurring_group:
        return None
    
    if recurring_group.expected_amount:
        old_amount = float(recurring_group.expected_amount)
        if new_amount > old_amount * 1.05:  # 5% threshold for price increase
            return {
                "previous_amount": old_amount,
                "new_amount": new_amount,
                "increase": new_amount - old_amount,
                "percent_increase": ((new_amount - old_amount) / old_amount) * 100
            }
    
    return None


async def analyze_transaction_for_alerts(
    db: Session,
    transaction: Transaction
) -> Optional[Alert]:
    """
    Analyze a transaction for anomalies and create an alert if needed.
    Uses AI for complex analysis, rule-based for simple checks.
    """
    settings = get_or_create_settings(db)
    
    if not settings.alerts_enabled:
        return None
    
    amount = abs(float(transaction.amount))
    merchant = transaction.clean_merchant or transaction.raw_description
    
    # Get context
    category_avg = get_category_average(db, transaction.category_id) if transaction.category_id else 0
    is_new_merchant = is_first_time_merchant(db, merchant, transaction.id)
    recurring = get_recurring_for_merchant(db, merchant)
    price_increase = check_price_increase(db, merchant, amount, recurring)
    
    # Rule-based checks first (faster, no AI needed)
    
    # Check 1: Price increase on recurring
    if price_increase:
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.price_increase,
            severity=AlertSeverity.warning,
            title=f"Price increase: {merchant}",
            description=f"Was ${price_increase['previous_amount']:.2f}/mo → Now ${price_increase['new_amount']:.2f}/mo (+${price_increase['increase']:.2f})",
            transaction_id=str(transaction.id),
            recurring_group_id=str(recurring.id) if recurring else None,
            metadata={
                "previous_amount": price_increase['previous_amount'],
                "new_amount": price_increase['new_amount'],
                "increase": price_increase['increase'],
                "percent_increase": price_increase['percent_increase']
            }
        )
        db.add(alert)
        db.commit()
        return alert
    
    # Check 2: Large purchase (rule-based)
    multiplier = float(settings.large_purchase_multiplier)
    if category_avg > 0 and amount > category_avg * multiplier:
        actual_multiplier = amount / category_avg
        severity = AlertSeverity.attention if actual_multiplier > 5 else AlertSeverity.warning
        
        # Get category name
        category = db.query(Category).filter(Category.id == transaction.category_id).first()
        category_name = category.name if category else "this category"
        
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=severity,
            title=f"Large purchase: {merchant}",
            description=f"${amount:.2f} is {actual_multiplier:.1f}x your usual {category_name} spending of ${category_avg:.2f}",
            transaction_id=str(transaction.id),
            metadata={
                "amount": amount,
                "category_avg": category_avg,
                "multiplier": actual_multiplier
            }
        )
        db.add(alert)
        db.commit()
        return alert
    
    # Check 3: Unusual merchant (first time, high amount)
    unusual_threshold = float(settings.unusual_merchant_threshold)
    if is_new_merchant and amount > unusual_threshold:
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.unusual_merchant,
            severity=AlertSeverity.info,
            title=f"New merchant: {merchant}",
            description=f"First purchase at {merchant}: ${amount:.2f}",
            transaction_id=str(transaction.id),
            metadata={
                "amount": amount,
                "threshold": unusual_threshold,
                "is_first_time": True
            }
        )
        db.add(alert)
        db.commit()
        return alert
    
    return None


def get_alerts(
    db: Session,
    is_read: Optional[bool] = None,
    is_dismissed: Optional[bool] = None,
    alert_type: Optional[str] = None,
    limit: int = 50
) -> List[Alert]:
    """Get alerts with optional filters."""
    query = db.query(Alert)
    
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    
    if is_dismissed is not None:
        query = query.filter(Alert.is_dismissed == is_dismissed)
    else:
        # Default: hide dismissed
        query = query.filter(Alert.is_dismissed == False)
    
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


def get_unread_count(db: Session) -> int:
    """Get count of unread, non-dismissed alerts."""
    return db.query(Alert).filter(
        Alert.is_read == False,
        Alert.is_dismissed == False
    ).count()


def mark_all_read(db: Session) -> int:
    """Mark all alerts as read. Returns count updated."""
    result = db.query(Alert).filter(
        Alert.is_read == False
    ).update({Alert.is_read: True})
    db.commit()
    return result


def create_new_recurring_alert(db: Session, recurring_group: RecurringGroup) -> Alert:
    """Create an alert for a newly detected recurring charge."""
    alert = Alert(
        id=str(uuid.uuid4()),
        type=AlertType.new_recurring,
        severity=AlertSeverity.info,
        title=f"New subscription: {recurring_group.name}",
        description=f"Detected new recurring charge: ${recurring_group.expected_amount:.2f}/{recurring_group.frequency.value}",
        recurring_group_id=str(recurring_group.id),
        metadata={
            "amount": float(recurring_group.expected_amount) if recurring_group.expected_amount else None,
            "frequency": recurring_group.frequency.value
        }
    )
    db.add(alert)
    db.commit()
    return alert
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 4: Backend - Alerts API Endpoints

Create `backend/app/api/alerts.py`:

```python
"""API endpoints for alerts management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.alert import Alert, AlertSettings
from app.schemas.alert import (
    AlertResponse,
    AlertsListResponse,
    AlertUpdate,
    UnreadCountResponse,
    AlertSettingsResponse,
    AlertSettingsUpdate,
)
from app.services import alerts_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsListResponse)
def get_alerts(
    is_read: Optional[bool] = Query(None),
    is_dismissed: Optional[bool] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get alerts with optional filters."""
    alerts = alerts_service.get_alerts(
        db,
        is_read=is_read,
        is_dismissed=is_dismissed,
        alert_type=type,
        limit=limit
    )
    unread_count = alerts_service.get_unread_count(db)
    
    return AlertsListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        unread_count=unread_count,
        total=len(alerts)
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(db: Session = Depends(get_db)):
    """Get count of unread alerts."""
    count = alerts_service.get_unread_count(db)
    return UnreadCountResponse(count=count)


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert (mark read, dismiss, record action)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    return AlertResponse.model_validate(alert)


@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db)):
    """Mark all alerts as read."""
    count = alerts_service.mark_all_read(db)
    return {"marked_read": count}


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Permanently delete an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    
    return {"deleted": True}


@router.get("/settings", response_model=AlertSettingsResponse)
def get_alert_settings(db: Session = Depends(get_db)):
    """Get alert settings."""
    settings = alerts_service.get_or_create_settings(db)
    return AlertSettingsResponse.model_validate(settings)


@router.patch("/settings", response_model=AlertSettingsResponse)
def update_alert_settings(
    update: AlertSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update alert settings."""
    settings = alerts_service.get_or_create_settings(db)
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.now()
    db.commit()
    db.refresh(settings)
    
    return AlertSettingsResponse.model_validate(settings)
```

Add missing import at top of file:
```python
from datetime import datetime
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 5: Backend - Integrate Alerts into Import Flow

Update `backend/app/services/import_service.py` to check for alerts after importing transactions.

Add import at top:
```python
from app.services.alerts_service import analyze_transaction_for_alerts
```

In the `process_import_with_ai` function, after creating each transaction and before `db.commit()`, add:

```python
# After: db.add(transaction)
# Add this:
try:
    await analyze_transaction_for_alerts(db, transaction)
except Exception as e:
    print(f"Alert analysis failed for transaction: {e}")
    # Don't fail import if alert analysis fails
```

**Note:** This is a simple integration. For production, you might want to batch alert analysis or run it asynchronously.

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 6: Backend - Update Router

Update `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router
from app.api.imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.recurring import router as recurring_router
from app.api.alerts import router as alerts_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(imports_router)
api_router.include_router(transactions_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)
api_router.include_router(recurring_router)
api_router.include_router(alerts_router)

@api_router.get("/health")
def health_check():
    from app.config import settings
    return {"status": "ok", "app_name": settings.APP_NAME}
```

**Verify:**
```bash
docker compose down
docker compose up -d --build
sleep 5
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/alerts
curl http://localhost:8000/api/v1/alerts/unread-count
```

---

### Step 7: Frontend - Update API Client

Add to `frontend/src/lib/api.ts`:

```typescript
// Alerts
export interface Alert {
  id: string
  type: 'large_purchase' | 'price_increase' | 'new_recurring' | 'unusual_merchant' | 'annual_charge'
  severity: 'info' | 'warning' | 'attention'
  title: string
  description: string
  transaction_id: string | null
  recurring_group_id: string | null
  metadata: Record<string, any> | null
  is_read: boolean
  is_dismissed: boolean
  action_taken: string | null
  created_at: string
}

export interface AlertsListResponse {
  items: Alert[]
  unread_count: number
  total: number
}

export interface AlertSettings {
  id: string
  large_purchase_threshold: number | null
  large_purchase_multiplier: number
  unusual_merchant_threshold: number
  alerts_enabled: boolean
  created_at: string
  updated_at: string | null
}

export async function getAlerts(params?: {
  is_read?: boolean
  is_dismissed?: boolean
  type?: string
  limit?: number
}) {
  const response = await api.get('/alerts', { params })
  return response.data as AlertsListResponse
}

export async function getUnreadCount() {
  const response = await api.get('/alerts/unread-count')
  return response.data as { count: number }
}

export async function updateAlert(id: string, data: {
  is_read?: boolean
  is_dismissed?: boolean
  action_taken?: string
}) {
  const response = await api.patch(`/alerts/${id}`, data)
  return response.data as Alert
}

export async function markAllAlertsRead() {
  const response = await api.post('/alerts/mark-all-read')
  return response.data
}

export async function deleteAlert(id: string) {
  const response = await api.delete(`/alerts/${id}`)
  return response.data
}

export async function getAlertSettings() {
  const response = await api.get('/alerts/settings')
  return response.data as AlertSettings
}

export async function updateAlertSettings(data: {
  large_purchase_threshold?: number | null
  large_purchase_multiplier?: number
  unusual_merchant_threshold?: number
  alerts_enabled?: boolean
}) {
  const response = await api.patch('/alerts/settings', data)
  return response.data as AlertSettings
}
```

---

### Step 8: Frontend - Update Types

Add to `frontend/src/types/index.ts`:

```typescript
// Alert types
export type AlertType = 'large_purchase' | 'price_increase' | 'new_recurring' | 'unusual_merchant' | 'annual_charge'
export type AlertSeverity = 'info' | 'warning' | 'attention'

export interface Alert {
  id: string
  type: AlertType
  severity: AlertSeverity
  title: string
  description: string
  transaction_id: string | null
  recurring_group_id: string | null
  metadata: Record<string, any> | null
  is_read: boolean
  is_dismissed: boolean
  action_taken: string | null
  created_at: string
}

export interface AlertsListResponse {
  items: Alert[]
  unread_count: number
  total: number
}

export interface AlertSettings {
  id: string
  large_purchase_threshold: number | null
  large_purchase_multiplier: number
  unusual_merchant_threshold: number
  alerts_enabled: boolean
  created_at: string
  updated_at: string | null
}
```

---

### Step 9: Frontend - Alert Bell Component

Create `frontend/src/components/alerts/AlertBell.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, updateAlert, markAllAlertsRead } from '@/lib/api'
import { Link } from 'react-router-dom'

const SEVERITY_STYLES = {
  info: 'bg-blue-50 border-blue-200',
  warning: 'bg-yellow-50 border-yellow-200',
  attention: 'bg-red-50 border-red-200',
}

const SEVERITY_ICONS = {
  info: 'ℹ️',
  warning: '⚡',
  attention: '⚠️',
}

export default function AlertBell() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: alertsData } = useQuery({
    queryKey: ['alerts', { limit: 5 }],
    queryFn: () => getAlerts({ limit: 5, is_dismissed: false }),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => updateAlert(id, { is_read: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: markAllAlertsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = alertsData?.unread_count || 0
  const alerts = alertsData?.items || []

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full"
      >
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
          <div className="p-3 border-b flex justify-between items-center">
            <span className="font-semibold">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllReadMutation.mutate()}
                className="text-xs text-blue-600 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No notifications
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 ${
                    !alert.is_read ? 'bg-blue-50/50' : ''
                  }`}
                  onClick={() => {
                    if (!alert.is_read) {
                      markReadMutation.mutate(alert.id)
                    }
                  }}
                >
                  <div className="flex gap-2">
                    <span>{SEVERITY_ICONS[alert.severity]}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {alert.title}
                      </div>
                      <div className="text-xs text-gray-600 line-clamp-2">
                        {alert.description}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(alert.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    {!alert.is_read && (
                      <span className="h-2 w-2 bg-blue-500 rounded-full flex-shrink-0 mt-1" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-2 border-t">
            <Link
              to="/insights"
              className="block text-center text-sm text-blue-600 hover:underline"
              onClick={() => setIsOpen(false)}
            >
              View all alerts →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

### Step 10: Frontend - Alerts/Insights Page

Replace `frontend/src/pages/Insights.tsx`:

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, updateAlert, deleteAlert, getAlertSettings, updateAlertSettings } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency } from '@/lib/formatters'

const SEVERITY_STYLES = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  attention: 'bg-red-50 border-red-200 text-red-800',
}

const SEVERITY_LABELS = {
  info: 'ℹ️ INFO',
  warning: '⚡ WARNING',
  attention: '⚠️ ATTENTION',
}

const TYPE_LABELS = {
  large_purchase: 'Large Purchase',
  price_increase: 'Price Increase',
  new_recurring: 'New Subscription',
  unusual_merchant: 'New Merchant',
  annual_charge: 'Annual Charge',
}

export default function Insights() {
  const queryClient = useQueryClient()
  const [showDismissed, setShowDismissed] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts', { is_dismissed: showDismissed ? undefined : false }],
    queryFn: () => getAlerts({ 
      is_dismissed: showDismissed ? undefined : false,
      limit: 100 
    }),
  })

  const { data: settings } = useQuery({
    queryKey: ['alert-settings'],
    queryFn: getAlertSettings,
  })

  const dismissMutation = useMutation({
    mutationFn: (id: string) => updateAlert(id, { is_dismissed: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const updateSettingsMutation = useMutation({
    mutationFn: updateAlertSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-settings'] })
    },
  })

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  const alerts = alertsData?.items || []
  const unreadCount = alertsData?.unread_count || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Insights & Alerts</h1>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500">{unreadCount} unread</p>
          )}
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showDismissed}
              onChange={(e) => setShowDismissed(e.target.checked)}
              className="rounded"
            />
            Show dismissed
          </label>
          <Button
            variant="outline"
            onClick={() => setShowSettings(!showSettings)}
          >
            ⚙️ Settings
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && settings && (
        <div className="bg-gray-50 border rounded-lg p-4 space-y-4">
          <h2 className="font-semibold">Alert Settings</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Large Purchase Multiplier
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                className="border rounded px-3 py-2 w-full"
                value={settings.large_purchase_multiplier}
                onChange={(e) => updateSettingsMutation.mutate({
                  large_purchase_multiplier: parseFloat(e.target.value)
                })}
              />
              <p className="text-xs text-gray-500 mt-1">
                Alert when purchase exceeds Nx category average
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                New Merchant Threshold
              </label>
              <input
                type="number"
                step="50"
                min="0"
                className="border rounded px-3 py-2 w-full"
                value={settings.unusual_merchant_threshold}
                onChange={(e) => updateSettingsMutation.mutate({
                  unusual_merchant_threshold: parseFloat(e.target.value)
                })}
              />
              <p className="text-xs text-gray-500 mt-1">
                Alert for first-time merchants over this amount
              </p>
            </div>
          </div>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings.alerts_enabled}
              onChange={(e) => updateSettingsMutation.mutate({
                alerts_enabled: e.target.checked
              })}
              className="rounded"
            />
            <span className="text-sm">Enable alerts</span>
          </label>
        </div>
      )}

      {/* Alerts List */}
      <div className="space-y-4">
        {alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-4xl mb-2">🎉</p>
            <p>No alerts! Everything looks good.</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-4 ${SEVERITY_STYLES[alert.severity]} ${
                alert.is_dismissed ? 'opacity-50' : ''
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs font-medium mb-1">
                    {SEVERITY_LABELS[alert.severity]}
                  </div>
                  <div className="font-semibold">{alert.title}</div>
                  <div className="text-sm mt-1">{alert.description}</div>
                  <div className="text-xs mt-2 opacity-75">
                    {TYPE_LABELS[alert.type]} • {new Date(alert.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {!alert.is_dismissed && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => dismissMutation.mutate(alert.id)}
                    >
                      Dismiss
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (confirm('Delete this alert permanently?')) {
                        deleteMutation.mutate(alert.id)
                      }
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
```

---

### Step 11: Frontend - Add Alert Bell to Layout

Update `frontend/src/components/layout/Layout.tsx` to include the AlertBell.

Add import:
```tsx
import AlertBell from '@/components/alerts/AlertBell'
```

Add AlertBell to the header area (near the settings link):
```tsx
<div className="flex items-center gap-4">
  <AlertBell />
  {/* existing settings link or other header items */}
</div>
```

The exact placement depends on your current Layout structure. The AlertBell should be in the top-right header area.

---

### Step 12: Final - Rebuild and Test

```bash
# Full rebuild
cd ~/projects/spendah
docker compose down
docker compose up -d --build
sleep 5

# Check for errors
docker compose logs api --tail 50
docker compose logs frontend --tail 20

# Test API endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/alerts
curl http://localhost:8000/api/v1/alerts/unread-count
curl http://localhost:8000/api/v1/alerts/settings
```

**Test the full flow:**

1. **Create a test alert manually:**
```bash
# This tests that alerts table works
docker compose exec api python -c "
from app.database import SessionLocal
from app.models.alert import Alert, AlertType, AlertSeverity
import uuid

db = SessionLocal()
alert = Alert(
    id=str(uuid.uuid4()),
    type=AlertType.large_purchase,
    severity=AlertSeverity.attention,
    title='Test Alert: Large Purchase',
    description='This is a test alert to verify the system works.',
    metadata={'test': True}
)
db.add(alert)
db.commit()
print(f'Created test alert: {alert.id}')
db.close()
"
```

2. **Verify in UI:**
   - http://localhost:5173 - Should see alert bell with badge showing "1"
   - Click bell - Should see dropdown with test alert
   - Click "View all alerts" - Should go to Insights page
   - Insights page should show the test alert
   - Settings panel should allow changing thresholds

3. **Test import-triggered alerts:**
   - Import a new CSV with a large purchase (>3x category average)
   - Should create an alert automatically

---

## Verification Checklist

- [ ] `GET /api/v1/alerts` returns alert list
- [ ] `GET /api/v1/alerts/unread-count` returns count
- [ ] `PATCH /api/v1/alerts/{id}` updates alert (mark read, dismiss)
- [ ] `GET /api/v1/alerts/settings` returns settings
- [ ] `PATCH /api/v1/alerts/settings` updates settings
- [ ] Alert bell shows in header
- [ ] Alert bell shows unread count badge
- [ ] Alert dropdown shows recent alerts
- [ ] Clicking alert marks it as read
- [ ] "View all alerts" links to Insights page
- [ ] Insights page lists all alerts
- [ ] Can dismiss and delete alerts
- [ ] Settings panel allows threshold configuration
- [ ] No console errors in browser
- [ ] No errors in API logs

---

## Do NOT Implement Yet (Phase 6)

- Subscription review AI prompt
- Annual charge detection/prediction
- Subscription review modal
- Scheduled review triggers

Focus on getting the core alert system working first.
