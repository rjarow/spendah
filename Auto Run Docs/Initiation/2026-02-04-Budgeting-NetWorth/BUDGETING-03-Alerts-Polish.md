# Phase 03: Budget Alerts and Polish

This phase adds intelligent budget alerts (approaching limit, exceeded limit) and polishes the budgeting experience with better UX touches. The existing alert system will be extended to support budget-related notifications.

## Tasks

- [x] Extend alert system for budget alerts:
  - Update `backend/app/models/alert.py`:
    - Add new AlertType enum values: `budget_warning` (approaching limit), `budget_exceeded` (over limit)
    - Add optional `budget_id` FK field to Alert model (nullable, for linking alerts to specific budgets)
  - Run migration: `cd backend && alembic revision --autogenerate -m "add budget alert types"` then `alembic upgrade head`
  - Update `backend/app/schemas/alert.py` to include new alert types

- [x] Create budget alert generation service:
  - Add `backend/app/services/budget_alerts.py` with functions:
    - `check_budget_alerts(db, budget_id)` - checks single budget, creates alerts if needed
    - `check_all_budget_alerts(db)` - iterates all active budgets, generates alerts
    - Alert triggers:
      - `budget_warning` when percent_used >= 80% and < 100%
      - `budget_exceeded` when percent_used >= 100%
    - Avoid duplicate alerts: check if similar alert exists within same period before creating
  - Follow patterns from existing alert generation in `backend/app/services/` if present

- [x] Add budget alert settings:
  - Update `backend/app/models/alert_settings.py`:
    - Add `budget_warning_threshold` (integer, default 80, percent at which to warn)
    - Add `budget_alerts_enabled` (boolean, default True)
  - Run migration for new fields
  - Update `backend/app/schemas/alert_settings.py` with new fields
  - Update settings API to expose these thresholds

- [x] Integrate budget alerts into transaction flow:
  - Modify transaction creation/import flow in `backend/app/api/v1/transactions.py` or relevant import service:
    - After transactions are added/updated, trigger `check_all_budget_alerts(db)`
    - This ensures alerts are generated when spending changes
  - Alternatively, add a periodic check endpoint: `POST /budgets/check-alerts` that can be called manually or via cron
    - Added endpoint in `backend/app/api/budgets.py`
    - Calls `check_all_budget_alerts(db)` after successful imports
    - Endpoint returns list of created alerts
    - Also added `check_all_budget_alerts` import to import service

- [x] Enhance frontend alert display for budget alerts:
  - Update `frontend/src/components/AlertBell.tsx` (or wherever alerts are displayed):
    - Handle `budget_warning` and `budget_exceeded` alert types
    - Show appropriate icons and colors (yellow for warning, red for exceeded)
    - Link alert to the specific budget page when clicked
  - Update alert type definitions in `frontend/src/types/index.ts`

- [x] Add budget period navigation to Budgets page:
  - Update `frontend/src/pages/Budgets.tsx`:
    - Add period selector to view current/past budget periods
    - Show historical progress (how did last month compare to budget?)
    - Visual indicator for budgets that were exceeded in past periods
  - Query historical data by passing date parameter to progress endpoint

- [x] Final testing and polish:
  - Test alert generation:
    - Create a small budget, add transactions to exceed 80%, verify warning alert appears
    - Add more transactions to exceed 100%, verify exceeded alert appears
    - Check no duplicate alerts are created for same condition
  - Test settings:
    - Change warning threshold in settings, verify new threshold is used
    - Disable budget alerts, verify no new alerts are created
  - UI polish:
    - Ensure all loading states are smooth
    - Verify error handling shows user-friendly messages
    - Check mobile responsiveness of budget components
