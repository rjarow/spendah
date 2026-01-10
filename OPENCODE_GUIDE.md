# OpenCode Development Guide for Spendah

## Team Structure

You are the **Implementation Agent** working on the Spendah project. You have a support channel:

**Architect Team** (Rich + Claude via Claude.ai)
- Has read/write access to the GitHub repo via MCP
- Handles architecture decisions, debugging help, code review
- Creates phase prompts and implementation plans
- Cannot directly access your devbox - communicates through GitHub

**You (OpenCode on devbox)**
- Direct filesystem access to `~/projects/spendah`
- Can run all shell commands: docker, git, sqlite3, pytest, etc.
- Implements features following phase prompts
- Commits work to GitHub

## Git Workflow

**Use feature branches, not main.**

```bash
# Starting new work
git checkout main
git pull origin main
git checkout -b phase7-privacy-tokenization

# Working
git add .
git commit -m "Step 1: Add token map models"

# Push regularly so Architect Team can see progress
git push origin phase7-privacy-tokenization

# When phase is complete and tested
git checkout main
git merge phase7-privacy-tokenization
git push origin main
git branch -d phase7-privacy-tokenization
```

**Branch naming:**
- `phase7-privacy-tokenization`
- `fix/alerts-service-import-error`
- `hotfix/cors-config`

**Commit often with clear messages:**
- `Step 1: Add token map models`
- `Step 3: Add structural redaction for format detection`
- `WIP: Tokenization service - date shifting not working`
- `BLOCKED: Need architect help - see ARCHITECT_HELP.md`

## Asking for Help

When you're stuck, need a design decision, or hit something you can't debug:

### 1. Create `ARCHITECT_HELP.md` in repo root:

```markdown
# Architect Help Needed

**Branch:** phase7-privacy-tokenization
**Step:** Step 6 - Integrate tokenization with AI client
**Blocked:** Yes / Partially / No (just need review)

## Problem

[Clear description of what's wrong]

## What I Tried

1. [First attempt]
2. [Second attempt]

## Relevant Files

- `backend/app/ai/client.py` (lines 45-60)
- `backend/app/services/tokenization_service.py`

## Error Output

```
[paste actual error if applicable]
```

## Specific Question

[What exactly do you need from Architect Team?]
```

### 2. Commit and push:

```bash
git add ARCHITECT_HELP.md
git commit -m "BLOCKED: Need architect help with AI client integration"
git push origin phase7-privacy-tokenization
```

### 3. Rich will notify the Architect Team, who will:
- Read your help request from GitHub
- Review relevant code in the repo
- Respond via `ARCHITECT_RESPONSE.md` committed to your branch (or Rich will paste the response)

### 4. Check for response:

```bash
git pull origin phase7-privacy-tokenization
cat ARCHITECT_RESPONSE.md
```

### 5. After resolving, clean up:

```bash
rm ARCHITECT_HELP.md ARCHITECT_RESPONSE.md
git add -A
git commit -m "Resolved: AI client integration working"
```

## What Architect Team Can See

The Architect Team can read from GitHub:
- All files in the repo
- Commit history and diffs
- Branch contents
- Pull request diffs (if you create PRs)

They **cannot** see:
- Your local uncommitted changes
- Docker logs (unless you paste them into a file and commit)
- Runtime errors (unless you capture and commit them)

**Rule of thumb:** If it's not committed and pushed, the Architect Team can't see it.

## Phase Prompts

Implementation plans live in the repo as `spendah-phase{N}-prompt.md`. These contain:
- Step-by-step instructions
- Files to create/modify
- Code snippets and patterns to follow
- Verification commands
- Progress tracker checkboxes

Work through these sequentially, committing after each step.

## Standard Verification After Each Step

```bash
# Check for Python syntax errors
docker compose exec api python -c "from app.main import app; print('OK')"

# Run tests
docker compose exec api pytest -v --tb=short

# Check logs for runtime errors
docker compose logs api --tail 50
```

## Project Conventions

From previous phases (don't repeat these mistakes):

1. **Account model:** Use `account_type`, not `type` (SQLAlchemy reserved)
2. **Alert model:** Use `Severity`, not `AlertSeverity`
3. **OpenRouter:** Use `OPENROUTER_API_KEY`, not `OPENAI_API_KEY`
4. **SQLAlchemy:** `metadata` is reserved - use `metadata_` for JSON columns
5. **Frontend API URL:** Use dynamic `window.location.hostname`, not hardcoded localhost
6. **After code changes:** Always restart containers:
   ```bash
   docker compose down && docker compose up -d --build
   ```

## Current Project State

- **Repo:** https://github.com/rjarow/spendah
- **Main docs:** `HANDOFF-phase6-complete.md`, `spendah-spec.md`
- **Current phase:** Check for latest `spendah-phase{N}-prompt.md`

---

*This workflow lets you move fast while having a safety net. Don't spin for more than 15-20 minutes on something confusing - commit a help request and context-switch to something else while waiting.*
