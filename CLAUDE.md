# Spendah

Local-first personal finance tracker with AI-powered categorization. Self-hosted, no cloud bank connections — privacy and data ownership first.

**Note:** "Spendah" is a working title. The app name is stored in `backend/app/config.py` as `APP_NAME` — update there if rebranding.

## Quick Start

```bash
docker-compose up
# API: http://localhost:8000 (configurable via API_PORT)
# UI: http://localhost:5173 (configurable via FRONTEND_PORT)
```

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite, Alembic
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **AI:** LiteLLM for model abstraction (supports OpenRouter, Ollama, OpenAI, Anthropic)
- **Infra:** Docker Compose, multi-stage Dockerfile

## Project Structure

```
backend/app/
├── main.py              # FastAPI entry point
├── config.py            # Settings (pydantic-settings)
├── database.py          # SQLAlchemy + session management
├── dependencies.py      # FastAPI DI
├── seed.py              # Default category seeding
├── models/              # SQLAlchemy models (12 tables)
├── schemas/             # Pydantic schemas
├── api/                 # Route handlers
├── services/            # Business logic layer
├── ai/
│   ├── client.py        # LiteLLM wrapper
│   └── prompts/         # AI prompt templates
└── parsers/             # CSV/OFX file parsers

frontend/src/
├── pages/               # 9 page components
├── components/          # Reusable UI components
├── lib/                 # API client, formatters, utils
├── types/               # TypeScript type definitions
└── App.tsx              # Route configuration

data/                    # SQLite DB + import folders (gitignored)
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
cd backend && pytest
cd frontend && npm test

# Docker
docker compose up -d --build          # Build and start
docker compose down                    # Stop
docker compose exec api alembic upgrade head  # Run migrations
```

## Key Patterns

1. **Repository pattern** for DB access
2. **Service layer** for business logic (never put logic in route handlers)
3. **Pydantic v2** for all validation and structured outputs
4. **LiteLLM** for model abstraction — never hardcode model names
5. **Structured outputs** (JSON mode) for all AI calls
6. **TanStack Query** for frontend server state management
7. **React Router v6** for client-side routing

## Current Phase

**Phases 1–7: Complete.** Phase 8 (Coach Foundation) is next.

### Completed Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Foundation (models, CRUD, UI scaffold) | Complete |
| 2 | File Import (CSV/OFX/QFX, dedup, preview) | Complete |
| 3 | AI Integration (categorization, merchant cleaning, format detection) | Complete |
| 4 | Budgeting (budgets, progress tracking, alerts) | Complete |
| 5a | Recurring Detection (AI pattern detection, subscription management) | Complete |
| 5b | Alert System (8 alert types, subscription review, annual charges) | Complete |
| 6 | Net Worth Backend (balance tracking, snapshots, history) | Complete |
| 7 | Privacy & Tokenization (sensitive data handling) | Complete |

### Phase 8: Coach Foundation (Next)

- Conversational AI Coach interface
- Conversation/Message models with tokenized storage
- Context assembly from financial data
- Embedded widget/drawer in layout
- Spec: `spendah-phase8-prompt.md`

## Database Schema

All models in `backend/app/models/`. 12 tables:

| Table | Purpose |
|-------|---------|
| `accounts` | Financial accounts with balance tracking and type classification |
| `categories` | Hierarchical transaction categories (parent-child) |
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

## API Endpoints

Base URL: `/api/v1`

- **Health:** `GET /health`
- **Accounts:** CRUD + `POST /{id}/balance` for balance updates
- **Categories:** CRUD with tree structure, reassigns to "Other" on delete
- **Transactions:** CRUD + filtering (account, category, date range, search, recurring) + `POST /bulk-categorize`
- **Imports:** `POST /upload`, `POST /{id}/confirm`, `GET /{id}/status`, `GET /history`
- **Budgets:** CRUD + `GET /{id}/progress` + `POST /check-alerts`
- **Alerts:** CRUD + `GET /unread-count`, `POST /mark-all-read`, `POST /subscription-review`, `GET /upcoming-renewals`, `POST /detect-annual`, settings endpoints
- **Dashboard:** `GET /summary`, `GET /trends`, `GET /recent-transactions`
- **Recurring:** CRUD + `POST /detect` (AI detection)
- **Net Worth:** `GET /networth`, `GET /networth/breakdown`, `GET /networth/history`, `POST /networth/auto-snapshot`
- **Settings:** `GET /settings`, `PATCH /settings`
- **Privacy:** `GET /settings`, `POST /tokenize`, `POST /detokenize`

## AI Integration

- Prompts live in `backend/app/ai/prompts/` (6 prompt modules)
- LiteLLM client wrapper in `backend/app/ai/client.py`
- Capabilities: categorization, merchant cleaning, format detection, recurring detection, subscription review, annual charge detection, anomaly detection
- User corrections feed back as few-shot examples
- All LLM calls logged for debugging
- Configure via Settings page or env vars (`AI_PROVIDER`, `AI_MODEL`)

## Tests

14 test files in `backend/tests/` using pytest with SQLite StaticPool for isolation:

- API tests: health, accounts, categories, transactions, alerts, budgets
- Service tests: alerts, budget alerts, deduplication, recurring, tokenization
- Integration tests: net worth, financial overview, balance import

## Known Gotchas

1. After model changes: `docker compose exec api alembic revision --autogenerate -m "msg"` then `alembic upgrade head`
2. Don't use `metadata` as a column name (SQLAlchemy reserved)
3. Circular FKs need explicit `foreign_keys=` in relationships
4. Dockerfile uses `npm install` not `npm ci`
5. Run `docker compose up -d --build` and test endpoints before marking phases complete
6. Account model uses `account_type` field (not `type`)
7. Alert routing: put `/settings` before `/{alert_id}` in router
8. Account classification: `is_asset` property determines asset vs liability (checking/savings/investment/cash = asset; credit_card/loan/mortgage/other = liability)
9. Frontend API client uses `window.location.hostname` dynamically (not hardcoded localhost)
10. OpenRouter uses `OPENROUTER_API_KEY` env var
