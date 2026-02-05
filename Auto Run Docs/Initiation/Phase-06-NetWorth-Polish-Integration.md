# Phase 06: Net Worth Polish and Integration

This phase completes the net worth feature with automatic balance inference from transactions, expanded account types, and integration between spending insights and net worth tracking for a complete financial picture.

## Tasks

- [ ] Add automatic balance calculation from transactions:
  - Create `backend/app/services/balance_inference.py`:
    - `calculate_balance_from_transactions(db, account_id)` - sums all transactions for an account
    - This gives a "calculated balance" that can supplement manual balance entry
    - For credit accounts: sum of transactions = amount owed
    - For bank/debit accounts: need a starting balance + transactions
  - Update Net Worth API:
    - Add `calculated_balance` field to breakdown response
    - Show both manual `current_balance` and `calculated_balance` when different
    - Flag accounts where manual balance is stale vs transaction activity

- [ ] Expand account types for better categorization:
  - Update `backend/app/models/account.py`:
    - Expand `AccountType` enum: checking, savings, credit_card, investment, loan, mortgage, cash, other
    - Or add `account_subtype` field for more granular classification
  - Update `backend/app/schemas/account.py` with new types
  - Run migration if schema changed
  - Update frontend account creation/edit to use new types
  - Update net worth service to categorize correctly:
    - Assets: checking, savings, investment, cash
    - Liabilities: credit_card, loan, mortgage

- [ ] Create unified financial dashboard view:
  - Update `frontend/src/pages/Dashboard.tsx`:
    - Reorganize layout to show complete financial picture:
      - Net Worth widget (top prominence)
      - Budget status widget (how are you tracking?)
      - Monthly spending summary (existing)
      - Recent transactions (existing)
      - Upcoming renewals (existing)
    - Ensure widgets are responsive and work on mobile
  - Consider adding a "Financial Health Score" concept:
    - Simple calculation: are budgets on track? Is net worth growing? Are subscriptions under control?
    - Display as a simple indicator or score

- [ ] Add balance import from transaction files:
  - Update import flow in `backend/app/services/` (wherever OFX import lives):
    - OFX files often contain balance information - extract and save
    - On import, offer to update account balance from file
  - Update import UI to show extracted balance:
    - "This file shows a balance of $X. Update account balance?"
    - Checkbox to apply balance update during import

- [ ] Implement periodic balance snapshots:
  - Add background task or cron endpoint:
    - `POST /networth/auto-snapshot` - records all current balances to history
    - Should be called periodically (daily or weekly) to build history
  - Add guidance in settings or docs for setting up periodic snapshots
  - Alternatively, auto-snapshot on certain events:
    - When user views net worth page (once per day max)
    - When import completes
    - When balance is manually updated

- [ ] Write integration tests for financial overview:
  - Add `backend/tests/test_financial_overview.py`:
    - Create accounts with balances
    - Create budgets with transactions
    - Verify net worth calculation includes all account types
    - Verify budget progress reflects transaction categorization
    - Test the interplay between features
  - Run: `cd backend && pytest tests/test_financial_overview.py -v`

- [ ] Final end-to-end testing:
  - Complete user flow test:
    1. Import transactions from a file
    2. Verify transactions are categorized
    3. Set up budgets for key categories
    4. Set account balances (or import them)
    5. View dashboard - see complete financial picture
    6. Navigate to Budgets page - see progress
    7. Navigate to Net Worth page - see breakdown and history
    8. Check alerts for any budget warnings
  - Fix any issues discovered during testing
  - Verify Docker deployment works: `docker-compose down && docker-compose up -d --build`
