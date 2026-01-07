# Spendah - Technical Specification

> Local-first personal finance tracker with AI-powered categorization

**Note:** The project name "Spendah" is a working title and may change before public release. To facilitate this, avoid hardcoding the name throughout the codebase. Use a central config constant (e.g., `APP_NAME`) for display strings, and keep the internal package/module names generic (e.g., `app`, `backend`, `frontend`) rather than branded.

## Overview

Spendah is a self-hosted personal finance application that prioritizes privacy and local data ownership. Unlike services like Rocket Money or Monarch Money, it does not connect to bank accounts via APIs. Instead, users manually import CSV/OFX/QFX files exported from their financial institutions.

The core innovation is AI-powered format detection and transaction categorization, with support for multiple LLM backends including local models via Ollama/LM Studio.

### Goals

1. **Privacy-first**: All data stays local. No external bank connections.
2. **AI-smart**: LLMs handle the tedious work (format detection, categorization, recurring detection).
3. **Model-agnostic**: Swap between local and cloud LLMs via configuration.
4. **Low friction**: Weekly file drops, minimal manual intervention.
5. **Single-user MVP**: No auth complexity for v1.

### Non-Goals (for MVP)

- Multi-user / household support
- Mobile app
- Real-time bank connections
- Investment tracking
- Multi-currency support

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Compose                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────┐   │
│  │   React     │◄──►│   FastAPI   │◄──►│    SQLite     │   │
│  │   Frontend  │    │   Backend   │    │               │   │
│  │   :5173     │    │   :8000     │    │  ./data/      │   │
│  └─────────────┘    └──────┬──────┘    └───────────────┘   │
│                            │                                │
│                            ▼                                │
│                     ┌─────────────┐                         │
│                     │   LiteLLM   │                         │
│                     └──────┬──────┘                         │
│                            │                                │
│              ┌─────────────┼─────────────┐                  │
│              ▼             ▼             ▼                  │
│         [Ollama]     [Claude API]   [OpenAI API]           │
│         (local)       (remote)       (remote)              │
│                                                             │
│  Volumes:                                                   │
│   - ./data/db.sqlite                                        │
│   - ./data/imports/{inbox,processed,failed}/                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLite (via SQLAlchemy)
- Alembic (migrations)
- LiteLLM (model abstraction)
- Pydantic v2 (validation, structured outputs)

### Frontend
- React 18
- TypeScript (strict mode)
- Vite
- Tailwind CSS
- shadcn/ui (component library)
- TanStack Table (transaction list)
- TanStack Query (server state)
- Recharts (visualizations)

### Infrastructure
- Docker Compose
- Single container build (multi-stage) or split api/ui containers
- Volume mounts for persistence

---

## Project Structure

```
spendah/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── dependencies.py         # FastAPI dependencies
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── recurring.py
│   │   │   ├── learned_format.py
│   │   │   ├── alert.py
│   │   │   └── alert_settings.py
│   │   │
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── import_file.py
│   │   │   ├── dashboard.py
│   │   │   └── alert.py
│   │   │
│   │   ├── api/                    # API routes
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Main router
│   │   │   ├── transactions.py
│   │   │   ├── accounts.py
│   │   │   ├── categories.py
│   │   │   ├── imports.py
│   │   │   ├── recurring.py
│   │   │   ├── dashboard.py
│   │   │   └── alerts.py           # Alerts & insights
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── transaction_service.py
│   │   │   ├── import_service.py
│   │   │   ├── categorization_service.py
│   │   │   ├── recurring_service.py
│   │   │   ├── deduplication_service.py
│   │   │   └── alerts_service.py     # Anomaly detection, subscription review
│   │   │
│   │   ├── parsers/                # File parsing
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base parser class
│   │   │   ├── csv_parser.py       # Generic CSV with AI detection
│   │   │   └── ofx_parser.py       # OFX/QFX parser
│   │   │
│   │   └── ai/                     # LLM integration
│   │       ├── __init__.py
│   │       ├── client.py           # LiteLLM wrapper
│   │       ├── prompts/            # Prompt templates
│   │       │   ├── format_detection.py
│   │       │   ├── categorization.py
│   │       │   ├── merchant_cleaning.py
│   │       │   ├── recurring_detection.py
│   │       │   ├── anomaly_detection.py
│   │       │   └── subscription_review.py
│   │       └── structured_outputs.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_parsers.py
│   │   ├── test_services.py
│   │   └── test_api.py
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── alembic.ini
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── SpendingOverview.tsx
│   │   │   │   ├── CategoryBreakdown.tsx
│   │   │   │   └── RecentTransactions.tsx
│   │   │   ├── transactions/
│   │   │   │   ├── TransactionTable.tsx
│   │   │   │   ├── TransactionRow.tsx
│   │   │   │   └── CategorySelect.tsx
│   │   │   ├── imports/
│   │   │   │   ├── FileDropZone.tsx
│   │   │   │   ├── FormatConfirmation.tsx
│   │   │   │   └── ImportProgress.tsx
│   │   │   ├── recurring/
│   │   │   │   └── RecurringList.tsx
│   │   │   ├── accounts/
│   │   │   │   └── AccountList.tsx
│   │   │   └── alerts/
│   │   │       ├── AlertBell.tsx         # Notification icon with badge
│   │   │       ├── AlertCard.tsx         # Individual alert display
│   │   │       ├── AlertsList.tsx        # Feed of alerts
│   │   │       └── SubscriptionReview.tsx # Subscription health modal
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Recurring.tsx
│   │   │   ├── Accounts.tsx
│   │   │   ├── Import.tsx
│   │   │   ├── Alerts.tsx                # Insights & alerts feed
│   │   │   └── Settings.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useTransactions.ts
│   │   │   ├── useCategories.ts
│   │   │   ├── useAccounts.ts
│   │   │   ├── useDashboard.ts
│   │   │   └── useAlerts.ts
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts              # API client
│   │   │   ├── utils.ts
│   │   │   └── formatters.ts
│   │   │
│   │   └── types/
│   │       └── index.ts
│   │
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── data/                           # gitignored
│   ├── db.sqlite
│   └── imports/
│       ├── inbox/
│       ├── processed/
│       └── failed/
│
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── CLAUDE.md
├── .claude/
│   └── settings.json
└── README.md
```

