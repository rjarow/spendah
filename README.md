# Spendah

> Local-first personal finance tracker with AI-powered categorization

Spendah is a self-hosted personal finance application that prioritizes privacy and local data ownership. Import CSV/OFX/QFX files from your bank, and let AI handle categorization, recurring payment detection, and spending insights.

## Features

### Phase 1 (Current)
- ✅ Full database schema with all models
- ✅ Account management API
- ✅ Category management with hierarchical structure
- ✅ Seeded default categories
- ✅ React frontend with routing and layout
- ✅ Docker Compose setup

### Coming Soon
- 📋 Phase 2: File import pipeline (CSV/OFX/QFX)
- 🤖 Phase 3: AI-powered format detection and categorization
- 📊 Phase 4: Dashboard, transaction list, and filtering
- 🔁 Phase 5: Recurring payment detection and alerts
- 📈 Phase 6: Subscription intelligence and insights

## Quick Start

### With Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd spendah

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up

# Access the application
# Frontend: http://localhost:5173
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

The first run will:
1. Create the database schema
2. Run migrations
3. Seed default categories
4. Start the API and frontend

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p ../data/imports/{inbox,processed,failed}

# Run migrations
alembic upgrade head

# Seed default categories
python -m app.seed

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Project Structure

```
spendah/
├── backend/
│   ├── app/
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── api/           # API route handlers
│   │   ├── services/      # Business logic (Phase 2+)
│   │   ├── parsers/       # File parsers (Phase 2+)
│   │   ├── ai/            # LLM integration (Phase 3+)
│   │   ├── config.py      # App configuration
│   │   ├── database.py    # Database setup
│   │   ├── main.py        # FastAPI app
│   │   └── seed.py        # Category seeding script
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # API client & utilities
│   │   ├── types/         # TypeScript types
│   │   └── App.tsx
│   └── package.json
├── data/                  # SQLite DB and imports (gitignored)
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database access
- **Alembic** - Database migrations
- **SQLite** - Local database
- **Pydantic** - Data validation
- **LiteLLM** - Multi-provider LLM abstraction (Phase 3+)

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library
- **TanStack Query** - Server state management
- **React Router** - Routing

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
# App name (change if rebranding)
APP_NAME=Spendah

# AI provider (for Phase 3+)
AI_PROVIDER=ollama
AI_MODEL=llama3.1:8b
AI_BASE_URL=http://localhost:11434

# For cloud LLMs (optional)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

## API Documentation

Once the backend is running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **OpenAPI spec**: http://localhost:8000/openapi.json

### Available Endpoints (Phase 1)

#### Health
- `GET /api/v1/health` - Health check

#### Accounts
- `GET /api/v1/accounts` - List accounts
- `POST /api/v1/accounts` - Create account
- `GET /api/v1/accounts/{id}` - Get account
- `PATCH /api/v1/accounts/{id}` - Update account
- `DELETE /api/v1/accounts/{id}` - Delete account

#### Categories
- `GET /api/v1/categories` - List categories (tree structure)
- `POST /api/v1/categories` - Create category
- `GET /api/v1/categories/{id}` - Get category
- `PATCH /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Delete category

## Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Database Migrations

```bash
cd backend

# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Resetting the Database

```bash
# Stop Docker containers
docker-compose down

# Remove data directory
rm -rf data/

# Start fresh
docker-compose up
```

## Default Categories

The seed script creates the following categories:
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

## Roadmap

See `spendah-spec.md` for the complete technical specification.

### Phase 1: Foundation ✅
- Project structure
- Database models and migrations
- Basic CRUD APIs
- Frontend shell

### Phase 2: Import Pipeline (Next)
- File upload
- CSV/OFX/QFX parsing
- Deduplication
- Import UI

### Phase 3: AI Integration
- Format detection
- Merchant cleaning
- Auto-categorization
- User corrections

### Phase 4: Core Features
- Transaction list with filters
- Dashboard with charts
- Inline editing
- Bulk operations

### Phase 5: Recurring & Alerts
- Recurring payment detection
- Large purchase alerts
- Price increase detection
- Unusual merchant warnings

### Phase 6: Subscription Intelligence
- Annual charge predictions
- Subscription health reviews
- Spending insights

## Privacy & Security

- **No bank connections**: Manual CSV/OFX imports only
- **Local-first**: All data stored in local SQLite database
- **No telemetry**: Your data never leaves your machine
- **Self-hosted**: Run on your own hardware
- **Optional AI**: Use local models (Ollama) or cloud providers (your choice)

## License

See LICENSE file for details.

## Contributing

This is a personal finance tool in active development. Contributions welcome!

## Support

For issues and questions, see CLAUDE.md for development documentation.
