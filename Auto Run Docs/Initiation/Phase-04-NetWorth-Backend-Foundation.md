# Phase 04: Net Worth Backend Foundation

This phase adds balance tracking to accounts and creates the net worth calculation infrastructure. The existing Account model will be extended to support current balances, balance history, and proper categorization into assets vs liabilities for net worth computation.

## Tasks

- [x] Extend Account model for net worth tracking:
  - Update `backend/app/models/account.py`:
    - Add `current_balance` (Decimal, precision 12 scale 2, default 0)
    - Add `balance_updated_at` (DateTime, nullable, when balance was last set)
    - Add `is_asset` (boolean, computed from account_type: True for bank/debit/cash, False for credit)
    - Alternatively, add `balance_type` Enum (asset, liability) for explicit control
  - Run migration: `cd backend && alembic revision --autogenerate -m "add balance fields to account"` then `alembic upgrade head`
  - Update `backend/app/schemas/account.py`:
    - Add `current_balance` and `balance_updated_at` to response schema
    - Add `current_balance` to create/update schemas (optional on create, updatable)

- [x] Create BalanceHistory model for net worth over time:
  - Add `backend/app/models/balance_history.py`:
    - `id` (string UUID, primary key)
    - `account_id` (FK to accounts)
    - `balance` (Decimal, the balance at that point)
    - `recorded_at` (Date, when this snapshot was taken)
    - `created_at` (DateTime)
  - Purpose: Track balance snapshots for historical net worth charts
  - Add relationship to Account with `back_populates`
  - Export in `backend/app/models/__init__.py`
  - Run migration

- [x] Create net worth calculation service:
  - Add `backend/app/services/networth_service.py` with functions:
    - `get_current_networth(db)` - sums all account balances (assets positive, liabilities negative)
    - `get_networth_breakdown(db)` - returns { total_assets, total_liabilities, net_worth, accounts: [...] }
    - `record_balance_snapshot(db, account_id, balance, date)` - saves to BalanceHistory
    - `get_networth_history(db, start_date, end_date)` - returns net worth over time from snapshots
    - `auto_snapshot_all_balances(db)` - records current balances for all accounts (for periodic snapshots)
  - Handle account types:
    - Assets (positive): bank, debit, cash, savings, investment
    - Liabilities (negative): credit
    - Use `account_type` to determine, or new `balance_type` field

- [x] Create Net Worth API endpoints:
  - Add `backend/app/api/v1/networth.py`:
    - `GET /networth` - current net worth summary (total_assets, total_liabilities, net_worth)
    - `GET /networth/breakdown` - detailed breakdown by account with individual balances
    - `GET /networth/history?start_date=&end_date=` - historical net worth data points for charting
    - `POST /networth/snapshot` - manually trigger balance snapshot for all accounts
  - Register router in `backend/app/api/v1/__init__.py`

- [x] Update Account API for balance management:
  - Modify `backend/app/api/v1/accounts.py`:
    - `PATCH /accounts/{id}` should accept `current_balance` updates
    - When balance is updated, automatically set `balance_updated_at` to now
    - Optionally auto-create a balance history record on update
  - Add dedicated endpoint: `POST /accounts/{id}/balance` for explicit balance updates with optional date

- [x] Write tests for net worth functionality:
  - Add `backend/tests/test_networth.py`:
    - Create accounts with different types and balances
    - Test net worth calculation (assets - liabilities)
    - Test balance history recording
    - Test historical net worth query
    - Test account balance updates
  - Run: `cd backend && pytest tests/test_networth.py -v`

- [x] Seed some account balance data for development:
  - Update `backend/app/seed.py` or create setup script:
    - Set initial balances on existing test accounts
    - Create a few balance history records for chart testing
  - This helps frontend development in next phase
