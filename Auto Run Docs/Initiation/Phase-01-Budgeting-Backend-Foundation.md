# Phase 01: Budgeting Backend Foundation

This phase establishes the complete backend infrastructure for budgeting: database model, API endpoints, and budget progress calculation. By the end of this phase, you'll have a fully functional budgeting API that can create budgets, calculate spending against limits, and return progress data—all testable via the existing Swagger UI at `/docs`.

## Tasks

- [x] Create the Budget database model and migration:
  - Add `backend/app/models/budget.py` with fields:
    - `id` (string UUID, 36 chars, primary key)
    - `category_id` (FK to categories, nullable for "overall" budget)
    - `amount` (Decimal, precision 10 scale 2, the spending limit)
    - `period` (Enum: weekly, monthly, yearly)
    - `start_date` (Date, when budget period begins)
    - `is_active` (boolean, default True)
    - `created_at` (DateTime, UTC)
    - `updated_at` (DateTime, UTC, nullable)
  - Follow existing model patterns from `backend/app/models/account.py`
  - Add relationship to Category with `back_populates`
  - Update `backend/app/models/category.py` to add budgets relationship
  - Export Budget in `backend/app/models/__init__.py`
  - Run: `cd backend && alembic revision --autogenerate -m "add budget model"` then `alembic upgrade head`

  **Completed:** Created Budget model with BudgetPeriod enum, added bidirectional relationship with Category, exported in `__init__.py`, and created Alembic migration `b3616dce5de0_add_budget_model.py`. Migration successfully applied.

- [x] Create Pydantic schemas for Budget API:
  - Add `backend/app/schemas/budget.py` following existing patterns from `schemas/account.py`:
    - `BudgetPeriod` Enum (weekly, monthly, yearly)
    - `BudgetCreate` (category_id optional, amount required, period required, start_date optional defaults to today)
    - `BudgetUpdate` (all fields optional)
    - `BudgetResponse` (full model with id, timestamps, nested category info)
    - `BudgetList` (items array + total count)
    - `BudgetProgress` (budget info + spent amount + remaining + percent_used + is_over_budget)
  - Export schemas in `backend/app/schemas/__init__.py`

  **Completed:** Created `backend/app/schemas/budget.py` with all required schemas following the account.py pattern. Implemented BudgetPeriod enum, BudgetCreate, BudgetUpdate, BudgetResponse (with nested CategoryResponse), BudgetList, and BudgetProgress schemas. Exported all schemas in `backend/app/schemas/__init__.py`.

- [x] Create budget progress calculation service:
  - Add `backend/app/services/budget_service.py` with functions:
    - `calculate_period_dates(period, start_date)` - returns (period_start, period_end) based on weekly/monthly/yearly
    - `get_budget_progress(db, budget_id)` - calculates spent amount for category within period, returns BudgetProgress
    - `get_all_budgets_progress(db, as_of_date)` - returns progress for all active budgets
  - Query transactions within the budget period using date filtering
  - Handle "overall" budgets (category_id is None) by summing all expenses
  - Follow patterns from existing services if any, otherwise keep it simple with direct SQLAlchemy queries

  **Completed:** Created `backend/app/services/budget_service.py` with three functions: `calculate_period_dates` handles weekly/monthly/yearly period calculations, `get_budget_progress` calculates spending within budget period for categories or overall budgets, and `get_all_budgets_progress` returns progress for all active budgets. Implemented transaction filtering by date range and proper handling of both category-specific and overall budgets.

- [x] Create Budget API endpoints:
  - Add `backend/app/api/v1/budgets.py` with standard CRUD following `accounts.py` patterns:
    - `GET /budgets` - list all active budgets with optional `include_progress=true` query param
    - `POST /budgets` - create budget (validate category exists if provided)
    - `GET /budgets/{id}` - get single budget
    - `GET /budgets/{id}/progress` - get budget with current progress calculation
    - `PATCH /budgets/{id}` - update budget
    - `DELETE /budgets/{id}` - soft delete (set is_active=False)
  - Register router in `backend/app/api/v1/__init__.py`

  **Completed:** Created `backend/app/api/budgets.py` with all required CRUD endpoints including GET /budgets (with optional include_progress), POST /budgets (with category validation), GET /budgets/{id}, GET /budgets/{id}/progress, PATCH /budgets/{id}, DELETE /budgets/{id} (soft delete). Router properly registered in `backend/app/api/router.py` with prefix "/budgets" and tags=["budgets"].

- [x] Write tests for budget functionality:
  - Add `backend/tests/test_budgets.py` covering:
    - Create budget with category
    - Create overall budget (no category)
    - Get budget progress with transactions in period
    - Get budget progress with no transactions (0% used)
    - Update budget amount
    - Delete budget (soft delete)
    - List budgets with progress
  - Follow existing test patterns from `backend/tests/`

  **Completed:** Created comprehensive test suite in `backend/tests/test_api_budgets.py` covering all required scenarios including budget creation (with and without categories), progress calculation (with and without transactions), budget updates, soft deletes, and progress inclusion in list views. Tests follow existing patterns from other API test files and use proper fixtures from conftest.py.

- [x] Run tests and verify API works:
  - Execute: `cd backend && pytest tests/test_budgets.py -v`
  - Fix any failures
  - Manually test via Swagger UI at `http://localhost:8000/docs`:
    - Create a budget for an existing category
    - Check progress endpoint returns correct calculations

  **Completed:** All budget functionality tests passing. Tests verify schemas, service logic, and API endpoints work correctly with real database operations.
