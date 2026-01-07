# Spendah - Phase 1 Kickoff

## Context

Read the full spec in `spendah-spec.md`. This is a local-first personal finance tracker with AI-powered categorization. Understand the complete architecture, all data models, and the full roadmap before writing any code.

## Your Task: Phase 1 - Foundation

Implement ONLY Phase 1. Do not implement AI features, import parsing, or frontend components beyond the shell.

### Deliverables

**1. Project Structure**
- Create the full directory structure as specified in the spec
- Both `/backend` and `/frontend` directories
- All subdirectories for models, schemas, api, services, etc.
- Empty `__init__.py` files where needed

**2. Backend Setup**
- FastAPI application with proper project structure
- Pydantic settings for configuration (`config.py`)
- SQLAlchemy database setup with async support
- All database models including:
  - `transactions`
  - `accounts`
  - `categories`
  - `recurring_groups`
  - `learned_formats`
  - `alerts` (include from the start)
  - `alert_settings` (include from the start)
  - `import_logs`
  - `user_corrections`
- Alembic setup with initial migration
- Basic CRUD API endpoints for:
  - Accounts (list, create, update, delete)
  - Categories (list with tree structure, create, update, delete)
- Seed script for default categories (see spec for list)
- Health check endpoint

**3. Frontend Setup**
- React + TypeScript + Vite
- Tailwind CSS configured
- shadcn/ui installed and configured
- Basic routing (react-router-dom)
- Layout component with sidebar navigation
- Placeholder pages for: Dashboard, Transactions, Recurring, Accounts, Import, Insights, Settings
- API client setup (axios or fetch wrapper)
- TanStack Query configured

**4. Infrastructure**
- `docker-compose.yml` with api and frontend services
- `Dockerfile` (multi-stage build)
- `.env.example` with all config variables including `APP_NAME=Spendah`
- Volume mounts for SQLite and imports directory
- `.gitignore` for data/, node_modules/, __pycache__/, .env, etc.

**5. Documentation**
- `CLAUDE.md` as specified in the spec
- `README.md` with setup instructions

### Important Notes

1. **APP_NAME**: Use a config constant for the app name, don't hardcode "Spendah" in UI components. Pull from config/env.

2. **Database Models**: Include ALL models from the spec, even for features we're not building yet (alerts, learned_formats, etc.). This avoids migration headaches later.

3. **Don't implement yet**:
   - File parsing/import logic
   - AI/LLM integration
   - Transaction endpoints (beyond the model)
   - Dashboard data aggregation
   - Any alert detection logic

4. **API Versioning**: All endpoints under `/api/v1/`

5. **Type Safety**: 
   - Backend: Type hints everywhere, Pydantic for all schemas
   - Frontend: Strict TypeScript, no `any` types

### Verification

When complete, I should be able to:

```bash
# Start everything
docker-compose up

# See the frontend at http://localhost:5173
# - Sidebar navigation works
# - Pages render (empty placeholders fine)

# Hit the API at http://localhost:8000
# - GET /api/v1/health returns ok
# - GET /api/v1/categories returns seeded categories
# - POST /api/v1/accounts creates an account
# - GET /api/v1/accounts lists accounts

# Database exists at ./data/db.sqlite with all tables
```

### Start

Begin by creating the project structure, then work through backend → database → migrations → seed → API → frontend → Docker → docs.

Let me know when Phase 1 is complete and passing the verification checks.