---

## Data Models

### transactions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| hash | VARCHAR(64) | SHA256(date+amount+raw_description+account_id) for deduplication |
| date | DATE | Transaction date |
| amount | DECIMAL(12,2) | Negative = expense, positive = income |
| raw_description | TEXT | Original bank description |
| clean_merchant | VARCHAR(255) | AI-cleaned or user-corrected merchant name |
| category_id | UUID | FK to categories |
| account_id | UUID | FK to accounts |
| is_recurring | BOOLEAN | AI-detected or user-set |
| recurring_group_id | UUID | FK to recurring_groups (nullable) |
| notes | TEXT | User notes (nullable) |
| ai_categorized | BOOLEAN | True if category was set by AI |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Unique constraint**: `hash` (prevents duplicate imports)

### accounts

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(100) | Display name ("Chase Sapphire") |
| type | ENUM | credit, debit, bank, cash, other |
| learned_format_id | UUID | FK to learned_formats (nullable) |
| is_active | BOOLEAN | Show in UI |
| created_at | TIMESTAMP | |

### categories

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(100) | Category name |
| parent_id | UUID | FK to self for subcategories (nullable) |
| color | VARCHAR(7) | Hex color for UI |
| icon | VARCHAR(50) | Icon identifier |
| is_system | BOOLEAN | Default categories vs user-created |
| created_at | TIMESTAMP | |

**Default categories** (seeded on init):
- Income
- Housing (Rent/Mortgage, Utilities, Insurance)
- Transportation (Gas, Auto Insurance, Maintenance, Parking)
- Food (Groceries, Restaurants, Coffee)
- Shopping (Clothing, Electronics, Home)
- Entertainment (Streaming, Games, Events)
- Health (Medical, Pharmacy, Fitness)
- Personal (Haircut, Education)
- Travel
- Subscriptions
- Transfers
- Fees
- Other

### recurring_groups

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(100) | Display name ("Netflix", "Rent") |
| merchant_pattern | VARCHAR(255) | Regex or fuzzy match pattern |
| expected_amount | DECIMAL(12,2) | Typical amount (nullable) |
| amount_variance | DECIMAL(5,2) | Acceptable % variance |
| frequency | ENUM | weekly, biweekly, monthly, quarterly, yearly |
| category_id | UUID | FK to categories |
| last_seen_date | DATE | |
| next_expected_date | DATE | AI-calculated |
| is_active | BOOLEAN | |
| created_at | TIMESTAMP | |

### learned_formats

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(100) | User-friendly name ("Chase Checking CSV") |
| fingerprint | VARCHAR(64) | Hash of headers/structure for matching |
| file_type | ENUM | csv, ofx, qfx |
| column_mapping | JSON | {"date": 0, "amount": 3, "description": 1, ...} |
| date_format | VARCHAR(50) | strptime format string |
| amount_style | ENUM | signed, separate_columns, parentheses_negative |
| debit_column | INTEGER | If amount_style is separate_columns |
| credit_column | INTEGER | If amount_style is separate_columns |
| skip_rows | INTEGER | Header rows to skip |
| account_id | UUID | FK to accounts (nullable) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### alerts

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| type | ENUM | large_purchase, price_increase, new_recurring, subscription_review, unusual_merchant, annual_charge |
| severity | ENUM | info, warning, attention |
| title | VARCHAR(200) | Short headline |
| description | TEXT | Detailed explanation |
| transaction_id | UUID | FK to transactions (nullable) |
| recurring_group_id | UUID | FK to recurring_groups (nullable) |
| metadata | JSON | Flexible data (thresholds, comparisons, etc.) |
| is_read | BOOLEAN | User has seen it |
| is_dismissed | BOOLEAN | User explicitly dismissed |
| action_taken | VARCHAR(100) | What user did (nullable): "kept", "cancelled", "reviewed" |
| created_at | TIMESTAMP | |

**Alert types explained:**

