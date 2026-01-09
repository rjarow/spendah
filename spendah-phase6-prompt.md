# Spendah - Phase 6: Subscription Intelligence

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Backend - Update Alert Schemas for Subscription Features
- [ ] Step 2: Backend - Subscription Review AI Prompt
- [ ] Step 3: Backend - Annual Charge Detection Prompt
- [ ] Step 4: Backend - Update Alerts Service for Subscriptions
- [ ] Step 5: Backend - Subscription Review API Endpoints
- [ ] Step 6: Backend - Update Alert Settings Model (if needed)
- [ ] Step 7: Frontend - Update API Client
- [ ] Step 8: Frontend - Update Types
- [ ] Step 9: Frontend - Subscription Review Modal
- [ ] Step 10: Frontend - Update Insights Page
- [ ] Step 11: Frontend - Dashboard Upcoming Renewals Widget
- [ ] Step 12: Final - Rebuild and Test

## Files to Create/Modify

**CREATE:**
- `backend/app/ai/prompts/subscription_review.py`
- `backend/app/ai/prompts/annual_charge_detection.py`
- `frontend/src/components/alerts/SubscriptionReviewModal.tsx`

**MODIFY:**
- `backend/app/ai/prompts/__init__.py` - Add new prompt exports
- `backend/app/schemas/alert.py` - Add subscription review schemas
- `backend/app/services/alerts_service.py` - Add subscription functions
- `backend/app/api/alerts.py` - Add subscription review endpoints
- `frontend/src/lib/api.ts` - Add subscription API functions
- `frontend/src/types/index.ts` - Add subscription types
- `frontend/src/pages/Insights.tsx` - Add subscription review trigger
- `frontend/src/pages/Dashboard.tsx` - Add upcoming renewals widget

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture, subscription review prompts, data models
2. `HANDOFF.md` - Current project state and gotchas

## Known Gotchas (from Phase 1-5b)

1. **Self-hosted networking:** 
   - CORS must be `allow_origins=["*"]`
   - Frontend API URL must be dynamic: `${window.location.protocol}//${window.location.hostname}:8000/api/v1`

2. **Alert model enum:** Use `Severity` not `AlertSeverity`

3. **OpenRouter API key:** Use `OPENROUTER_API_KEY` env var

4. **Always restart after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Context

Phase 5b (Alerts System) is complete. The app has:
- Alert creation on import (large purchases, unusual merchants, price increases)
- Alert bell with unread count
- Insights page with alert management
- Alert settings (multiplier, threshold)

## Your Task: Phase 6 - Subscription Intelligence

Build smart subscription tracking:
- Detect annual charges and warn before renewal
- Periodic subscription review with AI recommendations
- Track subscription health (total cost, unused services)

---

## Deliverables

### Step 1: Backend - Update Alert Schemas

Update `backend/app/schemas/alert.py` to add subscription-related schemas:

```python
# Add these new schemas to the existing file

class SubscriptionInsight(BaseModel):
    """Individual insight about a subscription."""
    type: str  # "unused", "price_increase", "high_cost", "annual_upcoming", "duplicate"
    recurring_group_id: str
    merchant: str
    amount: float
    frequency: str
    insight: str
    recommendation: str


class SubscriptionReviewResponse(BaseModel):
    """Response from subscription review."""
    total_monthly_cost: float
    total_yearly_cost: float
    subscription_count: int
    insights: List[SubscriptionInsight]
    summary: str
    alert_id: Optional[str] = None  # The created review alert


class UpcomingRenewal(BaseModel):
    """An upcoming subscription renewal."""
    recurring_group_id: str
    merchant: str
    amount: float
    frequency: str
    next_date: str
    days_until: int


class UpcomingRenewalsResponse(BaseModel):
    """Response for upcoming renewals."""
    renewals: List[UpcomingRenewal]
    total_upcoming_30_days: float
```

