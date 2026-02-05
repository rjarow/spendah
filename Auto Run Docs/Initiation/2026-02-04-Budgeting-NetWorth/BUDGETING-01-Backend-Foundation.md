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

- [x] Create budget progress calculation service:
  - Add `backend/app/services/budget_service.py` with functions:
    - `calculate_period_dates(period, start_date)` - returns (period_start, period_end) based on weekly/monthly/yearly
    - `get_budget_progress(db, budget_id)` - calculates spent amount for category within period, returns BudgetProgress
    - `get_all_budgets_progress(db, as_of_date)` - returns progress for all active budgets
  - Query transactions within the budget period using date filtering
  - Handle "overall" budgets (category_id is None) by summing all expenses
  - Follow patterns from existing services if any, otherwise keep it simple with direct SQLAlchemy queries

- [x] Create Budget API endpoints:
  - Add `backend/app/api/v1/budgets.py` with standard CRUD following `accounts.py` patterns:
    - `GET /budgets` - list all active budgets with optional `include_progress=true` query param
    - `POST /budgets` - create budget (validate category exists if provided)
    - `GET /budgets/{id}` - get single budget
    - `GET /budgets/{id}/progress` - get budget with current progress calculation
    - `PATCH /budgets/{id}` - update budget
    - `DELETE /budgets/{id}` - soft delete (set is_active=False)
  - Register router in `backend/app/api/v1/__init__.py`

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

- [x] Run tests and verify API works:
  - Execute: `cd backend && pytest tests/test_budgets.py -v`
  - Fix any failures
  - Manually test via Swagger UI at `http://localhost:8000/docs`:
    - Create a budget for an existing category
    - Check progress endpoint returns correct calculations
