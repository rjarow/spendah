# Spendah

Local-first personal finance tracker with AI-powered categorization. Self-hosted, no cloud bank connections — privacy and data ownership first.

**Note:** "Spendah" is a working title. The app name is stored in `backend/app/config.py` as `APP_NAME` — update there if rebranding.

## Quick Start

```bash
docker compose up -d --build
# API: http://localhost:8000 (configurable via API_PORT)
# UI: http://localhost:5173 (configurable via FRONTEND_PORT)
# Both ports bound to 127.0.0.1 only (not accessible from LAN)
```

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite (WAL mode), Alembic
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **AI:** LiteLLM for model abstraction (supports OpenRouter, Ollama, OpenAI, Anthropic)
- **Infra:** Docker Compose, multi-stage Dockerfile, slowapi rate limiting

## Project Structure

```
backend/app/
├── main.py              # FastAPI entry, CORS, rate limiting
├── config.py            # Settings (pydantic-settings)
├── database.py          # SQLAlchemy + SQLite WAL mode + busy_timeout
├── dependencies.py      # FastAPI DI
├── seed.py              # Default category seeding
├── models/              # SQLAlchemy models (16 tables)
├── schemas/             # Pydantic v2 schemas
├── api/                 # Route handlers (13 routers)
├── services/            # Business logic layer (14 services)
├── ai/
│   ├── client.py        # LiteLLM wrapper (async, multi-provider)
│   ├── prompts/         # AI prompt templates (8 modules)
│   └── sanitization.py  # Prompt injection defense
└── parsers/             # CSV/OFX file parsers

frontend/src/
├── pages/               # 12 page components
├── components/          # Reusable UI components (layout, coach, alerts, ui)
├── lib/                 # API client, formatters, utils
├── types/               # TypeScript type definitions
├── hooks/               # Custom React hooks
└── App.tsx              # Route configuration

data/                    # SQLite DB + import folders (gitignored)
├── db.sqlite
└── imports/{inbox,processed,failed}/
```

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.seed  # Seed default categories
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && .venv/bin/pytest          # All tests
.venv/bin/pytest tests/test_smoke.py    # Smoke tests
.venv/bin/pytest -k "transaction"       # Pattern match