Also update `AlertSettingsBase` and `AlertSettingsUpdate` to include:
```python
class AlertSettingsBase(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: float = 3.0
    unusual_merchant_threshold: float = 200.0
    subscription_review_days: int = 90  # NEW
    annual_charge_warning_days: int = 14  # NEW
    alerts_enabled: bool = True


class AlertSettingsUpdate(BaseModel):
    large_purchase_threshold: Optional[float] = None
    large_purchase_multiplier: Optional[float] = None
    unusual_merchant_threshold: Optional[float] = None
    subscription_review_days: Optional[int] = None  # NEW
    annual_charge_warning_days: Optional[int] = None  # NEW
    alerts_enabled: Optional[bool] = None
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 2: Backend - Subscription Review AI Prompt

Create `backend/app/ai/prompts/subscription_review.py`:

```python
"""AI prompt for subscription health review."""

SUBSCRIPTION_REVIEW_SYSTEM = """You analyze a user's recurring subscriptions and provide a health review.

You will receive:
1. List of active recurring charges (subscriptions)
2. Transaction activity for each subscription (how often they use related services)
3. Date of last review

Analyze and provide insights:
- Subscriptions that seem unused (no related activity in 60+ days)
- Price increases since last review
- High-cost subscriptions that might have cheaper alternatives
- Annual subscriptions coming up for renewal
- Potential duplicate services (multiple streaming, multiple cloud storage, etc.)

Respond with JSON only:
{
  "insights": [
    {
      "type": "unused" | "price_increase" | "high_cost" | "annual_upcoming" | "duplicate",
      "recurring_group_id": "<uuid>",
      "merchant": "<name>",
      "amount": <number>,
      "frequency": "<frequency>",
      "insight": "<explanation of the issue>",
      "recommendation": "<action suggestion>"
    }
  ],
  "summary": "<2-3 sentence overall summary of subscription health>"
}

Guidelines:
- Be helpful, not alarmist - some subscriptions are worth keeping even if unused occasionally
- For duplicates, explain what they might be duplicating
- For high_cost, only flag if significantly above average for the category
- Order insights by importance (unused and annual_upcoming first)"""

SUBSCRIPTION_REVIEW_USER = """Review these subscriptions:

Active Recurring Charges:
{recurring_json}

Transaction Activity by Merchant (last 90 days):
{activity_json}

Last Review Date: {last_review_date}

Provide subscription health insights."""
```

---

### Step 3: Backend - Annual Charge Detection Prompt

Create `backend/app/ai/prompts/annual_charge_detection.py`:

```python
"""AI prompt for detecting annual/yearly subscriptions."""

ANNUAL_CHARGE_DETECTION_SYSTEM = """You identify likely annual/yearly subscriptions from transaction history.

Look for:
- Charges that occur once per year to the same merchant
- Large charges to subscription-like merchants (software, services, memberships)
- Patterns suggesting annual billing (similar amount, roughly 365 day gap)

Common annual subscriptions:
- Amazon Prime, Costco membership
- Software: Adobe, Microsoft 365, antivirus
- Cloud storage: iCloud, Google One, Dropbox
- Professional: LinkedIn Premium, domain renewals
- Entertainment: Annual streaming plans

Respond with JSON only:
{
  "annual_subscriptions": [
    {
      "merchant": "<name>",
      "transaction_ids": ["<uuid>", ...],
      "amount": <number>,
      "last_charge_date": "<YYYY-MM-DD>",
      "predicted_next_date": "<YYYY-MM-DD>",
      "confidence": <0.0 to 1.0>
    }
  ]
}

Only include if:
- At least 1 charge exists (can predict from merchant name)
- Confidence > 0.6
- Amount > $20 (skip small annual fees)"""

ANNUAL_CHARGE_DETECTION_USER = """Analyze these transactions for annual subscriptions:

{transactions_json}

Look back period: 18 months
Current date: {current_date}

Identify likely annual charges and predict next renewal dates."""
```

Update `backend/app/ai/prompts/__init__.py`:

```python
from app.ai.prompts.format_detection import FORMAT_DETECTION_SYSTEM, FORMAT_DETECTION_USER
from app.ai.prompts.categorization import CATEGORIZATION_SYSTEM, CATEGORIZATION_USER
from app.ai.prompts.merchant_cleaning import MERCHANT_CLEANING_SYSTEM, MERCHANT_CLEANING_USER
from app.ai.prompts.recurring_detection import RECURRING_DETECTION_SYSTEM, RECURRING_DETECTION_USER
from app.ai.prompts.anomaly_detection import ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER
from app.ai.prompts.subscription_review import SUBSCRIPTION_REVIEW_SYSTEM, SUBSCRIPTION_REVIEW_USER
from app.ai.prompts.annual_charge_detection import ANNUAL_CHARGE_DETECTION_SYSTEM, ANNUAL_CHARGE_DETECTION_USER

