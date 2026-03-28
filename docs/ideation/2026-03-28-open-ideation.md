---
date: 2026-03-28
topic: open-ideation
focus: open-ended post-hardening
---

# Ideation: Spendah Post-Hardening Improvements

## Codebase Context

Spendah is a local-first personal finance tracker (FastAPI, React 18, SQLite WAL, LiteLLM). Self-hosted on Proxmox homelab. Phases 1-8 complete (accounts, transactions, import, AI categorization, budgets, recurring detection, alerts, net worth, privacy/tokenization, coach). A hardening pass was completed on 2026-03-27 covering N+1 fixes, rate limiting, CORS, WAL mode, dead code removal, and code quality improvements.

Key pain points identified during review:
- PENDING_IMPORTS is in-process memory (lost on restart)
- No authentication
- Coach page doesn't use TanStack Query
- Several features require manual triggering (recurring detection, budget alerts, snapshots)
- Rules engine exists but isn't the primary categorization path
- Budget creation is a cold-start problem
- Transaction model lacks splits

No formal `docs/solutions/` knowledge base exists. Institutional knowledge lives in CLAUDE.md, AGENTS.md, and claude memory files.

## Ranked Ideas

### 1. Scheduled Task Runner
**Description:** Add a lightweight asyncio scheduler that runs existing service functions on a cron: recurring detection, budget alert checks, net worth snapshots, stale-balance warnings. All the features exist but require manual triggering today.
**Rationale:** Backbone infrastructure that enables proactive behavior across the app. Low effort since it just wires existing functions to a schedule.
**Downsides:** Adds a background process to a request-response app. Need to handle graceful shutdown.
**Confidence:** 85%
**Complexity:** Low-Medium
**Status:** Unexplored

### 2. Persist PENDING_IMPORTS to SQLite
**Description:** Replace the in-memory PENDING_IMPORTS dict with a database-backed staging table. Store parsed preview rows, detected format, and column mapping in SQLite.
**Rationale:** Known bug (CLAUDE.md gotcha #12). A restart between upload and confirm silently loses import state.
**Downsides:** Requires schema migration. Preview data is potentially large (JSON blob).
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 3. Rules Engine as Universal Fast Path
**Description:** Restructure the import pipeline so user-defined rules are checked first (free, instant, deterministic), with AI categorization only for unmatched transactions. Auto-promote corrections to rules after N occurrences.
**Rationale:** Every correction permanently eliminates future AI calls. Most of the code exists — just needs the ordering tightened and auto-promotion wired in.
**Downsides:** Need to verify rule quality doesn't degrade over time.
**Confidence:** 80%
**Complexity:** Low-Medium
**Status:** Unexplored

### 4. Budget Auto-Suggest from Spending History
**Description:** Analyze 3-6 months of spending history and propose budgets per category. "You typically spend $340/mo on groceries. Set a $350 budget?" One-click accept.
**Rationale:** Pure SQL query, no AI needed. Solves the cold-start problem where new users have no idea what limits to set.
**Downsides:** Needs enough history data to be meaningful. Early months may not be representative.
**Confidence:** 85%
**Complexity:** Low
**Status:** Unexplored

### 5. Transaction Splits
**Description:** Allow splitting a single transaction across multiple categories (e.g., $150 Costco = $80 groceries + $70 household). Child rows linked to parent transaction.
**Rationale:** Highest-value data model change. Without splits, big-box retailer transactions systematically distort budget tracking.
**Downsides:** Touches budget calculations, dashboard sums, and reporting. Needs careful handling of dedup hashes.
**Confidence:** 75%
**Complexity:** Medium-High
**Status:** Unexplored

### 6. Lightweight Auth Gate
**Description:** Simple passphrase/API key stored as env var, checked via FastAPI middleware. Frontend prompts once, stores in localStorage.
**Rationale:** Security fix, not a feature. Zero auth on a finance app is a risk even on localhost.
**Downsides:** Need to handle the UX of the login prompt without a full auth system.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 7. Coach TanStack Query Migration + SSE Streaming
**Description:** Migrate Coach.tsx from manual useState/useEffect to TanStack Query (matching every other page), then add SSE streaming so coach responses arrive token-by-token instead of after a full LLM round-trip.
**Rationale:** Consistency fix (Coach is the only page not using TanStack Query) + real UX improvement (eliminates 5-10s loading spinner wait).
**Downsides:** SSE streaming requires FastAPI StreamingResponse and frontend EventSource handling.
**Confidence:** 80%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Folder-Watch Auto-Import | Saves one click for Docker-hosted app; not worth the background process |
| 2 | Confidence-Gated Auto-Confirm | Preview catches mistakes; silently committing errors is worse |
| 3 | Smart Import Memory | Vague; AI format detection already handles re-detection |
| 4 | Auto-Promote Corrections | Already implemented via generate_rules_from_corrections |
| 5 | Expand Correction Feedback | Too vague; names a direction but no actionable design |
| 6 | Offline-First AI Fallback Chain | Over-engineered; LiteLLM already supports provider switching |
| 7 | Coach Context Cache | Premature optimization; SQLite fast, LLM round-trip dominates |
| 8 | Local Embedding Index | Overkill; SQLite FTS5 gives 90% of value at 5% complexity |
| 9 | Proactive Coach Digests | Costs tokens weekly for dubious value |
| 10 | Cash Flow Projection | Requires reliable income detection that doesn't exist |
| 11 | AI Token Cost Dashboard | Tiny costs for single-user tool |
| 12 | Transaction Tags | Redundant with splits + categories |
| 13 | Transaction Relationships | Subsumes splits but 3x complexity |
| 14 | Multi-Currency | Scope creep; banks already convert |
| 15 | Envelope Budgeting | Different philosophy; full rebuild |
| 16 | PWA Shell | UI isn't mobile-responsive; lipstick on a pig |
| 17 | Webhook/REST API | API already exists; this is auth + docs |
| 18 | Data Export | 20-line function, not an idea |
| 19 | Household Multi-User | Requires user_id on every table; different product |
| 20 | Unified Service Layer | Zero user-facing value; unify when you touch them |
| 21 | SQLite Performance Armor | 10k transactions is not a problem |
| 22 | Token Map GC | Grows slowly; non-problem for years |
| 23 | Alert Feedback Loop | Half-implemented; remaining half undefined |

## Session Log
- 2026-03-28: Initial ideation — 48 generated across 6 agents (pain/friction, missing capability, inversion/automation, assumption-breaking, leverage/compounding, edge cases/power users), deduped to 30 unique + 3 cross-cutting combos, 7 survived adversarial filtering. User confirmed survivors, noted #7 (Coach streaming) is needed and #4 (Budget auto-suggest) is a favorite.
