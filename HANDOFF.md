# Spendah Project Handoff

> Last updated: January 13, 2026
> Status: Phase 7 complete, test fixes needed before dogfooding
> Repo: https://github.com/rjarow/spendah

## What is Spendah?

Local-first personal finance tracker with AI-powered categorization. Built for Rich, a DevOps engineer who wants to track finances without connecting to banks (privacy-first). Users import CSV/OFX files, AI cleans merchant names and categorizes transactions.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, SQLite, Alembic
- **Frontend:** React 18, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query
- **AI:** LiteLLM with OpenRouter (Claude Haiku) - can also use Ollama, Anthropic, OpenAI
- **Infrastructure:** Docker Compose, runs on Proxmox VM
- **Testing:** pytest with 60 service layer tests (some failing - see below)

## Project Location

```
VM: 192.168.1.217 (devbox on Proxmox homelab)
User: rj
Path: ~/projects/spendah
Repo: https://github.com/rjarow/spendah
```

## Current Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation (models, basic CRUD, Docker) | ✅ Complete |
| Phase 2 | Import Pipeline (CSV/OFX parsing, dedup) | ✅ Complete |
| Phase 3 | AI Integration (LiteLLM, categorization) | ✅ Complete |
| Phase 4 | Core Features (transaction UI, dashboard) | ✅ Complete |
| Phase 5a | Recurring Detection | ✅ Complete |
| Phase 5b | Alerts System | ✅ Complete |
| Phase 6 | Subscription Intelligence | ✅ Complete |
| Phase 7 | Privacy & Tokenization | ✅ Complete |
| Test Fixes | Pre-existing test failures | 🔄 Next |
| Dogfooding | Test with real bank data | ⏳ After test fixes |
| Phase 8 | Coach Foundation | ⏳ After dogfooding |

### Pre-Existing Test Failures (Must Fix Before Dogfooding)

These issues existed before Phase 7 and need to be fixed:

1. **`backend/tests/conftest.py` line ~47**: `sample_account` fixture sets `account.type` but column is `account_type`
   - Fix: Change to `account.account_type = AccountType.bank`

2. **`backend/tests/test_api_accounts.py`**: `test_create_account` sends `AccountType.bank` enum in JSON
   - Fix: Should be string `"bank"` not enum

3. **`backend/tests/test_api_alerts.py`**: Missing imports
   - Fix: Add `from datetime import date`, `from decimal import Decimal`, `from app.models.transaction import Transaction`

4. **`backend/app/services/recurring_service.py` line ~77**: `calculate_next_expected` yearly case crashes on Feb 29 → non-leap year
   - Fix: Wrap `date(last_date.year + 1, last_date.month, last_date.day)` in try/except with fallback to `date(last_date.year + 1, last_date.month, 28)`

5. **`backend/tests/test_recurring_service.py`**: `test_yearly_leap_day` accepts either Feb 28 OR Mar 1 (indeterminate)
   - Fix: Should assert only `date(2025, 2, 28)`

**After fixes, run:** `docker compose exec api pytest -v --tb=short` - should see 60+ tests pass.

### What's Working

**Backend APIs:**
- Health check: `GET /api/v1/health`
- Accounts: Full CRUD
- Categories: Full CRUD with tree structure
- Transactions: CRUD, search, filter, pagination, bulk categorize
- Dashboard: Summary, trends, recent transactions
- Settings: AI provider/model configuration
- Imports: Upload, AI format detection, confirm with categorization
- Recurring: List, create, update, delete, AI-powered detection
- Alerts: List, update, dismiss, delete, settings, unread count
- Subscription Review: AI-powered analysis, upcoming renewals, annual charge detection
- **Privacy: Token management, per-provider obfuscation settings, preview**

**Frontend Pages:**
- Dashboard: Month selector, summary cards, category breakdown, trends chart, upcoming renewals widget
- Transactions: Search, filters, inline category editing, bulk operations
- Import: File drop, AI format detection, column mapping
- Settings: AI provider/model selection, feature toggles, **privacy settings panel**
- Recurring: Detection trigger, group management, summary stats
- Accounts: Basic list and create
- Insights: Alert list, settings panel, dismiss/delete actions, subscription review button
- Alert Bell: Header notification with unread badge, dropdown preview
- Subscription Review Modal: AI insights, cost summary, recommendations

**AI Features:**
- CSV format detection with confidence scoring
- Merchant name cleaning
- Transaction categorization with user correction learning
- Recurring pattern detection
- Anomaly detection (large purchases, unusual merchants, price increases)
- Subscription review with usage analysis
- Annual charge detection and prediction
- **Tokenization: Merchant/account/person tokens, date shifting, per-provider settings**

### Database Tables

```
accounts          alerts            learned_formats   user_corrections
alembic_version   categories        recurring_groups  token_maps
alert_settings    import_logs       transactions      date_shift
```

## Key Files