# Docker
docker compose up -d --build
docker compose down
docker compose exec api alembic upgrade head  # Run migrations in container
docker compose logs api                       # View API logs
```

## Key Patterns

1. **Service layer** for business logic — never put query logic in route handlers
2. **Pydantic v2** for all validation — use `model_validate()` not `from_orm()`
3. **LiteLLM** for model abstraction — never hardcode model names
4. **Structured outputs** (JSON mode) for all AI calls
5. **TanStack Query** for frontend server state management
6. **React Router v6** for client-side routing
7. **SQLite WAL mode** with `busy_timeout=5000` for concurrent access
8. **Batch operations** for alert analysis and categorization during imports (pre-compute lookups, avoid N+1)
9. **`model_validate()` with `validation_alias`** for ORM-to-schema mapping where field names differ (e.g., `alert_metadata` -> `metadata`)

## Current Status

**Phases 1-8: Complete.** Phase 9 (UI overhaul, rules engine, insights) is in progress. A hardening pass was completed on 2026-03-27 covering performance, security, and code cleanup.

### Completed Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Foundation (models, CRUD, Docker) | Complete |
| 2 | File Import (CSV/OFX/QFX, dedup, preview) | Complete |
| 3 | AI Integration (categorization, merchant cleaning, format detection) | Complete |
| 4 | Budgeting (budgets, progress tracking, alerts) | Complete |
| 5a | Recurring Detection (AI pattern detection, subscription management) | Complete |
| 5b | Alert System (8 alert types, subscription review, annual charges) | Complete |
| 6 | Net Worth (balance tracking, snapshots, history) | Complete |
| 7 | Privacy & Tokenization (sensitive data handling) | Complete |
| 8 | Coach Foundation (conversational AI, chat interface, context assembly) | Complete |

### Recent: Hardening Pass (2026-03-27)

- Fixed N+1 queries in coach and alert services (batch pre-fetch)
- Replaced Python-side sums with SQL aggregates (balance inference, budgets)
- Added SQLite WAL mode + busy_timeout
- Tightened CORS (explicit methods/headers instead of wildcards)
- Added rate limits to AI-calling endpoints
- Streaming upload size check (chunked reads, abort early)
- Bound Docker ports to 127.0.0.1
- Removed dead code and unused functions
- Fixed date arithmetic bugs in insights/dashboard

## Database Schema

All models in `backend/app/models/`. 16 tables:

| Table | Purpose |
|-------|---------|
| `accounts` | Financial accounts with balance tracking and type classification |
| `categories` | Hierarchical transaction categories (parent-child, with LLM prompts) |
| `transactions` | Individual transactions with SHA256 dedup hash |
| `recurring_groups` | Subscription/recurring payment groups |
| `budgets` | Per-category budgets (weekly/monthly/yearly) |
| `alerts` | Notifications (8 types, 3 severity levels) |
| `alert_settings` | Alert threshold configuration |
| `balance_history` | Net worth snapshots over time |
| `learned_formats` | Saved CSV column mappings |
| `import_logs` | Import history and status |
| `user_corrections` | AI training data from user edits |
| `privacy_settings` | Tokenization configuration |
| `token_map` | Tokenization reverse lookup (merchant/name/account tokens) |
| `conversations` | Coach chat threads |
| `messages` | Individual chat messages (user/assistant roles) |
| `rules` | Categorization rules (match by merchant/description, exact/contains) |
| `ai_settings` | API key storage and model selection per task |
| `ai_token_usage` | LLM token consumption logging |

## API Endpoints

Base URL: `/api/v1`

- **Health:** `GET /health`
- **Accounts:** CRUD + `POST /{id}/balance` for balance updates
- **Categories:** CRUD with tree structure, reassigns to "Other" on delete
- **Transactions:** CRUD + filtering (account, category, date range, search, recurring) + `POST /bulk-categorize`
- **Imports:** `POST /upload` (rate limited), `POST /{id}/confirm` (rate limited), `GET /{id}/status`, `GET /history`
- **Budgets:** CRUD + `GET /{id}/progress` + `POST /check-alerts`
- **Alerts:** CRUD + `GET /unread-count`, `POST /mark-all-read`, `POST /subscription-review`, `GET /upcoming-renewals`, `POST /detect-annual`, settings endpoints
- **Dashboard:** `GET /summary`, `GET /trends`, `GET /recent-transactions`, `GET /account-balances`, `GET /category-trends`, `GET /savings-rate`
- **Recurring:** CRUD + `POST /detect` (AI detection, rate limited)
- **Net Worth:** `GET /networth`, `GET /networth/breakdown`, `GET /networth/history`, `POST /networth/auto-snapshot`
- **Coach:** `POST /messages` (rate limited), `GET /conversations/{id}`, `GET /conversations`, `GET /quick-questions`
- **Rules:** CRUD for categorization rules
- **Insights:** `GET /spending-trends`, `GET /category-breakdown`, `GET /merchant-ranking`, `GET /monthly-summary`
- **Settings:** `GET /settings`, `PATCH /settings`, API key management, provider/model selection
- **Privacy:** `GET /settings`, `POST /tokenize`, `POST /detokenize`, token management

## AI Integration

- Prompts live in `backend/app/ai/prompts/` (8 prompt modules)
- LiteLLM client wrapper in `backend/app/ai/client.py` (async via `acompletion`)
- Prompt injection sanitization in `backend/app/ai/sanitization.py`
- Capabilities: categorization, merchant cleaning, format detection, recurring detection, subscription review, annual charge detection, anomaly detection, coach conversations
- User corrections feed back as few-shot examples
- Token usage logged to `ai_token_usage` table
- Privacy: tokenization layer obfuscates PII before sending to cloud providers (per-provider toggle)
- Configure via Settings page or env vars (`AI_PROVIDER`, `AI_MODEL`)

## Tests

22 test files in `backend/tests/` using pytest with SQLite StaticPool for isolation:

- API tests: health, accounts, categories, transactions, alerts, budgets, dashboard, imports, networth, privacy, recurring, settings
- Service tests: alerts, budget alerts, coach, deduplication, recurring, tokenization
- Integration tests: financial overview, balance import, CSV parser, smoke tests

### Known Pre-Existing Test Failures

- `test_networth.py::TestBalanceInference::test_get_networth_breakdown_with_calculated_balance` — test expects `current_balance` but service uses calculated balance from transactions
- `test_financial_overview.py::test_financial_overview_with_transaction_balances` — same root cause
- `test_financial_overview.py::test_financial_overview_integration_multiple_categories` — same root cause

These tests need their assertions updated to account for the calculated balance logic in `get_networth_breakdown`.

## Known Gotchas

1. After model changes: `docker compose exec api alembic revision --autogenerate -m "msg"` then `alembic upgrade head`
2. Don't use `metadata` as a column name (SQLAlchemy reserved) — Alert model uses `alert_metadata` with `validation_alias` in schema
3. Circular FKs need explicit `foreign_keys=` in relationships
4. Dockerfile uses `npm install` not `npm ci`
5. Account model uses `account_type` field (not `type` — reserved word)
6. Alert routing: put `/settings` before `/{alert_id}` in router (order matters)
7. Account classification: `is_asset` property on the Account model determines asset vs liability — always use this property, don't inline the check
8. Frontend API client uses `window.location.hostname` dynamically (not hardcoded localhost)
9. OpenRouter uses `OPENROUTER_API_KEY` env var (not `OPENAI_API_KEY`)
10. Docker ports bound to `127.0.0.1` — not accessible from LAN by default
11. CORS restricted to specific methods/headers — if frontend adds custom headers, update `main.py`
12. `PENDING_IMPORTS` dict in `import_service.py` is in-process memory — won't survive restart or multi-worker deployment
13. Service layer uses mixed patterns: some class-based (TransactionService, CategoryService, CoachService, TokenizationService), others are module-level functions — not yet unified

## Architecture Notes

### Balance Inference
`get_calculated_balance()` in `balance_inference.py` derives account balances from transactions, not `current_balance`. For asset accounts, it's `current_balance + sum(transactions)`. For liability accounts with no transactions, it falls back to `current_balance`. The `is_stale` flag indicates when calculated differs from manual.

### Alert Batch Analysis
During imports, alerts are analyzed in batch (`analyze_transactions_for_alerts_batch`) with pre-computed lookups for category averages, known merchants, recurring groups, and category names — avoiding per-transaction queries.

### Coach Context Assembly
The coach service assembles financial context (account summary, spending by category, recurring charges, trends, recent transactions, alerts) into a structured prompt. All financial data is tokenized before sending to the AI provider.