| Type | Trigger | Example |
|------|---------|---------|
| `large_purchase` | Transaction > 3x category average | "$847 at Best Buy - 5x your usual Electronics spend" |
| `price_increase` | Recurring charge increased | "Netflix went up $3/mo (was $15.99, now $18.99)" |
| `new_recurring` | AI detected new subscription | "Looks like you subscribed to Cursor ($20/mo)" |
| `subscription_review` | Scheduled periodic review | "Time for your 90-day subscription check-in" |
| `unusual_merchant` | First-time merchant over threshold | "First purchase at B&H Photo: $1,243" |
| `annual_charge` | Yearly subscription hit | "Annual charge: iCloud+ $119.88 (renews yearly)" |

### alert_settings

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| large_purchase_threshold | DECIMAL | Dollar amount, or null for auto-detect |
| large_purchase_multiplier | DECIMAL | X times category average (default 3.0) |
| unusual_merchant_threshold | DECIMAL | First-time merchant alert threshold (default $200) |
| subscription_review_days | INTEGER | Days between reviews (default 90) |
| last_subscription_review | TIMESTAMP | When last review was triggered |
| annual_charge_warning_days | INTEGER | Days before annual charge to warn (default 14) |
| alerts_enabled | BOOLEAN | Master toggle |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### import_logs

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| filename | VARCHAR(255) | Original filename |
| account_id | UUID | FK to accounts |
| status | ENUM | pending, processing, completed, failed |
| transactions_imported | INTEGER | |
| transactions_skipped | INTEGER | Duplicates |
| error_message | TEXT | If failed |
| created_at | TIMESTAMP | |

### user_corrections

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| raw_description | TEXT | Original bank description |
| clean_merchant | VARCHAR(255) | User-corrected merchant |
| category_id | UUID | User-corrected category |
| created_at | TIMESTAMP | |

Used to improve future AI categorization. When user corrects a transaction, store the mapping here and feed it as few-shot examples.

---

## API Endpoints

Base URL: `/api/v1`

### Dashboard

```
GET /dashboard/summary
  Query: month (YYYY-MM), defaults to current
  Returns: {
    total_income: number,
    total_expenses: number,
    net: number,
    by_category: [{category, amount, percent}],
    vs_last_month: {income_change_pct, expense_change_pct}
  }

GET /dashboard/trends
  Query: months (int, default 6)
  Returns: [{month, income, expenses, net}]
```

### Transactions

```
GET /transactions
  Query: 
    - page, per_page (pagination)
    - account_id (filter)
    - category_id (filter)
    - start_date, end_date (filter)
    - search (fuzzy search on description/merchant)
    - is_recurring (boolean filter)
  Returns: {items: [...], total, page, pages}

GET /transactions/{id}

PATCH /transactions/{id}
  Body: {category_id?, clean_merchant?, is_recurring?, notes?}
  Note: Updates to category/merchant create user_corrections entry

POST /transactions/bulk-categorize
  Body: {transaction_ids: [...], category_id}
```

### Accounts

```
GET /accounts
POST /accounts
  Body: {name, type}
PATCH /accounts/{id}
DELETE /accounts/{id}
  Note: Soft delete (is_active = false), preserves transactions
```

### Categories

```
GET /categories
  Returns: Tree structure with parent/children
POST /categories
  Body: {name, parent_id?, color?, icon?}
PATCH /categories/{id}
DELETE /categories/{id}
  Note: Reassigns transactions to "Other" first
```

### Recurring

```
GET /recurring
  Returns: [{group, last_transaction, next_expected, trend}]

POST /recurring/detect
  Triggers AI detection job, returns job status

PATCH /recurring/{id}
  Body: {name?, frequency?, expected_amount?, is_active?}

POST /transactions/{id}/mark-recurring
  Body: {recurring_group_id} or {create_new: true, name, frequency}
```

### Imports

```
POST /imports/upload
  Multipart file upload
  Returns: {
    import_id,
    detected_format: {name, column_mapping, confidence},
    preview_rows: [...],
    needs_confirmation: boolean
  }

POST /imports/{id}/confirm
  Body: {
    account_id,
    format_adjustments?: {column_mapping?, date_format?},
    save_format: boolean,
    format_name?: string
  }
  Triggers actual import

GET /imports/{id}/status
  Returns: {status, transactions_imported, transactions_skipped, errors}

GET /imports/history
```

### Settings

```
GET /settings
  Returns: {ai_provider, ai_model, alert_settings, ...}

PATCH /settings
  Body: {ai_provider?, ai_model?, ...}

GET /settings/formats
  Returns: List of learned_formats

DELETE /settings/formats/{id}

PATCH /settings/alerts
  Body: {
    large_purchase_threshold?,
    large_purchase_multiplier?,
    unusual_merchant_threshold?,
    subscription_review_days?,
    annual_charge_warning_days?,
    alerts_enabled?
  }
```

### Alerts

```
GET /alerts
  Query:
    - is_read (boolean filter)
    - is_dismissed (boolean filter)
    - type (filter by alert type)
    - severity (filter)
    - limit (default 20)
  Returns: {items: [...], unread_count}

GET /alerts/unread-count
  Returns: {count: number}

PATCH /alerts/{id}
  Body: {is_read?, is_dismissed?, action_taken?}

POST /alerts/mark-all-read

POST /alerts/subscription-review
  Manually trigger a subscription review
  Returns: {alert_id, subscriptions: [...]}

GET /alerts/insights/spending
  Query: months (default 3)
  Returns: {
    avg_by_category: [...],
    anomalies_detected: number,
    subscription_total_monthly: number,
    subscription_change_yoy: number
  }
```

