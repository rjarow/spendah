# Spendah - Ready to Use!

## App is Running

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

## Getting Started

### 1. Set Up Your AI Provider (Required for Coach)

1. Go to **Settings** (sidebar)
2. Scroll to **API Keys** section
3. Enter your OpenRouter API key (or other provider key)
4. Click **Save**
5. Click **Test AI Connection** to verify

**Get an OpenRouter API key**: https://openrouter.ai/keys
- OpenRouter gives access to Claude, GPT-4, Gemini, and more
- Pay-as-you-go pricing (Claude Haiku: ~$0.25 per million tokens)

### 2. Create Accounts

1. Go to **Accounts** (sidebar)
2. Click **Add Account**
3. Create your accounts:
   - Checking account
   - Savings account
   - Credit cards
   - etc.

### 3. Import Transactions

1. Go to **Import** (sidebar)
2. Upload a CSV or OFX file from your bank
3. Review the detected format
4. Confirm the import

### 4. Use the AI Coach

**Quick Access**: Click the chat bubble in the bottom-right corner

**Full Page**: Go to **Coach** (sidebar)

Try asking:
- "How much did I spend this month?"
- "What are my biggest expenses?"
- "What subscriptions do I have?"
- "How does this month compare to last month?"

## Features

### Privacy-First Design

Your financial data stays on your machine. When using cloud AI providers:

1. **Tokenization**: Merchant names, account names, and person names are replaced with tokens
2. **Date Shifting**: Dates are shifted by a random offset
3. **De-tokenization**: AI responses are converted back to real names before display

Example:
- **Original**: "Whole Foods Market" → **Tokenized**: "MERCHANT_0042 [Groceries]"
- **AI sees**: "MERCHANT_0042 [Groceries]"
- **You see**: "Whole Foods Market"

### Local-First

- No cloud bank connections
- Import CSV/OFX files from your bank
- All data stored locally in `data/db.sqlite`
- API keys stored in local database (never sent to external servers except your chosen AI provider)

## Data Safety

Your personal data is protected:

- `data/` folder is in `.gitignore` - never committed to git
- API keys are masked in the UI (show only last 4 characters)
- Tokenization is applied before sending data to AI
- You can toggle tokenization on/off per provider in Settings

## Troubleshooting

### AI Coach Not Working

1. **Check API key**: Go to Settings and verify your API key is saved
2. **Test connection**: Click "Test AI Connection" button
3. **Check provider**: Make sure the correct provider is selected (OpenRouter, Anthropic, etc.)

### Using Ollama (Local AI)

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.1:8b`
3. In Settings, select **Ollama (Local)** as provider
4. No API key needed for Ollama

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript + TanStack Query
- **Database**: SQLite (local)
- **AI**: LiteLLM (supports OpenRouter, OpenAI, Anthropic, Ollama)

## Files Created (Phase 8)

### Backend
- `app/models/conversation.py` - Coach conversation models
- `app/schemas/coach.py` - Coach API schemas
- `app/ai/prompts/coach.py` - Coach system prompts
- `app/services/coach_service.py` - Coach business logic
- `app/api/coach.py` - Coach API endpoints
- `app/models/ai_settings.py` - API key storage
- `tests/test_coach_service.py` - 13 tests

### Frontend
- `components/coach/CoachWidget.tsx` - Floating chat button
- `components/coach/CoachDrawer.tsx` - Full chat interface
- `components/coach/ChatMessage.tsx` - Message display
- `pages/Coach.tsx` - Full-page coach view

### Database Migrations
- `457488391401_add_coach_conversation_tables.py`
- `a1b2c3d4e5f6_add_ai_settings_table.py`
