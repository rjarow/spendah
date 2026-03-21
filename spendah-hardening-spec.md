# Spendah Hardening Pass Spec

## Goal

Stabilize the existing feature set before adding new features (Coach, Rocket Money import). Fix performance bottlenecks, data correctness issues, and frontend/backend mismatches so the app works reliably with real-world data.

## Non-Goals

- No new features
- No UI redesign
- No schema changes (unless required for correctness)
- No Phase 8 (Coach) work

---

## Phase H1: Data Correctness

**Priority: Critical — broken features that silently lose data or don't work.**

### H1.1: Verify alert metadata is persisting

The `metadata=` → `alert_metadata=` bug was just fixed, but any alerts created before the fix have `NULL` metadata. Verify alert display still works when metadata is missing (graceful fallback, no crashes).

**Files:** `frontend/src/pages/Insights.tsx`, `frontend/src/components/alerts/AlertBell.tsx`

### H1.2: Frontend/backend type audit

The `AccountType` enum on the backend (`checking`, `savings`, `credit_card`, `investment`, `loan`, `mortgage`, `cash`, `other`) doesn't match what several frontend components expect. The NetWorth fix was applied but there may be more mismatches.

**Audit checklist:**
- [ ] `Accounts.tsx` — verify `account.type` field name matches API response (is it `type` or `account_type`?)
- [ ] `Accounts.tsx` — verify `current_balance` and `balance_updated_at` exist on the Account type used in list view (the TS type `Account` in `types/index.ts` is missing these fields)
- [ ] `Insights.tsx` — the `updateAlert` mutation signature doesn't match usage (passes object, expects string)
- [ ] `Import.tsx` — verify column mapping flow works end-to-end with a real CSV
- [ ] `Recurring.tsx` — verify the detect → apply flow works (apply re-runs detection, which is wasteful but should be functionally correct)
- [ ] All pages — verify no runtime errors with empty data (no accounts, no transactions, no budgets)

### H1.3: Fix Account type definition

The `Account` interface in `types/index.ts` is missing `current_balance` and `balance_updated_at` fields that the backend returns and the frontend uses. Add them.

**Files:** `frontend/src/types/index.ts`

### H1.4: Fix Insights page alert mutation

`Insights.tsx` passes `{ id, is_read }` to `updateAlert` but the mutation expects a single string argument. Fix the mutation signature or the call site.

**Files:** `frontend/src/pages/Insights.tsx`

---

## Phase H2: Import Performance

**Priority: High — the import pipeline is the core workflow and it's O(n) API calls per transaction.**

### H2.1: Batch deduplication check

Replace per-transaction `is_duplicate(db, hash)` calls with a single `WHERE hash IN (...)` query before the import loop.

```python
# Before the loop:
existing_hashes = set(
    row[0] for row in db.query(Transaction.hash)
    .filter(Transaction.hash.in_(all_hashes))
    .all()
)

# In the loop:
if txn_hash in existing_hashes:
    skipped += 1
    continue
```

**Files:** `backend/app/services/import_service.py`, `backend/app/services/deduplication_service.py`

### H2.2: Pre-fetch categories and corrections once per import

Move `db.query(Category).all()` and `db.query(UserCorrection)...limit(20).all()` out of the per-transaction `categorize_transaction()` call. Fetch once, pass as arguments.

**Files:** `backend/app/services/ai_service.py`

### H2.3: Batch AI calls

Currently each transaction gets two sequential `await` calls (clean merchant + categorize). Options:
- **Quick win:** Use `asyncio.gather` to parallelize clean + categorize per transaction
- **Better:** Batch multiple transactions into a single AI call (the prompt already supports this pattern — send a list of descriptions, get back a list of categories)
- **Best:** Deduplicate merchants first (many transactions share the same merchant), then only call AI once per unique merchant

**Files:** `backend/app/services/ai_service.py`, `backend/app/services/import_service.py`

### H2.4: Pre-fetch alert settings once per import

`analyze_transaction_for_alerts` calls `get_or_create_settings(db)` for every transaction. Fetch once before the loop, pass as argument.

**Files:** `backend/app/services/alerts_service.py`

### H2.5: Consolidate `process_import` and `process_import_with_ai`

These share ~80% identical code. Merge into a single function with a `use_ai: bool` parameter. The AI-specific logic (merchant cleaning, categorization) can be conditionally applied inside the loop.

**Files:** `backend/app/services/import_service.py`

---

## Phase H3: Query Performance

**Priority: Medium — won't matter with small datasets but will degrade as data grows.**

### H3.1: Dashboard summary — use SQL aggregation

Replace loading all transactions into Python for summing with SQL `SUM`/`GROUP BY`:

```python
# Instead of: [t for t in transactions if t.amount < 0]
# Use:
db.query(
    Transaction.category_id,
    func.sum(Transaction.amount)
).filter(...).group_by(Transaction.category_id).all()
```

**Files:** `backend/app/api/dashboard.py`

### H3.2: Dashboard trends — single query with GROUP BY month

Replace N separate per-month queries with a single query over the full range, grouped by month.

**Files:** `backend/app/api/dashboard.py`

### H3.3: Budget progress — use SQL SUM

Replace loading all transaction objects just to sum amounts with `SELECT SUM(ABS(amount))`.

**Files:** `backend/app/services/budget_service.py`