---

## AI Integration

### LiteLLM Configuration

```python
# config.py
class Settings(BaseSettings):
    ai_provider: str = "ollama"  # ollama, openai, anthropic
    ai_model: str = "llama3.1:8b"
    ai_base_url: Optional[str] = "http://localhost:11434"  # For Ollama
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
```

### Prompt: Format Detection

```python
SYSTEM = """You are a financial data expert. Analyze CSV file contents and identify column mappings.

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
  "source_guess": "<bank/card name if recognizable>",
  "confidence": <0.0-1.0>
}"""

USER = """Headers: {headers}

First 5 data rows:
{sample_rows}

Identify the column mapping for this financial export."""
```

### Prompt: Merchant Cleaning

```python
SYSTEM = """Clean merchant names from bank transactions.

Input: Raw bank description
Output: Clean, human-readable merchant name

Examples:
- "AMZN MKTP US*1X2Y3Z4" → "Amazon"
- "UBER *EATS PENDING" → "Uber Eats"
- "SQ *BLUE BOTTLE COF" → "Blue Bottle Coffee"
- "GOOGLE *YOUTUBE MUSIC" → "YouTube Music"

Respond with just the clean name, no explanation."""
```

### Prompt: Categorization

```python
SYSTEM = """Categorize financial transactions.

Available categories:
{categories_json}

Recent user corrections (learn from these):
{user_corrections}

For each transaction, respond with JSON:
{"category_id": "<uuid>", "confidence": <0.0-1.0>}"""

USER = """Merchant: {clean_merchant}
Amount: ${amount}
Date: {date}
Account type: {account_type}"""
```

### Prompt: Recurring Detection

```python
SYSTEM = """Analyze transactions to identify recurring payments.

Look for:
- Regular intervals (weekly, monthly, yearly)
- Similar amounts (within 10% variance)
- Same or similar merchant names

Respond with JSON array:
[
  {
    "merchant_pattern": "<merchant name or pattern>",
    "transaction_ids": ["<uuid>", ...],
    "frequency": "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly",
    "average_amount": <number>,
    "confidence": <0.0-1.0>
  }
]"""

USER = """Analyze these transactions for recurring patterns:
{transactions_json}"""
```

### Prompt: Anomaly Detection

```python
SYSTEM = """Analyze transactions to detect anomalies and unusual spending.

You will receive:
1. A new transaction to analyze
2. Historical spending averages by category
3. Known merchants and their typical amounts

Flag the transaction if ANY of these apply:
- Amount is significantly higher than category average (use multiplier threshold)
- First-time merchant with amount over threshold
- Price increase on a known recurring charge
- Annual/yearly subscription charge

Respond with JSON:
{
  "is_anomaly": boolean,
  "anomaly_types": ["large_purchase" | "unusual_merchant" | "price_increase" | "annual_charge"],
  "severity": "info" | "warning" | "attention",
  "explanation": "<human readable explanation>",
  "comparisons": {
    "category_avg": <number or null>,
    "multiplier": <number or null>,
    "previous_amount": <number or null>,
    "price_change": <number or null>
  }
}

If not an anomaly, return:
{"is_anomaly": false}"""

USER = """Analyze this transaction:
{transaction_json}

Category averages (last 3 months):
{category_averages_json}

Known recurring charges:
{recurring_charges_json}

Thresholds:
- Large purchase multiplier: {multiplier}x category average
- Unusual merchant threshold: ${unusual_threshold}
"""
```

### Prompt: Subscription Review

```python
SYSTEM = """Generate a subscription health review.

Analyze the user's recurring charges and provide insights:
1. Total monthly cost of all subscriptions
2. Subscriptions that seem unused or forgotten (no related activity)
3. Price increases in the last period
4. Annual subscriptions coming up for renewal
5. Recommendations for review

Respond with JSON:
{
  "total_monthly_cost": <number>,
  "total_yearly_cost": <number>,
  "subscription_count": <number>,
  "insights": [
    {
      "type": "unused" | "price_increase" | "high_cost" | "annual_upcoming" | "duplicate",
      "recurring_group_id": "<uuid>",
      "merchant": "<name>",
      "amount": <number>,
      "frequency": "<frequency>",
      "insight": "<explanation>",
      "recommendation": "<action suggestion>"
    }
  ],
  "summary": "<2-3 sentence overall summary>"
}"""

USER = """Review these subscriptions:
{recurring_charges_json}

Transaction activity by merchant (last 90 days):
{merchant_activity_json}

Previous review date: {last_review_date}
"""
```

### Prompt: Annual Charge Prediction

```python
SYSTEM = """Identify likely annual/yearly subscriptions from transaction history.

Look for:
- Charges that occur once per year to the same merchant
- Large charges to subscription-like merchants (software, services, memberships)
- Patterns suggesting annual billing (similar amount, ~365 day gap)

Respond with JSON array:
[
  {
    "merchant": "<name>",
    "transaction_ids": ["<uuid>", ...],
    "amount": <number>,
    "last_charge_date": "<ISO date>",
    "predicted_next_date": "<ISO date>",
    "confidence": <0.0-1.0>
  }
]"""

USER = """Analyze these transactions for annual subscriptions:
{transactions_json}

Look back period: 18 months
"""
```