__all__ = [
    'FORMAT_DETECTION_SYSTEM', 'FORMAT_DETECTION_USER',
    'CATEGORIZATION_SYSTEM', 'CATEGORIZATION_USER',
    'MERCHANT_CLEANING_SYSTEM', 'MERCHANT_CLEANING_USER',
    'RECURRING_DETECTION_SYSTEM', 'RECURRING_DETECTION_USER',
    'ANOMALY_DETECTION_SYSTEM', 'ANOMALY_DETECTION_USER',
    'SUBSCRIPTION_REVIEW_SYSTEM', 'SUBSCRIPTION_REVIEW_USER',
    'ANNUAL_CHARGE_DETECTION_SYSTEM', 'ANNUAL_CHARGE_DETECTION_USER',
]
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
```

---

### Step 4: Backend - Update Alerts Service

Add these functions to `backend/app/services/alerts_service.py`:

```python
# Add imports at top
from app.ai.prompts import (
    SUBSCRIPTION_REVIEW_SYSTEM, SUBSCRIPTION_REVIEW_USER,
    ANNUAL_CHARGE_DETECTION_SYSTEM, ANNUAL_CHARGE_DETECTION_USER
)
from app.models.recurring import RecurringGroup, Frequency
import json


async def run_subscription_review(db: Session) -> Dict[str, Any]:
    """
    Run an AI-powered subscription review.
    Creates a subscription_review alert and returns insights.
    """
    settings = get_or_create_settings(db)
    
    # Get active recurring charges
    recurring = db.query(RecurringGroup).filter(
        RecurringGroup.is_active == True
    ).all()
    
    if not recurring:
        return {
            "total_monthly_cost": 0,
            "total_yearly_cost": 0,
            "subscription_count": 0,
            "insights": [],
            "summary": "No active subscriptions found."
        }
    
    # Calculate costs
    total_monthly = 0
    for r in recurring:
        if r.expected_amount:
            amount = float(r.expected_amount)
            if r.frequency == Frequency.weekly:
                total_monthly += amount * 4.33
            elif r.frequency == Frequency.biweekly:
                total_monthly += amount * 2.17
            elif r.frequency == Frequency.monthly:
                total_monthly += amount
            elif r.frequency == Frequency.quarterly:
                total_monthly += amount / 3
            elif r.frequency == Frequency.yearly:
                total_monthly += amount / 12
    
    total_yearly = total_monthly * 12
    
    # Prepare data for AI
    recurring_json = json.dumps([
        {
            "id": str(r.id),
            "name": r.name,
            "merchant_pattern": r.merchant_pattern,
            "amount": float(r.expected_amount) if r.expected_amount else 0,
            "frequency": r.frequency.value,
            "last_seen": r.last_seen_date.isoformat() if r.last_seen_date else None,
            "next_expected": r.next_expected_date.isoformat() if r.next_expected_date else None,
        }
        for r in recurring
    ], indent=2)
    
    # Get transaction activity (simplified - count per merchant)
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=90)
    
    activity = {}
    for r in recurring:
        count = db.query(Transaction).filter(
            Transaction.recurring_group_id == r.id,
            Transaction.date >= cutoff.date()
        ).count()
        activity[r.name] = count
    
    activity_json = json.dumps(activity, indent=2)
    
    # Get last review date
    last_review = db.query(Alert).filter(
        Alert.type == AlertType.subscription_review
    ).order_by(Alert.created_at.desc()).first()
    
    last_review_date = last_review.created_at.isoformat() if last_review else "Never"
    
    # Call AI for review
    client = get_ai_client()
    user_prompt = SUBSCRIPTION_REVIEW_USER.format(
        recurring_json=recurring_json,
        activity_json=activity_json,
        last_review_date=last_review_date
    )
    
    try:
        result = await client.complete_json(
            system_prompt=SUBSCRIPTION_REVIEW_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        insights = result.get("insights", [])
        summary = result.get("summary", "Review complete.")
        
    except Exception as e:
        print(f"Subscription review AI failed: {e}")
        insights = []
        summary = "Unable to generate AI insights. Review your subscriptions manually."
    
    # Create review alert
    alert = Alert(
        id=str(uuid.uuid4()),
        type=AlertType.subscription_review,
        severity=Severity.info,
        title=f"Subscription Review: {len(recurring)} active subscriptions",
        description=f"Monthly: ${total_monthly:.2f} | Yearly: ${total_yearly:.2f}. {summary}",
        metadata={
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "subscription_count": len(recurring),
            "insights": insights
        }
    )
    db.add(alert)
    
    # Update last review timestamp in settings
    settings.last_subscription_review = datetime.now()
    settings.updated_at = datetime.now()
    
    db.commit()
    
    return {
        "total_monthly_cost": total_monthly,
        "total_yearly_cost": total_yearly,
        "subscription_count": len(recurring),
        "insights": insights,
        "summary": summary,
        "alert_id": str(alert.id)
    }


def get_upcoming_renewals(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get recurring charges expected in the next N days."""
    from datetime import timedelta
    
    cutoff = date.today() + timedelta(days=days)
    
    recurring = db.query(RecurringGroup).filter(
        RecurringGroup.is_active == True,
        RecurringGroup.next_expected_date != None,
        RecurringGroup.next_expected_date <= cutoff
    ).order_by(RecurringGroup.next_expected_date).all()
    
    renewals = []
    total = 0
    
    for r in recurring:
        amount = float(r.expected_amount) if r.expected_amount else 0
        days_until = (r.next_expected_date - date.today()).days
        
        renewals.append({
            "recurring_group_id": str(r.id),
            "merchant": r.name,
            "amount": amount,
            "frequency": r.frequency.value,
            "next_date": r.next_expected_date.isoformat(),
            "days_until": days_until
        })
        total += amount
    
    return {
        "renewals": renewals,
        "total_upcoming_30_days": total
    }


async def detect_annual_charges(db: Session) -> List[Dict[str, Any]]:
    """
    Use AI to detect annual subscription patterns.
    Creates annual_charge alerts for upcoming renewals.
    """
    settings = get_or_create_settings(db)
    warning_days = settings.annual_charge_warning_days or 14
    
    # Get transactions from last 18 months
    cutoff = date.today() - timedelta(days=548)
    
    transactions = db.query(Transaction).filter(
        Transaction.date >= cutoff,
        Transaction.amount < 0,
        func.abs(Transaction.amount) > 20  # Skip small charges
    ).order_by(Transaction.date.desc()).all()
    
    if len(transactions) < 10:
        return []
    
    txn_json = json.dumps([
        {
            "id": str(t.id),
            "date": t.date.isoformat(),
            "amount": float(t.amount),
            "merchant": t.clean_merchant or t.raw_description,
        }
        for t in transactions
    ], indent=2)
    
    client = get_ai_client()
    user_prompt = ANNUAL_CHARGE_DETECTION_USER.format(
        transactions_json=txn_json,
        current_date=date.today().isoformat()
    )
    
    try:
        result = await client.complete_json(
            system_prompt=ANNUAL_CHARGE_DETECTION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1500
        )
        
        annual_subs = result.get("annual_subscriptions", [])
        
    except Exception as e:
        print(f"Annual charge detection failed: {e}")
        return []
    
    # Create alerts for upcoming annual charges
    created_alerts = []
    for sub in annual_subs:
        if sub.get("confidence", 0) < 0.6:
            continue
            
        predicted_date = sub.get("predicted_next_date")
        if not predicted_date:
            continue
            
        try:
            next_date = datetime.strptime(predicted_date, "%Y-%m-%d").date()
        except:
            continue
        
        days_until = (next_date - date.today()).days
        
        # Only alert if within warning window
        if 0 < days_until <= warning_days:
            alert = Alert(
                id=str(uuid.uuid4()),
                type=AlertType.annual_charge,
                severity=Severity.info,
                title=f"Annual renewal: {sub['merchant']}",
                description=f"${sub['amount']:.2f} expected in {days_until} days (around {predicted_date})",
                metadata={
                    "merchant": sub["merchant"],
                    "amount": sub["amount"],
                    "predicted_date": predicted_date,
                    "days_until": days_until,
                    "confidence": sub.get("confidence", 0)
                }
            )
            db.add(alert)
            created_alerts.append(sub)
    
    if created_alerts:
        db.commit()
    
    return created_alerts
```

Add needed imports at top of file:
```python
from datetime import datetime, date, timedelta
from sqlalchemy import func
from app.ai.client import get_ai_client
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 20
```

---

### Step 5: Backend - Subscription Review API Endpoints

Add these endpoints to `backend/app/api/alerts.py`:

```python
# Add these imports at top
from app.schemas.alert import (
    AlertResponse,
    AlertsListResponse,
    AlertUpdate,
    UnreadCountResponse,
    AlertSettingsResponse,
    AlertSettingsUpdate,
    SubscriptionReviewResponse,
    UpcomingRenewalsResponse,
)

# Add these new endpoints

@router.post("/subscription-review", response_model=SubscriptionReviewResponse)
async def trigger_subscription_review(db: Session = Depends(get_db)):
    """
    Manually trigger a subscription review.
    Uses AI to analyze subscriptions and create insights.
    """
    result = await alerts_service.run_subscription_review(db)
    return SubscriptionReviewResponse(**result)


@router.get("/upcoming-renewals", response_model=UpcomingRenewalsResponse)
def get_upcoming_renewals(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get upcoming subscription renewals."""
    result = alerts_service.get_upcoming_renewals(db, days)
    return UpcomingRenewalsResponse(**result)


@router.post("/detect-annual")
async def detect_annual_charges(db: Session = Depends(get_db)):
    """
    Detect annual subscription patterns and create alerts for upcoming renewals.
    """
    detected = await alerts_service.detect_annual_charges(db)
    return {
        "detected": len(detected),
        "charges": detected
    }
```

**Verify:**
```bash
docker compose restart api
docker compose logs api --tail 10
curl http://localhost:8000/api/v1/alerts/upcoming-renewals
```

---

### Step 6: Backend - Update Alert Settings Model (if needed)

Check if `alert_settings` table has the new columns. If not, add them:

```bash
# Check current columns
docker compose exec api python -c "
from app.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('alert_settings')]
print('Columns:', columns)
"
```

If `subscription_review_days`, `annual_charge_warning_days`, or `last_subscription_review` are missing, create a migration:

```bash
docker compose exec api alembic revision --autogenerate -m "add subscription review settings"
docker compose exec api alembic upgrade head
```

Or add columns directly if needed:
```bash
docker compose exec api python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE alert_settings ADD COLUMN subscription_review_days INTEGER DEFAULT 90'))
    except: pass
    try:
        conn.execute(text('ALTER TABLE alert_settings ADD COLUMN annual_charge_warning_days INTEGER DEFAULT 14'))
    except: pass
    try:
        conn.execute(text('ALTER TABLE alert_settings ADD COLUMN last_subscription_review TIMESTAMP'))
    except: pass
    conn.commit()
print('Columns added')
"
```

---

### Step 7: Frontend - Update API Client

Add to `frontend/src/lib/api.ts`:

```typescript
// Subscription Intelligence

export interface SubscriptionInsight {
  type: 'unused' | 'price_increase' | 'high_cost' | 'annual_upcoming' | 'duplicate'
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  insight: string
  recommendation: string
}

export interface SubscriptionReviewResponse {
  total_monthly_cost: number
  total_yearly_cost: number
  subscription_count: number
  insights: SubscriptionInsight[]
  summary: string
  alert_id?: string
}

export interface UpcomingRenewal {
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  next_date: string
  days_until: number
}

export interface UpcomingRenewalsResponse {
  renewals: UpcomingRenewal[]
  total_upcoming_30_days: number
}

export async function triggerSubscriptionReview() {
  const response = await api.post('/alerts/subscription-review')
  return response.data as SubscriptionReviewResponse
}

export async function getUpcomingRenewals(days: number = 30) {
  const response = await api.get('/alerts/upcoming-renewals', { params: { days } })
  return response.data as UpcomingRenewalsResponse
}

export async function detectAnnualCharges() {
  const response = await api.post('/alerts/detect-annual')
  return response.data
}
```

---

### Step 8: Frontend - Update Types

Add to `frontend/src/types/index.ts`:

```typescript
// Subscription Intelligence types

export interface SubscriptionInsight {
  type: 'unused' | 'price_increase' | 'high_cost' | 'annual_upcoming' | 'duplicate'
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  insight: string
  recommendation: string
}

export interface SubscriptionReviewResponse {
  total_monthly_cost: number
  total_yearly_cost: number
  subscription_count: number
  insights: SubscriptionInsight[]
  summary: string
  alert_id?: string
}

export interface UpcomingRenewal {
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  next_date: string
  days_until: number
}

export interface UpcomingRenewalsResponse {
  renewals: UpcomingRenewal[]
  total_upcoming_30_days: number
}
```

---

### Step 9: Frontend - Subscription Review Modal

Create `frontend/src/components/alerts/SubscriptionReviewModal.tsx`:

```tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { triggerSubscriptionReview, SubscriptionReviewResponse, SubscriptionInsight } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency } from '@/lib/formatters'

