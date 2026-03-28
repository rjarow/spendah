# AGENTS.md

Coding agent guidelines for the Spendah codebase.

## Multi-Agent Coordination

When you receive a task from the orchestrator (via agent-peers message), follow these rules:

1. **Work in the directory you're given.** If the orchestrator gives you a worktree path, `cd` into it. Never work in the main checkout if told to use a worktree.
2. **Stay in your file scope.** The orchestrator will tell you which files/directories are yours. Do not modify files outside your scope — another agent may be working on them.
3. **Commit when done.** After finishing all tasks, stage your changes and commit. Don't forget this step.
4. **Report back.** Send a message to the orchestrator when you're done, including what you changed and test results.
5. **Run tests before committing.** `cd backend && .venv/bin/pytest` — report pass/fail counts.

## Build/Lint/Test Commands

### Backend (Python)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run all tests (use .venv/bin/pytest, not bare pytest)
.venv/bin/pytest

# Run a single test file
.venv/bin/pytest tests/test_api_transactions.py

# Run a single test by name
.venv/bin/pytest tests/test_api_transactions.py::TestTransactionsAPI::test_list_transactions_empty

# Run tests with verbose output
.venv/bin/pytest -v

# Run tests matching a pattern
.venv/bin/pytest -k "transaction"

# Start development server
uvicorn app.main:app --reload
```

### Frontend (TypeScript/React)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Type check
npx tsc --noEmit --skipLibCheck
```

### Docker

```bash
# Build and start all services
docker compose up -d --build

# Stop services
docker compose down

# Run migrations in container
docker compose exec api alembic upgrade head

# View logs
docker compose logs -f api
```

## Code Style Guidelines

### Backend (Python)

#### Imports
Group imports in this order, separated by blank lines:
1. Standard library
2. Third-party packages
3. Local application imports

```python
import uuid
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.services.transaction_service import TransactionService
```

#### Naming Conventions
- **Files**: snake_case (e.g., `transaction_service.py`)
- **Classes**: PascalCase (e.g., `TransactionService`)
- **Functions/Methods**: snake_case (e.g., `list_transactions`)
- **Variables**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Models**: PascalCase, singular noun (e.g., `Transaction`, `RecurringGroup`)
- **Schemas**: PascalCase with suffix (e.g., `TransactionCreate`, `TransactionResponse`)

#### Docstrings
- Module-level docstrings at top of files
- Class docstrings explaining purpose
- Method docstrings for public methods

```python
"""Transaction service layer."""

class TransactionService:
    """Service for transaction operations."""

    def list_transactions(self, page: int = 1) -> Dict[str, Any]:
        """List transactions with filtering and pagination."""
```

#### Error Handling
- Use HTTPException in API routes with appropriate status codes
- Return None from service methods when entity not found
- Let route handlers convert None to 404

```python
@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    service = TransactionService(db)
    transaction = service.get_transaction(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)
```

#### Patterns
- **Service Layer**: All business logic goes in `services/`, never in route handlers
- **Repository Pattern**: Database access through services, not direct ORM in routes
- **Pydantic v2**: Use `model_validate()` instead of `from_orm()`, `model_dump()` instead of `dict()`
- **IDs**: Use string UUIDs (36 chars): `id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))`

#### Database Models
- Use `account_type` field, not `type` (reserved word conflict)
- Add indexes on foreign keys and frequently queried columns
- Use `ondelete` in ForeignKey for cascade behavior

### Frontend (TypeScript/React)

#### Imports
- Use path alias `@/*` for src imports
- Group: React/external libs, then local imports

```typescript
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getTransactions } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import type { Transaction } from '@/types'
```

#### Naming Conventions
- **Files**: PascalCase for components (e.g., `Dashboard.tsx`)
- **Components**: PascalCase, default export
- **Functions**: camelCase (e.g., `formatCurrency`)
- **Types/Interfaces**: PascalCase (e.g., `TransactionListResponse`)
- **API functions**: camelCase (e.g., `getTransactions`, `updateAccount`)

#### Components
- Functional components with default export
- Use TanStack Query for data fetching

```typescript
export default function Dashboard() {
  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions'],
    queryFn: () => getTransactions({}),
  })

  if (isLoading) return <div>Loading...</div>

  return <div>...</div>
}
```

#### Types
- Define types in `src/types/index.ts`
- Use `interface` for object shapes, `type` for unions/aliases

#### Error Handling
- API client has interceptor that throws Error with message
- Use ErrorBoundary for component-level errors
- Handle loading and error states in components

### AI Integration

- Use LiteLLM via `app/ai/client.py` - never hardcode model names
- All prompts in `app/ai/prompts/`
- Use JSON mode for structured outputs
- User corrections stored in `user_corrections` table for learning

### API Conventions

- Base URL: `/api/v1`
- List endpoints return paginated response with `items`, `total`, `page`, `pages`
- Use `PATCH` for partial updates, `PUT` for full replacements
- Route order matters: static routes (e.g., `/settings`) before parametrized (e.g., `/{id}`)

### Testing

- Backend tests use pytest with in-memory SQLite (StaticPool)
- Fixtures in `conftest.py` create fresh DB per test
- Test classes group related tests: `class TestTransactionsAPI`
- Test names: `test_<action>_<expected_result>` (e.g., `test_list_transactions_empty`)

## Key Architecture Decisions

1. **Local-first**: No cloud bank connections, user imports CSV/OFX files
2. **Privacy**: Tokenization available for AI calls, data stays local
3. **Service Layer**: Routes are thin, services contain logic — never put query logic in route handlers
4. **Pydantic V2**: All validation through schemas, use `model_validate()` with `validation_alias` for field name mismatches
5. **TanStack Query**: Server state management in frontend (all pages, including Coach)
6. **LiteLLM**: Model abstraction for AI features — never hardcode model names
7. **SQLite WAL mode**: Configured in `database.py` with `busy_timeout=5000`
8. **Rate limiting**: Shared `Limiter` instance in `app/rate_limit.py` — import from there, never create your own
9. **Batch operations**: Pre-compute lookups before loops during imports (avoid N+1 queries)
10. **Account classification**: Always use `acc.is_asset` property, never inline string comparisons against account_type

## Known Gotchas

1. After model changes: `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`
2. Don't use `metadata` as column name (SQLAlchemy reserved) — Alert model uses `alert_metadata` with `validation_alias` in schema
3. Circular FKs need explicit `foreign_keys=` in relationships
4. Dockerfile uses `npm install` not `npm ci`
5. Account model uses `account_type` field (not `type` — reserved word)
6. Alert routing: put `/settings` before `/{alert_id}` in router (order matters)
7. Asset vs liability: `is_asset` property on Account model — always use this, never check strings
8. Frontend API client uses `window.location.hostname` dynamically (not hardcoded localhost)
9. OpenRouter uses `OPENROUTER_API_KEY` env var (not `OPENAI_API_KEY`)
10. Docker ports bound to `127.0.0.1` — not accessible from LAN
11. CORS restricted to specific methods/headers — update `main.py` if frontend adds custom headers
12. `PENDING_IMPORTS` dict in `import_service.py` is in-process memory — won't survive restart
13. Use `.venv/bin/pytest` to run tests, not bare `pytest`