### Structured Output Handling

```python
# ai/structured_outputs.py
from pydantic import BaseModel
from litellm import completion
import json

class FormatDetectionResult(BaseModel):
    columns: dict[str, int | None]
    date_format: str
    amount_style: str
    skip_rows: int
    source_guess: str | None
    confidence: float

async def detect_format(headers: list[str], sample_rows: list[list[str]]) -> FormatDetectionResult:
    response = await completion(
        model=settings.ai_model,
        messages=[
            {"role": "system", "content": FORMAT_DETECTION_SYSTEM},
            {"role": "user", "content": FORMAT_DETECTION_USER.format(
                headers=headers,
                sample_rows=sample_rows
            )}
        ],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return FormatDetectionResult(**result)
```

---

## Deduplication Logic

```python
# services/deduplication_service.py
import hashlib
from datetime import date
from decimal import Decimal

def generate_transaction_hash(
    txn_date: date,
    amount: Decimal,
    raw_description: str,
    account_id: str
) -> str:
    """
    Generate a unique hash for deduplication.
    
    Uses date + amount + description + account to identify duplicates.
    This handles:
    - Re-importing the same file
    - Overlapping date ranges in imports
    """
    components = [
        txn_date.isoformat(),
        str(amount),
        raw_description.strip().lower(),
        account_id
    ]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode()).hexdigest()

def is_duplicate(session: Session, hash: str) -> bool:
    return session.query(Transaction).filter_by(hash=hash).first() is not None
```

### Edge Cases

1. **Same merchant, same amount, same day**: Could be legitimate (two coffees). Hash includes raw_description which usually has unique transaction IDs embedded.

2. **Transfers**: Show as expense on one account, income on another. Handled by account_id in hash - they're separate transactions.

3. **Pending vs Posted**: Some exports show both. Raw description usually differs. If not, we accept the duplicate risk (rare).

---

## Import Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────►│   Detect    │────►│   Preview   │
│   File      │     │   Format    │     │   & Confirm │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┘
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Parse     │────►│   Dedupe    │────►│  Categorize │
│   Rows      │     │   Check     │     │   (AI)      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┘
                    ▼
┌─────────────┐     ┌─────────────┐
│   Save to   │────►│   Move to   │
│   Database  │     │   processed/│
└─────────────┘     └─────────────┘
```

1. **Upload**: User drops file in UI or inbox folder
2. **Detect**: AI analyzes headers/rows, checks against learned_formats
3. **Preview**: Show first N rows with detected mapping, let user adjust
4. **Confirm**: User selects account, confirms format, optionally saves format
5. **Parse**: Apply format mapping to all rows
6. **Dedupe**: Skip rows with existing hashes
7. **Categorize**: Batch AI categorization (with user corrections as few-shot)
8. **Save**: Insert transactions, log import
9. **Cleanup**: Move file to processed/ (or failed/ if errors)

---

## UI Wireframes

### Dashboard

```
┌────────────────────────────────────────────────────────────────┐
│  ┌──────────┐                                                  │
│  │ $        │  Spendah                            [Settings]   │
│  └──────────┘                                                  │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│  Dashboard   │  January 2025                    [◄] [Month] [►]│
│              │                                                 │
│  Transactions│  ┌─────────────────┐  ┌─────────────────┐      │
│              │  │ Spent           │  │ vs December     │      │
│  Recurring   │  │ $4,231.45       │  │ ▲ +12.3%        │      │
│              │  └─────────────────┘  └─────────────────┘      │
│  Accounts    │                                                 │
│              │  ┌─────────────────┐  ┌─────────────────┐      │
│  Import      │  │ Income          │  │ Net             │      │
│              │  │ $6,500.00       │  │ +$2,268.55      │      │
│  ──────────  │  └─────────────────┘  └─────────────────┘      │
│              │                                                 │
│  Settings    │  Spending by Category                           │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ ████████████████████████  Food    $892  │   │
│              │  │ ██████████████████        Housing $723  │   │
│              │  │ █████████████             Transport $534│   │
│              │  │ ████████                  Shopping $412 │   │
│              │  │ ██████                    Other    $670 │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  Recent Transactions                            │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ Jan 5   Amazon           Shopping  -$45 │   │
│              │  │ Jan 4   Spotify          Subscript -$11 │   │
│              │  │ Jan 4   Whole Foods      Groceries -$89 │   │
│              │  │ Jan 3   Shell Gas        Transport -$52 │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                    [View All →] │
│              │                                                 │
│              │  Upcoming Recurring                             │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ Jan 8   Netflix          ~$15.99        │   │
│              │  │ Jan 15  Electric Bill    ~$120          │   │
│              │  │ Feb 1   Rent             ~$2,100        │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

### Transactions