### H3.4: Recurring groups — batch transaction count

Replace per-group `get_group_transaction_count` with a single grouped COUNT query.

**Files:** `backend/app/api/recurring.py`, `backend/app/services/recurring_service.py`

### H3.5: Net worth — eliminate double balance computation

`get_networth_breakdown` calls `get_accounts_with_stale_balances` (which iterates all accounts calling `get_balance_difference`) and then calls `get_balance_difference` again per account in its own loop. Compute once.

**Files:** `backend/app/services/networth_service.py`, `backend/app/services/balance_inference.py`

### H3.6: Bulk categorize — single UPDATE

Replace per-transaction query in `bulk_categorize` with `UPDATE ... WHERE id IN (...)`.

**Files:** `backend/app/api/transactions.py`

---

## Phase H4: Reliability

**Priority: Medium — things that will bite in production.**

### H4.1: Replace PENDING_IMPORTS with database-backed storage

The module-level `Dict[str, Dict]` has multiple problems:
- Memory leak (uploads never confirmed are never cleaned up)
- Lost on process restart
- Doesn't work with multiple workers

Replace with a `pending_imports` table or store in `import_logs` with a `pending` status. Include a created_at timestamp for TTL cleanup.

**Files:** `backend/app/services/import_service.py`, possibly new migration

### H4.2: Replace print() with logging

Replace all `print()` and `print(f"...")` statements in backend services with proper `logging.getLogger(__name__)` calls. Use appropriate levels (debug, info, warning, error).

**Files:** `backend/app/services/ai_service.py`, `backend/app/services/import_service.py`, `backend/app/services/alerts_service.py`

### H4.3: Fix swallowed exceptions

Audit `except Exception: pass` patterns. In each case, at minimum log the error. Key locations:
- `import_service.py` — exception during individual transaction processing silently skipped
- `networth_service.py` — `get_balance_difference` failure silently excluded

**Files:** `backend/app/services/import_service.py`, `backend/app/services/networth_service.py`

### H4.4: Remove duplicate balance update endpoint

`POST /accounts/{id}/balance` exists in both `accounts.py` and `v1/networth.py`. Keep one (the accounts router makes more sense), remove the other, update any frontend calls.

**Files:** `backend/app/api/accounts.py`, `backend/app/api/v1/networth.py`

### H4.5: Remove duplicate net worth endpoint

`GET /networth` and `GET /networth/breakdown` both call `get_networth_breakdown(db)` and return identical data. Remove `/networth` or make it return a lighter summary.

**Files:** `backend/app/api/v1/networth.py`

---

## Phase H5: Dev Environment

**Priority: Medium — enables everything else.**

### H5.1: Fix local venv

The local `.venv` is missing `pip` and `setuptools`, making it impossible to run tests locally. Either:
- Recreate the venv: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Or document that tests must run in Docker

### H5.2: Add a test runner script

Create a simple `scripts/test.sh` that handles venv activation and pytest execution, so testing is a single command.

### H5.3: End-to-end smoke test

Create a script or test that:
1. Seeds the database with categories
2. Creates an account
3. Imports a small CSV (5-10 rows)
4. Verifies transactions were created with correct amounts
5. Checks budget alert flow
6. Verifies dashboard summary returns correct totals

This catches the class of bugs we found (type mismatches, silently dropped data) that unit tests miss.

**Files:** `backend/tests/test_smoke.py`

---

## Phase H6: Frontend Polish

**Priority: Low — cosmetic/UX issues.**

### H6.1: Extract shared components

- `calculateDaysAgo` / `formatLastUpdated` → already extracted to `Accounts.tsx` module level, but should move to `formatters.ts` and be used by `NetWorth.tsx` too
- `flatCategories` computation (used in `Transactions.tsx` and `Budgets.tsx`) → shared utility
- Balance update form (duplicated in `NetWorth.tsx` for assets and liabilities sections) → shared `AccountBalanceRow` component

### H6.2: Consistent API function style

`api.ts` mixes arrow function style (most functions) with `function` declaration style (alert functions). Pick one and standardize.

### H6.3: Remove unused imports

Pre-existing unused imports across several components (`Button` in CreateAccountModal, `formatCurrency` in FinancialHealthScore, `NetWorthWidget` in Dashboard, etc.). Clean these up.

---

## Suggested Execution Order

```
H1 (Correctness)  →  H5 (Dev Env)  →  H2 (Import Perf)  →  H4 (Reliability)  →  H3 (Query Perf)  →  H6 (Polish)
```

H1 first because data correctness bugs are actively breaking things. H5 next because you need working tests to validate the rest. H2 before H3 because import is the most-used hot path. H4 before H3 because reliability issues (PENDING_IMPORTS, swallowed exceptions) are harder to debug in production than slow queries.

---

## Success Criteria

- [ ] All existing tests pass locally (not just in Docker)
- [ ] Smoke test passes with a real CSV import
- [ ] Import of 500 rows completes in < 60 seconds (with AI enabled)
- [ ] Dashboard loads in < 1 second with 10k transactions
- [ ] No `print()` statements in production code
- [ ] No duplicate API endpoints
- [ ] No bare `except:` or `except Exception: pass` without logging
- [ ] Frontend TypeScript compiles with zero errors
- [ ] PENDING_IMPORTS survives process restart
