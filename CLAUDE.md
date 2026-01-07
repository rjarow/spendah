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
python -m app.seed  # Seed default categories
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

Phase 1: Foundation (Complete)

## Phase 1 Deliverables

### Backend
- FastAPI app with health check endpoint
- All database models (transactions, accounts, categories, recurring_groups, learned_formats, alerts, alert_settings, import_logs, user_corrections)
- Alembic migrations setup
- Seed script for default categories
- CRUD APIs for accounts and categories

### Frontend
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Routing with react-router-dom
- Layout with sidebar navigation
- Placeholder pages (Dashboard, Transactions, Recurring, Accounts, Import, Insights, Settings)
- API client with TanStack Query

### Infrastructure
- Docker Compose with api and frontend services
- Multi-stage Dockerfile
- Environment configuration

## AI Integration Notes (Phase 3+)

- Prompts live in `backend/app/ai/prompts/`
- All LLM calls logged for debugging
- User corrections feed back as few-shot examples
- Default model: llama3.1:8b via Ollama

## Database Schema

All models are defined in `backend/app/models/`. The schema includes:
- **accounts**: Financial account management
- **categories**: Hierarchical transaction categories
- **transactions**: Individual transactions with deduplication
- **recurring_groups**: Subscription and recurring payment tracking
- **learned_formats**: Saved import file formats
- **alerts**: Insights and notifications
- **alert_settings**: Alert configuration
- **import_logs**: Import history tracking
- **user_corrections**: AI training data from user edits

## API Endpoints

Base URL: `/api/v1`

### Health
- `GET /health` - Health check

### Accounts
- `GET /accounts` - List accounts
- `POST /accounts` - Create account
- `GET /accounts/{id}` - Get account
- `PATCH /accounts/{id}` - Update account
- `DELETE /accounts/{id}` - Soft delete account

### Categories
- `GET /categories` - List categories (tree structure)
- `POST /categories` - Create category
- `GET /categories/{id}` - Get category
- `PATCH /categories/{id}` - Update category
- `DELETE /categories/{id}` - Delete category (reassigns transactions to "Other")

## Next Steps (Phase 2)

- File upload endpoint
- CSV parser (basic, no AI yet)
- OFX/QFX parser
- Deduplication service
- Import UI with file drop
- Import history/logs

## Known Gotchas

1. After model changes: `docker compose exec api alembic revision --autogenerate -m "msg"` then `alembic upgrade head`
2. Don't use `metadata` as a column name (SQLAlchemy reserved)
3. Circular FKs need explicit `foreign_keys=` in relationships
4. Dockerfile uses `npm install` not `npm ci`
5. Run `docker compose up -d --build` and test endpoints before marking phases complete