```
┌────────────────────────────────────────────────────────────────┐
│  Transactions                                                  │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│  [Sidebar]   │  ┌─────────────────────────────────────────┐   │
│              │  │ 🔍 Search...          [All Accounts ▼]  │   │
│              │  │ [All Categories ▼]    [Date Range  ▼]   │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ □  Date     Merchant      Category  Amt │   │
│              │  ├─────────────────────────────────────────┤   │
│              │  │ □  Jan 5   Amazon        [Shopping▼] -45│   │
│              │  │ □  Jan 4   Spotify     ○ [Subscr. ▼] -11│   │
│              │  │ □  Jan 4   Whole Foods   [Grocerie▼] -89│   │
│              │  │ □  Jan 3   Shell Gas     [Transpor▼] -52│   │
│              │  │ □  Jan 2   Paycheck      [Income  ▼]+6500│  │
│              │  │ ...                                      │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  [◄ Prev]  Page 1 of 24  [Next ►]              │
│              │                                                 │
│              │  Selected: 0  [Bulk Categorize] [Mark Recurring]│
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘

Note: ○ = recurring indicator
      Category dropdowns allow inline editing
```

### Import

```
┌────────────────────────────────────────────────────────────────┐
│  Import Transactions                                           │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│  [Sidebar]   │  ┌─────────────────────────────────────────┐   │
│              │  │                                         │   │
│              │  │     ┌─────────────────────────┐         │   │
│              │  │     │                         │         │   │
│              │  │     │    Drop CSV/OFX here    │         │   │
│              │  │     │    or click to browse   │         │   │
│              │  │     │                         │         │   │
│              │  │     └─────────────────────────┘         │   │
│              │  │                                         │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  Recent Imports                                 │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ chase_jan.csv    Jan 5   ✓ 45 imported  │   │
│              │  │ amex_dec.csv     Dec 28  ✓ 32 imported  │   │
│              │  │ ally_dec.csv     Dec 15  ✓ 18 imported  │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

### Import Confirmation Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Confirm Import                                         [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Detected format: Chase Credit Card CSV (92% confidence)   │
│                                                             │
│  Column Mapping:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Date:        [Column 1: "Transaction Date" ▼]       │   │
│  │ Amount:      [Column 4: "Amount"            ▼]       │   │
│  │ Description: [Column 3: "Description"       ▼]       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Preview:                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 01/05/2025 | AMAZON.COM*1X2Y3Z      | -$45.99       │   │
│  │ 01/04/2025 | SPOTIFY USA            | -$10.99       │   │
│  │ 01/04/2025 | WHOLE FOODS #1234      | -$89.23       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Account: [Chase Sapphire ▼]     [+ New Account]           │
│                                                             │
│  ☑ Save this format for future imports                     │
│    Format name: [Chase Sapphire CSV_________]              │
│                                                             │
│                          [Cancel]  [Import 127 Transactions]│
└─────────────────────────────────────────────────────────────┘
```

### Dashboard with Alert Bell

```
┌────────────────────────────────────────────────────────────────┐
│  ┌──────────┐                                                  │
│  │ $        │  Spendah                      [🔔 3]  [Settings] │
│  └──────────┘                                  ▲               │
│                                                │               │
│                              ┌─────────────────┴─────────────┐ │
│                              │ ● $847 at Best Buy - unusual  │ │
│                              │ ● Netflix price increased     │ │
│                              │ ● Annual iCloud charge coming │ │
│                              │                  [View All →] │ │
│                              └───────────────────────────────┘ │
├──────────────┬─────────────────────────────────────────────────┤
│  ...         │  ...                                            │
```

### Alerts / Insights Page