```
spendah/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── client.py           # LiteLLM wrapper with tokenization
│   │   │   └── prompts/            # format_detection, categorization, 
│   │   │                           # merchant_cleaning, recurring_detection,
│   │   │                           # anomaly_detection, subscription_review,
│   │   │                           # annual_charge_detection
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   ├── accounts.py
│   │   │   ├── categories.py
│   │   │   ├── transactions.py
│   │   │   ├── imports.py
│   │   │   ├── dashboard.py
│   │   │   ├── settings.py
│   │   │   ├── recurring.py
│   │   │   ├── alerts.py           # Includes subscription review endpoints
│   │   │   └── privacy.py          # Token stats, preview, settings
│   │   ├── models/
│   │   │   ├── account.py          # Uses account_type (not type)
│   │   │   └── token_map.py        # TokenMap, DateShift models
│   │   ├── schemas/
│   │   │   ├── alert.py            # Includes subscription review schemas
│   │   │   └── privacy.py          # Privacy settings schemas
│   │   ├── services/
│   │   │   ├── import_service.py
│   │   │   ├── recurring_service.py
│   │   │   ├── alerts_service.py   # Includes subscription review logic
│   │   │   └── tokenization_service.py  # PII tokenization
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py             # Shared fixtures (has bug - see above)
│   │   ├── test_deduplication.py   # 10 tests
│   │   ├── test_recurring_service.py  # 13 tests (has bug - see above)
│   │   ├── test_alerts_service.py  # 20 tests
│   │   ├── test_tokenization.py    # 17 tests (Phase 7)
│   │   └── test_api_*.py           # API tests (need fixes - see above)
│   ├── pytest.ini
│   └── alembic/
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx       # Includes upcoming renewals widget
│       │   ├── Transactions.tsx
│       │   ├── Import.tsx
│       │   ├── Settings.tsx        # Includes privacy settings
│       │   ├── Recurring.tsx
│       │   ├── Accounts.tsx
│       │   └── Insights.tsx        # Includes subscription review trigger
│       ├── components/
│       │   ├── layout/
│       │   ├── alerts/
│       │   │   ├── AlertBell.tsx
│       │   │   └── SubscriptionReviewModal.tsx
│       │   └── settings/
│       │       └── PrivacySettings.tsx  # Phase 7
│       ├── lib/
│       │   ├── api.ts              # Includes privacy API functions
│       │   └── formatters.ts
│       └── types/index.ts          # Includes privacy types
├── test-data/
├── docker-compose.yml
├── .env
├── HANDOFF.md                      # This file
├── spendah-spec.md
└── spendah-phase8-prompt.md        # Next phase
```

## Known Gotchas & Fixes

### 1. Self-Hosted Networking (IMPORTANT!)

**CORS Configuration** - Backend must allow all origins:
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Dynamic API URL** - Frontend must NOT hardcode localhost:
```typescript
// frontend/src/lib/api.ts
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
```

### 2. Account Model Column Name

The column is `account_type`, NOT `type` (SQLAlchemy reserved keyword):
```python
# Correct:
account.account_type = AccountType.bank
# Wrong:
account.type = AccountType.bank
```

### 3. Alert Model Enum Names

Use `Severity` not `AlertSeverity`:
```python
from app.models.alert import Alert, AlertType, Severity
```

### 4. OpenRouter API Key

LiteLLM expects `OPENROUTER_API_KEY`:
```python
os.environ["OPENROUTER_API_KEY"] = key  # NOT OPENAI_API_KEY
```

### 5. Test Data Date Range

Test data is from Jan-June 2024. Recurring detection lookback is 3 years in `recurring_service.py`.

### 6. Running Tests

```bash
# Run all tests
docker compose exec api pytest -v --tb=short

# Run specific test file
docker compose exec api pytest tests/test_deduplication.py -v

# Run with coverage (if installed)
docker compose exec api pytest --cov=app --cov-report=term-missing
```

### 7. Always Restart After Code Changes

```bash
cd ~/projects/spendah
docker compose down
docker compose up -d --build
sleep 5
docker compose logs api --tail 30
```

## Commands Reference

```bash
# Start everything
cd ~/projects/spendah
docker compose up -d --build

# View logs
docker compose logs api --tail 50
docker compose logs frontend --tail 20

# Run tests
docker compose exec api pytest -v --tb=short

# Test endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/alerts
curl http://localhost:8000/api/v1/alerts/upcoming-renewals
curl http://localhost:8000/api/v1/privacy/settings
curl http://localhost:8000/api/v1/privacy/stats
curl -X POST http://localhost:8000/api/v1/alerts/subscription-review

# Access (from any machine on network)
# API: http://192.168.1.217:8000
# Frontend: http://192.168.1.217:5173
```

## Environment Variables

Key vars in `.env` (NOT committed to git):
```
APP_NAME=Spendah
DATABASE_URL=sqlite:///./data/db.sqlite
AI_PROVIDER=openrouter
AI_MODEL=anthropic/claude-3-haiku
OPENROUTER_API_KEY=sk-or-v1-...
PRIVACY_OBFUSCATION_ENABLED=true
PRIVACY_OLLAMA_OBFUSCATION=false
PRIVACY_OPENROUTER_OBFUSCATION=true
```

## Next Steps

1. **Fix pre-existing test failures** (see list above)
2. **Run full test suite** - verify 60+ tests pass
3. **Dogfood with real bank data** - identify friction points
4. **Phase 8: Coach Foundation** - see `spendah-phase8-prompt.md`

## Development Workflow

Rich uses a hybrid AI approach:
- **Claude (Opus via claude.ai):** Architecture decisions, code review, troubleshooting, writing phase prompts
- **Claude Code:** Quick fixes, test debugging, small changes
- **OpenCode (GLM 4.7):** Bulk implementation following detailed phase prompts

Typical flow:
1. Claude writes detailed phase prompt with Progress Tracker and File Manifest
2. OpenCode executes following the prompt step-by-step
3. Rich tests manually
4. Debug any issues with Claude's help
5. Commit and push to GitHub
6. Update HANDOFF.md

## Rich's Preferences

- Prefers practical over perfect
- Values local-first, privacy-focused solutions
- Uses Proxmox homelab for development
- Wants easy provider switching in Settings UI
- Asks for HANDOFF.md updates to preserve context across sessions
- Testing: Focus on critical business logic, skip brittle AI mocks
