# Phase 05: Net Worth Frontend UI

This phase builds the frontend interface for net worth tracking: a dedicated Net Worth page with aggregate views and trend charts, account balance management UI, and dashboard integration showing overall financial health.

## Tasks

- [ ] Add Net Worth types and API client methods:
  - Update `frontend/src/types/index.ts`:
    - `NetWorthSummary` interface (total_assets, total_liabilities, net_worth)
    - `NetWorthBreakdown` interface (summary + accounts array with balances)
    - `NetWorthHistoryPoint` interface (date, net_worth, total_assets, total_liabilities)
    - Update `Account` interface to include `current_balance` and `balance_updated_at`
  - Add to `frontend/src/lib/api.ts`:
    - `getNetWorth()` - current summary
    - `getNetWorthBreakdown()` - detailed by account
    - `getNetWorthHistory(startDate, endDate)` - for charting
    - `updateAccountBalance(id, balance)` - update account balance
  - Follow existing API patterns

- [ ] Create Net Worth page with breakdown view:
  - Add `frontend/src/pages/NetWorth.tsx`:
    - Hero section: Large net worth number with assets/liabilities below
    - Color coding: Net worth green if positive, red if negative
    - Account breakdown table/cards:
      - Group by type (Assets vs Liabilities)
      - Show each account with name, type, current balance
      - Sum row for each group
    - "Update Balance" action per account (opens modal/inline edit)
    - Last updated timestamp showing when balances were refreshed
  - Use TanStack Query for data fetching
  - Use existing shadcn/ui components for consistent styling

- [ ] Create Net Worth trend chart component:
  - Add `frontend/src/components/NetWorthChart.tsx`:
    - Line chart showing net worth over time (6-12 months)
    - Optional: Show stacked area for assets vs liabilities
    - Period selector (3M, 6M, 1Y, All Time)
    - Hover tooltips showing exact values
    - Handle empty state gracefully (not enough history)
  - Use same charting approach as existing dashboard trends (or add recharts/chart.js if not present)
  - Integrate into Net Worth page below the summary

- [ ] Add Net Worth page to navigation:
  - Update `frontend/src/components/Sidebar.tsx`:
    - Add "Net Worth" link with appropriate icon (e.g., Scale, TrendingUp, or DollarSign from lucide-react)
    - Place in logical order with other navigation items
  - Update `frontend/src/App.tsx` router:
    - Add route for `/net-worth` pointing to NetWorth page

- [ ] Update Accounts page with balance management:
  - Modify `frontend/src/pages/Accounts.tsx`:
    - Display current balance for each account in the list
    - Add "Update Balance" button/action per account
    - Balance update form: input field + "Update" button
    - Show `balance_updated_at` as "Last updated: X days ago"
  - Ensure balance updates trigger cache invalidation for net worth queries

- [ ] Create Net Worth dashboard widget:
  - Add `frontend/src/components/NetWorthWidget.tsx`:
    - Compact display: Net worth amount with trend indicator (↑↓)
    - Mini sparkline or simple +/- change vs last month
    - "View Details" link to /net-worth page
    - Assets and liabilities as small secondary numbers
  - Integrate into `frontend/src/pages/Dashboard.tsx`:
    - Add widget to dashboard grid (prominent position as key financial health indicator)
    - Query net worth data alongside existing dashboard queries

- [ ] Test the complete net worth flow:
  - Run the app with `docker-compose up -d --build`
  - Set balances on multiple accounts (checking, savings, credit card)
  - Verify net worth calculates correctly (assets - liabilities)
  - Update a balance and confirm net worth updates
  - Check Net Worth page shows breakdown correctly
  - Verify dashboard widget displays accurate summary
  - Test historical chart (may need seed data or wait for snapshots)
