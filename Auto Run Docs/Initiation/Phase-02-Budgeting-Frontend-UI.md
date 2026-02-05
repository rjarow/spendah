# Phase 02: Budgeting Frontend UI

This phase builds the frontend interface for budgeting: a dedicated Budgets page for managing budgets, progress visualization components, and dashboard integration. Users will be able to create budgets, see visual progress bars, and get warnings when approaching or exceeding limits.

## Tasks

- [x] Add Budget types and API client methods:
  - Update `frontend/src/types/index.ts` with Budget interfaces:
    - `BudgetPeriod` type ('weekly' | 'monthly' | 'yearly')
    - `Budget` interface matching BudgetResponse schema
    - `BudgetProgress` interface with spent, remaining, percent_used, is_over_budget
    - `BudgetCreate` and `BudgetUpdate` interfaces
  - Add to `frontend/src/lib/api.ts`:
    - `getBudgets(includeProgress?: boolean)`
    - `createBudget(data: BudgetCreate)`
    - `updateBudget(id: string, data: BudgetUpdate)`
    - `deleteBudget(id: string)`
    - `getBudgetProgress(id: string)`
  - Follow existing patterns from accounts/categories API methods

- [x] Create BudgetProgressBar component:
  - Add `frontend/src/components/BudgetProgressBar.tsx`:
    - Accepts: budget name, spent amount, limit amount, percent used
    - Visual progress bar with Tailwind (green < 75%, yellow 75-90%, red > 90%)
    - Shows "$X / $Y spent" text with remaining amount
    - "Over budget by $Z" warning when exceeded
    - Compact variant for dashboard widget use
  - Follow existing component patterns from `frontend/src/components/`

- [x] Create Budgets management page:
  - Add `frontend/src/pages/Budgets.tsx`:
    - List all budgets with progress bars
    - "Add Budget" button opening a dialog/form
    - Budget form with:
      - Category dropdown (optional, "Overall Budget" if none selected)
      - Amount input (currency formatted)
      - Period selector (Weekly/Monthly/Yearly radio or select)
      - Start date picker (defaults to first of current period)
    - Edit/Delete actions per budget row
    - Empty state when no budgets exist
  - Use TanStack Query patterns from Dashboard.tsx
  - Use shadcn/ui Dialog, Button, Input, Select components

- [x] Add Budgets page to navigation:
  - Update `frontend/src/components/Sidebar.tsx`:
    - Add "Budgets" link with appropriate icon (e.g., Target, PiggyBank, or Wallet from lucide-react)
    - Place after existing navigation items in logical order
  - Update `frontend/src/App.tsx` router:
    - Add route for `/budgets` pointing to Budgets page
  - Import and register the new page component

- [x] Create Budget Summary dashboard widget:
  - Add `frontend/src/components/BudgetSummaryWidget.tsx`:
    - Shows top 3-5 budgets with most spending as compact progress bars
    - "View All" link to /budgets page
    - Highlights any over-budget items with warning styling
    - Graceful empty state: "No budgets set up yet" with link to create one
  - Integrate into `frontend/src/pages/Dashboard.tsx`:
    - Add widget to dashboard grid layout
    - Query budget progress data alongside existing dashboard queries

- [x] Test the complete budgeting flow:
  - Run the app: `docker-compose up -d --build` (or `cd frontend && npm run dev` if backend running)
  - Create a budget for an existing category with transactions
  - Verify progress bar shows correct percentage
  - Create an "overall" budget and verify it sums all expenses
  - Edit a budget amount and confirm progress updates
  - Delete a budget and confirm it's removed from list
  - Check dashboard widget displays budgets correctly