interface Props {
  isOpen: boolean
  onClose: () => void
}

const INSIGHT_ICONS: Record<string, string> = {
  unused: '💤',
  price_increase: '📈',
  high_cost: '💸',
  annual_upcoming: '📅',
  duplicate: '👯',
}

const INSIGHT_COLORS: Record<string, string> = {
  unused: 'bg-yellow-50 border-yellow-200',
  price_increase: 'bg-red-50 border-red-200',
  high_cost: 'bg-orange-50 border-orange-200',
  annual_upcoming: 'bg-blue-50 border-blue-200',
  duplicate: 'bg-purple-50 border-purple-200',
}

export default function SubscriptionReviewModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient()
  const [reviewData, setReviewData] = useState<SubscriptionReviewResponse | null>(null)

  const reviewMutation = useMutation({
    mutationFn: triggerSubscriptionReview,
    onSuccess: (data) => {
      setReviewData(data)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-bold">Subscription Review</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {!reviewData && !reviewMutation.isPending && (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">
                Run an AI-powered review of your subscriptions to find savings opportunities.
              </p>
              <Button onClick={() => reviewMutation.mutate()}>
                🔍 Start Review
              </Button>
            </div>
          )}

          {reviewMutation.isPending && (
            <div className="text-center py-8">
              <p className="text-gray-600">Analyzing your subscriptions...</p>
            </div>
          )}

          {reviewMutation.error && (
            <div className="text-center py-8 text-red-600">
              Error running review. Please try again.
            </div>
          )}

          {reviewData && (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold">{reviewData.subscription_count}</div>
                  <div className="text-sm text-gray-500">Subscriptions</div>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold text-red-600">
                    {formatCurrency(reviewData.total_monthly_cost)}
                  </div>
                  <div className="text-sm text-gray-500">Monthly</div>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold text-red-600">
                    {formatCurrency(reviewData.total_yearly_cost)}
                  </div>
                  <div className="text-sm text-gray-500">Yearly</div>
                </div>
              </div>

              {/* AI Summary */}
              <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <p className="text-sm">{reviewData.summary}</p>
              </div>

              {/* Insights */}
              {reviewData.insights.length > 0 ? (
                <div className="space-y-3">
                  <h3 className="font-semibold">Recommendations</h3>
                  {reviewData.insights.map((insight, i) => (
                    <div
                      key={i}
                      className={`border rounded p-3 ${INSIGHT_COLORS[insight.type] || 'bg-gray-50'}`}
                    >
                      <div className="flex gap-2 items-start">
                        <span className="text-xl">{INSIGHT_ICONS[insight.type] || '💡'}</span>
                        <div className="flex-1">
                          <div className="font-medium">
                            {insight.merchant} - {formatCurrency(insight.amount)}/{insight.frequency}
                          </div>
                          <div className="text-sm text-gray-700 mt-1">{insight.insight}</div>
                          <div className="text-sm font-medium text-gray-900 mt-2">
                            💡 {insight.recommendation}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-500">
                  🎉 No issues found! Your subscriptions look healthy.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex justify-end gap-2">
          {reviewData && (
            <Button variant="outline" onClick={() => setReviewData(null)}>
              Run Again
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

### Step 10: Frontend - Update Insights Page

Update `frontend/src/pages/Insights.tsx` to add subscription review trigger:

Add import:
```tsx
import SubscriptionReviewModal from '@/components/alerts/SubscriptionReviewModal'
```

Add state:
```tsx
const [showReviewModal, setShowReviewModal] = useState(false)
```

Add button in the header area (near Settings button):
```tsx
<Button onClick={() => setShowReviewModal(true)}>
  📋 Subscription Review
</Button>
```

Add modal at the end of the component (before final closing tag):
```tsx
<SubscriptionReviewModal
  isOpen={showReviewModal}
  onClose={() => setShowReviewModal(false)}
/>
```

---

### Step 11: Frontend - Dashboard Upcoming Renewals Widget

Update `frontend/src/pages/Dashboard.tsx` to add an upcoming renewals section.

Add import:
```tsx
import { getUpcomingRenewals } from '@/lib/api'
```

Add query:
```tsx
const { data: upcomingRenewals } = useQuery({
  queryKey: ['upcoming-renewals'],
  queryFn: () => getUpcomingRenewals(30),
})
```

Add widget (in the grid with other dashboard cards):
```tsx
{/* Upcoming Renewals */}
<div className="bg-white border rounded-lg p-4">
  <h2 className="text-lg font-semibold mb-4">Upcoming Renewals</h2>
  <div className="space-y-3">
    {upcomingRenewals?.renewals?.slice(0, 5).map((renewal) => (
      <div key={renewal.recurring_group_id} className="flex justify-between items-center">
        <div>
          <div className="text-sm font-medium">{renewal.merchant}</div>
          <div className="text-xs text-gray-500">
            {renewal.days_until === 0 ? 'Today' : 
             renewal.days_until === 1 ? 'Tomorrow' :
             `In ${renewal.days_until} days`}
          </div>
        </div>
        <div className="text-sm font-medium text-red-600">
          {formatCurrency(renewal.amount)}
        </div>
      </div>
    ))}
    {(!upcomingRenewals?.renewals || upcomingRenewals.renewals.length === 0) && (
      <p className="text-sm text-gray-500">No upcoming renewals in the next 30 days</p>
    )}
  </div>
  {upcomingRenewals?.total_upcoming_30_days > 0 && (
    <div className="mt-3 pt-3 border-t text-sm">
      <span className="text-gray-500">Total next 30 days:</span>
      <span className="font-medium text-red-600 ml-2">
        {formatCurrency(upcomingRenewals.total_upcoming_30_days)}
      </span>
    </div>
  )}
</div>
```

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

# Test new endpoints
curl http://localhost:8000/api/v1/alerts/upcoming-renewals
curl -X POST http://localhost:8000/api/v1/alerts/subscription-review
curl -X POST http://localhost:8000/api/v1/alerts/detect-annual
```

**Test in UI:**
1. Go to Dashboard - should see "Upcoming Renewals" widget
2. Go to Insights - should see "Subscription Review" button
3. Click "Subscription Review" - modal should open
4. Click "Start Review" - should show AI analysis
5. Check alert settings have new fields (subscription_review_days, annual_charge_warning_days)

---

## Verification Checklist

- [ ] `GET /api/v1/alerts/upcoming-renewals` returns upcoming charges
- [ ] `POST /api/v1/alerts/subscription-review` runs AI review
- [ ] `POST /api/v1/alerts/detect-annual` detects annual patterns
- [ ] Dashboard shows "Upcoming Renewals" widget
- [ ] Insights page has "Subscription Review" button
- [ ] Subscription Review modal opens and runs
- [ ] AI provides insights and recommendations
- [ ] Review creates a subscription_review alert
- [ ] No console errors
- [ ] No API errors

---

## Notes

- Subscription review uses AI (costs API credits) - that's why it's manual trigger
- Annual charge detection also uses AI - could be scheduled weekly
- The `subscription_review_days` setting is for future scheduled reviews (not implemented in this phase)
- Price increase detection was already in Phase 5b - this builds on it