```
┌────────────────────────────────────────────────────────────────┐
│  Insights & Alerts                              [🔔 3]         │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│  Dashboard   │  ┌─────────────────────────────────────────┐   │
│              │  │ Subscription Summary        [Review →]  │   │
│  Transactions│  │ 14 active subscriptions                 │   │
│              │  │ $127.43/month ($1,529/year)             │   │
│  Recurring   │  │ ▲ +$12 vs last month                    │   │
│              │  └─────────────────────────────────────────┘   │
│  Accounts    │                                                 │
│              │  Needs Attention                                │
│  Import      │  ┌─────────────────────────────────────────┐   │
│              │  │ ⚠️ ATTENTION                             │   │
│  ▶ Insights  │  │ Large Purchase Detected                 │   │
│              │  │ $847.23 at Best Buy                      │   │
│  ──────────  │  │ This is 5.2x your usual Electronics     │   │
│              │  │ spending of $163/month                   │   │
│  Settings    │  │                                          │   │
│              │  │ Jan 5, 2025        [Dismiss] [View Txn]  │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ ⚡ WARNING                               │   │
│              │  │ Price Increase: Netflix                  │   │
│              │  │ Was $15.99/mo → Now $18.99/mo (+$3.00)  │   │
│              │  │ Annual impact: +$36/year                 │   │
│              │  │                                          │   │
│              │  │ Jan 4, 2025        [Dismiss] [Keep] [Cancel?]│
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │ ℹ️ INFO                                  │   │
│              │  │ Annual Charge Coming Up                  │   │
│              │  │ iCloud+ ($119.88) renews in 12 days     │   │
│              │  │ Last charged: Jan 17, 2024               │   │
│              │  │                                          │   │
│              │  │ Jan 5, 2025              [Dismiss] [OK]  │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │  Previously Dismissed              [Show ▼]    │
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

### Subscription Review Modal

```
┌─────────────────────────────────────────────────────────────┐
│  90-Day Subscription Review                             [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  You have 14 active subscriptions totaling $127.43/month    │
│                                                             │
│  ┌─ Needs Review ────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  ⚠️ Headspace                              $12.99/mo  │ │
│  │     No related activity in 67 days                    │ │
│  │                               [Keep] [Cancel] [Pause] │ │
│  │                                                        │ │
│  │  ⚠️ Adobe Creative Cloud                   $54.99/mo  │ │
│  │     Last used 45 days ago                             │ │
│  │                               [Keep] [Cancel] [Pause] │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Price Increases Since Last Review ───────────────────┐ │
│  │                                                        │ │
│  │  Netflix              $15.99 → $18.99    +$3.00/mo    │ │
│  │  Spotify              $10.99 → $11.99    +$1.00/mo    │ │
│  │                                                        │ │
│  │  Total increase: +$4.00/mo (+$48/year)                │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Annual Renewals Coming Up ───────────────────────────┐ │
│  │                                                        │ │
│  │  Jan 17   iCloud+           $119.88/year              │ │
│  │  Feb 3    Amazon Prime      $139.00/year              │ │
│  │  Mar 15   1Password         $35.88/year               │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ All Good ✓ ──────────────────────────────────────────┐ │
│  │  Showing 8 more subscriptions with regular activity   │ │
│  │                                     [Show Details ▼]  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│                    [Remind Me Later]  [Complete Review]     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Settings - Alert Configuration

```
┌────────────────────────────────────────────────────────────────┐
│  Settings                                                      │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│  [Sidebar]   │  Alerts & Insights                              │
│              │  ┌─────────────────────────────────────────┐   │
│              │  │                                         │   │
│              │  │  Enable Alerts              [━━━━●]  ON │   │
│              │  │                                         │   │
│              │  │  ─────────────────────────────────────  │   │
│              │  │                                         │   │
│              │  │  Large Purchase Detection               │   │
│              │  │  Alert when purchase exceeds:           │   │
│              │  │  [ 3.0 ]x category average              │   │
│              │  │  - or -                                 │   │
│              │  │  Fixed threshold: $[      ] (optional)  │   │
│              │  │                                         │   │
│              │  │  ─────────────────────────────────────  │   │
│              │  │                                         │   │
│              │  │  New Merchant Alert                     │   │
│              │  │  Alert for first-time merchants over:   │   │
│              │  │  $[ 200 ]                               │   │
│              │  │                                         │   │
│              │  │  ─────────────────────────────────────  │   │
│              │  │                                         │   │
│              │  │  Subscription Review                    │   │
│              │  │  Remind me every: [ 90 ▼] days          │   │
│              │  │  Last review: Dec 5, 2024               │   │
│              │  │                    [Trigger Review Now] │   │
│              │  │                                         │   │
│              │  │  ─────────────────────────────────────  │   │
│              │  │                                         │   │
│              │  │  Annual Charge Warning                  │   │
│              │  │  Warn me [ 14 ] days before renewal     │   │
│              │  │                                         │   │
│              │  └─────────────────────────────────────────┘   │
│              │                                                 │
│              │                                      [Save]     │
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

### Phase 1: Foundation (Week 1)
- [ ] Project scaffolding (backend + frontend)
- [ ] Docker Compose setup
- [ ] Database models + Alembic migrations
- [ ] Basic CRUD APIs (accounts, categories)
- [ ] Seed default categories
- [ ] Basic UI shell with routing

### Phase 2: Import Pipeline (Week 2)
- [ ] File upload endpoint
- [ ] CSV parser (basic, no AI yet)
- [ ] OFX/QFX parser
- [ ] Deduplication service
- [ ] Import UI with file drop
- [ ] Import history/logs

### Phase 3: AI Integration (Week 3)
- [ ] LiteLLM client setup
- [ ] Format detection prompt + flow
- [ ] learned_formats storage
- [ ] Format confirmation UI
- [ ] Merchant cleaning prompt
- [ ] Categorization prompt + batch processing
- [ ] User corrections storage + few-shot feeding

### Phase 4: Core Features (Week 4)
- [ ] Transaction list with search/filter
- [ ] Inline category editing
- [ ] Bulk operations
- [ ] Dashboard summary view
- [ ] Category breakdown chart
- [ ] Month selector

### Phase 5: Recurring & Alerts (Week 5-6)
- [ ] Recurring detection prompt
- [ ] Recurring groups management
- [ ] Upcoming recurring view
- [ ] **Alerts data model + API**
- [ ] **Anomaly detection on import**
- [ ] **Large purchase detection**
- [ ] **Price increase detection**
- [ ] **Alert bell UI component**
- [ ] **Alerts/Insights page**

### Phase 6: Subscription Intelligence (Week 7)
- [ ] **Annual charge detection + prediction**
- [ ] **Subscription review prompt**
- [ ] **Subscription review modal UI**
- [ ] **Alert settings configuration UI**
- [ ] **Scheduled subscription review trigger**
- [ ] Trends chart (month over month)
- [ ] Settings page (model selection, alert thresholds)
- [ ] Error handling + edge cases

### Phase 7: Nice-to-Haves (Future)
- [ ] Budget targets per category
- [ ] Export functionality
- [ ] Dark mode
- [ ] Chat interface for queries
- [ ] Watched folder auto-import
- [ ] Email/push notifications for alerts

---

## Configuration

### .env.example

```bash
# App
APP_NAME=Spendah

# Database
DATABASE_URL=sqlite:///./data/db.sqlite

# AI Provider (ollama, openai, anthropic)
AI_PROVIDER=ollama
AI_MODEL=llama3.1:8b
AI_BASE_URL=http://localhost:11434

# For cloud providers (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Import paths
IMPORT_INBOX_PATH=./data/imports/inbox
IMPORT_PROCESSED_PATH=./data/imports/processed
IMPORT_FAILED_PATH=./data/imports/failed

# Server
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:5173
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/db.sqlite
      - AI_PROVIDER=${AI_PROVIDER:-ollama}
      - AI_MODEL=${AI_MODEL:-llama3.1:8b}
      - AI_BASE_URL=${AI_BASE_URL:-http://host.docker.internal:11434}
    depends_on:
      - migrate

  frontend:
    build:
      context: .
      dockerfile: Dockerfile
      target: frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
      target: api
    command: alembic upgrade head
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/db.sqlite

volumes:
  data:
```

---

## Claude Code Configuration

### .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Bash(npm install*)",
      "Bash(npm run*)",
      "Bash(npx*)",
      "Bash(pip install*)",
      "Bash(python*)",
      "Bash(pytest*)",
      "Bash(alembic*)",
      "Bash(docker*)",
      "Bash(sqlite3*)",
      "Bash(cat*)",
      "Bash(ls*)",
      "Bash(mkdir*)",
      "Bash(cp*)",
      "Bash(mv*)",
      "Bash(rm*)",
      "Bash(curl*)",
      "Bash(head*)",
      "Bash(tail*)",
      "Bash(grep*)",
      "Write(*)"
    ],
    "deny": []
  }
}
```

### MCP Configuration (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/spendah"]
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "/path/to/spendah/data/db.sqlite"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

---

## CLAUDE.md

```markdown
# Spendah

Local-first personal finance tracker with AI-powered categorization.

**Note:** "Spendah" is a working title. The app name is stored in `backend/app/config.py` as `APP_NAME` - update there if rebranding.

## Quick Start

```bash
docker-compose up
# API: http://localhost:8000
# UI: http://localhost:5173
```

## Stack

- Backend: Python 3.11, FastAPI, SQLite, LiteLLM
- Frontend: React, TypeScript, Tailwind, shadcn/ui
- AI: Configurable (Ollama default, supports OpenAI/Anthropic)

## Project Structure

See spec for full structure. Key paths:
- `backend/app/` - FastAPI application
- `frontend/src/` - React application  
- `data/` - SQLite DB + import folders (gitignored)

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && pytest
cd frontend && npm test
```

## Key Patterns

1. **Repository pattern** for DB access
2. **Service layer** for business logic
3. **Pydantic** for all validation
4. **LiteLLM** for model abstraction - never hardcode model names
5. **Structured outputs** (JSON mode) for all AI calls

## Current Phase

Phase 1: Foundation

## AI Integration Notes

- Prompts live in `backend/app/ai/prompts/`
- All LLM calls logged for debugging
- User corrections feed back as few-shot examples
- Default model: llama3.1:8b via Ollama
```

---

## Testing Strategy

### Backend Tests

```python
# tests/conftest.py
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_ai_client():
    with patch("app.ai.client.completion") as mock:
        yield mock

# tests/test_deduplication.py
def test_duplicate_transaction_skipped(db_session):
    txn1 = create_transaction(date="2025-01-05", amount=-45.99, description="AMAZON")
    db_session.add(txn1)
    db_session.commit()
    
    result = import_service.import_transaction(
        date="2025-01-05", 
        amount=-45.99, 
        description="AMAZON",
        account_id=txn1.account_id
    )
    
    assert result.skipped == True
    assert result.reason == "duplicate"
```

### Frontend Tests

```typescript
// src/hooks/useTransactions.test.ts
describe('useTransactions', () => {
  it('filters by category', async () => {
    const { result } = renderHook(() => 
      useTransactions({ categoryId: 'groceries' })
    );
    
    await waitFor(() => {
      expect(result.current.data.items).toHaveLength(5);
      expect(result.current.data.items[0].category.name).toBe('Groceries');
    });
  });
});
```

---

## Security Considerations

1. **No auth for MVP** - localhost only, single user assumed
2. **File uploads** - validate file types, scan for malicious content
3. **SQL injection** - SQLAlchemy ORM prevents this
4. **API keys** - stored in .env, never committed
5. **Future**: Add optional basic auth for remote access

---

## Future Enhancements

1. **Chat interface** - natural language queries ("how much did I spend on food last month?")
2. **Budget alerts** - notifications when approaching limits
3. **Receipt scanning** - OCR for paper receipts
4. **Multi-currency** - conversion and tracking
5. **Mobile app** - React Native or PWA
6. **Bank sync** - optional Plaid integration for those who want it
7. **Household mode** - multi-user with shared/personal categories
