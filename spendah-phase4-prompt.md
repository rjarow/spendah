
# Spendah - Phase 4: Core Features

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `spendah-spec.md` - Full architecture, UI wireframes, and data models
2. `CLAUDE.md` - Project conventions

## Known Gotchas (from Phase 1-3)

1. **After model changes, generate migrations:**
   ```bash
   docker compose exec api alembic revision --autogenerate -m "description"
   docker compose exec api alembic upgrade head
   ```

2. **Never use SQLAlchemy reserved words:** `metadata`, `query`, `registry`, `type`

3. **API keys must be in docker-compose.yml environment section**

4. **Test after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   docker compose logs api --tail 30
   curl http://localhost:8000/api/v1/health
   ```

---

## Context

Phases 1-3 are complete. The app can:
- Import CSV/OFX files with AI format detection
- AI cleans merchant names and categorizes transactions
- Basic CRUD for accounts, categories, transactions
- Settings page for AI provider configuration

## Your Task: Phase 4 - Core Features

Build the main user-facing features: Transaction management UI and Dashboard.

**Focus on:**
- Transaction list with filtering, search, pagination
- Inline editing of categories and merchants
- Bulk operations
- Dashboard with spending overview

---

## Deliverables

### Step 1: Backend - Enhanced Transactions Endpoint

First, ensure the transactions endpoint supports filtering. Update `backend/app/api/transactions.py` to add query parameters:

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.transaction import Transaction
from app.models.user_correction import UserCorrection
from app.schemas.transaction import TransactionResponse, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])

class BulkCategorizeRequest(BaseModel):
    transaction_ids: List[str]
    category_id: str

@router.get("")
def get_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    is_recurring: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Get transactions with filtering, search, and pagination"""
    query = db.query(Transaction)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.raw_description.ilike(search_term),
                Transaction.clean_merchant.ilike(search_term)
            )
        )
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    if is_recurring is not None:
        query = query.filter(Transaction.is_recurring == is_recurring)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Transaction.date.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    transactions = query.all()
    
    return {
        "items": [TransactionResponse.model_validate(t) for t in transactions],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Get a single transaction by ID"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)

@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction and record user corrections for AI learning"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If category changed and was AI-categorized, record correction
    if update.category_id and transaction.ai_categorized and update.category_id != str(transaction.category_id):
        correction = UserCorrection(
            id=str(uuid.uuid4()),
            raw_description=transaction.raw_description,
            clean_merchant=update.clean_merchant or transaction.clean_merchant,
            category_id=update.category_id
        )
        db.add(correction)
    
    # If merchant name changed, record correction
    if update.clean_merchant and update.clean_merchant != transaction.clean_merchant:
        existing = db.query(UserCorrection).filter(
            UserCorrection.raw_description == transaction.raw_description
        ).first()
        if existing:
            existing.clean_merchant = update.clean_merchant
        else:
            correction = UserCorrection(
                id=str(uuid.uuid4()),
                raw_description=transaction.raw_description,
                clean_merchant=update.clean_merchant,
                category_id=update.category_id or str(transaction.category_id) if transaction.category_id else None
            )
            db.add(correction)
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    # Mark as no longer AI-categorized if user changed it
    if update.category_id:
        transaction.ai_categorized = False
    
    db.commit()
    db.refresh(transaction)
    
    return TransactionResponse.model_validate(transaction)

@router.post("/bulk-categorize")
def bulk_categorize(
    request: BulkCategorizeRequest,
    db: Session = Depends(get_db)
):
    """Bulk update category for multiple transactions"""
    updated = 0
    for txn_id in request.transaction_ids:
        transaction = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if transaction:
            transaction.category_id = request.category_id
            transaction.ai_categorized = False
            updated += 1
    
    db.commit()
    return {"updated": updated}
```

### Step 2: Backend - Dashboard Endpoints

Create `backend/app/api/dashboard.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.models.transaction import Transaction
from app.models.category import Category

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary for a month.
    Returns: total_income, total_expenses, net, by_category, vs_last_month
    """
    # Parse month or default to current
    if month:
        year, m = map(int, month.split('-'))
        start_date = date(year, m, 1)
        if m == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, m + 1, 1)
    else:
        today = date.today()
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1)
        else:
            end_date = date(today.year, today.month + 1, 1)
    
    # Query transactions for the month
    transactions = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()
    
    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    net = total_income - total_expenses
    
    # Group by category
    category_totals = {}
    for t in transactions:
        if t.amount < 0:  # Only expenses
            cat_id = str(t.category_id) if t.category_id else 'uncategorized'
            category_totals[cat_id] = category_totals.get(cat_id, Decimal('0')) + abs(t.amount)
    
    # Get category names
    categories = {str(c.id): c.name for c in db.query(Category).all()}
    categories['uncategorized'] = 'Uncategorized'
    
    by_category = [
        {
            "category_id": cat_id,
            "category_name": categories.get(cat_id, 'Unknown'),
            "amount": float(amount),
            "percent": float(amount / total_expenses * 100) if total_expenses > 0 else 0
        }
        for cat_id, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Calculate vs last month
    prev_month = start_date.month - 1 if start_date.month > 1 else 12
    prev_year = start_date.year if start_date.month > 1 else start_date.year - 1
    prev_start = date(prev_year, prev_month, 1)
    prev_end = start_date
    
    prev_transactions = db.query(Transaction).filter(
        Transaction.date >= prev_start,
        Transaction.date < prev_end
    ).all()
    
    prev_income = sum(t.amount for t in prev_transactions if t.amount > 0)
    prev_expenses = abs(sum(t.amount for t in prev_transactions if t.amount < 0))
    
    income_change_pct = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_change_pct = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    
    return {
        "month": start_date.strftime("%Y-%m"),
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net": float(net),
        "by_category": by_category,
        "vs_last_month": {
            "income_change_pct": round(float(income_change_pct), 1),
            "expense_change_pct": round(float(expense_change_pct), 1)
        }
    }

@router.get("/trends")
def get_spending_trends(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """
    Get spending trends over multiple months.
    Returns: [{month, income, expenses, net}, ...]
    """
    today = date.today()
    trends = []
    
    for i in range(months - 1, -1, -1):
        # Calculate month start/end
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        
        start_date = date(y, m, 1)
        if m == 12:
            end_date = date(y + 1, 1, 1)
        else:
            end_date = date(y, m + 1, 1)
        
        transactions = db.query(Transaction).filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()
        
        income = sum(t.amount for t in transactions if t.amount > 0)
        expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
        
        trends.append({
            "month": start_date.strftime("%Y-%m"),
            "income": float(income),
            "expenses": float(expenses),
            "net": float(income - expenses)
        })
    
    return trends

@router.get("/recent-transactions")
def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get most recent transactions for dashboard widget"""
    transactions = db.query(Transaction).order_by(
        Transaction.date.desc()
    ).limit(limit).all()
    
    # Get category names
    categories = {str(c.id): c.name for c in db.query(Category).all()}
    
    return [
        {
            "id": str(t.id),
            "date": t.date.isoformat(),
            "merchant": t.clean_merchant or t.raw_description,
            "category": categories.get(str(t.category_id), "Uncategorized") if t.category_id else "Uncategorized",
            "amount": float(t.amount)
        }
        for t in transactions
    ]
```

### Step 3: Backend - Update Router

Update `backend/app/api/router.py` to include all routers:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router
from app.api.imports import router as imports_router
from app.api.transactions import router as transactions_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(imports_router)
api_router.include_router(transactions_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)

@api_router.get("/health")
def health_check():
    from app.config import settings
    return {"status": "ok", "app_name": settings.APP_NAME}
```

### Step 4: Frontend - Update API Client

Update `frontend/src/lib/api.ts` to add all necessary functions:

```typescript
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Accounts
export async function getAccounts() {
  const response = await api.get('/accounts')
  return response.data
}

export async function createAccount(data: { name: string; account_type: string }) {
  const response = await api.post('/accounts', data)
  return response.data
}

export async function updateAccount(id: string, data: { name?: string; account_type?: string; is_active?: boolean }) {
  const response = await api.patch(`/accounts/${id}`, data)
  return response.data
}

export async function deleteAccount(id: string) {
  const response = await api.delete(`/accounts/${id}`)
  return response.data
}

// Categories
export async function getCategories() {
  const response = await api.get('/categories')
  return response.data
}

export async function createCategory(data: { name: string; parent_id?: string; color?: string; icon?: string }) {
  const response = await api.post('/categories', data)
  return response.data
}

// Transactions
export interface GetTransactionsParams {
  page?: number
  per_page?: number
  search?: string
  account_id?: string
  category_id?: string
  start_date?: string
  end_date?: string
  is_recurring?: boolean
}

export async function getTransactions(params: GetTransactionsParams = {}) {
  const response = await api.get('/transactions', { params })
  return response.data
}

export async function getTransaction(id: string) {
  const response = await api.get(`/transactions/${id}`)
  return response.data
}

export async function updateTransaction(id: string, data: {
  category_id?: string | null
  clean_merchant?: string
  is_recurring?: boolean
  notes?: string
}) {
  const response = await api.patch(`/transactions/${id}`, data)
  return response.data
}

export async function bulkCategorize(transactionIds: string[], categoryId: string) {
  const response = await api.post('/transactions/bulk-categorize', {
    transaction_ids: transactionIds,
    category_id: categoryId,
  })
  return response.data
}

// Dashboard
export async function getDashboardSummary(month?: string) {
  const params = month ? { month } : {}
  const response = await api.get('/dashboard/summary', { params })
  return response.data
}

export async function getDashboardTrends(months: number = 6) {
  const response = await api.get('/dashboard/trends', { params: { months } })
  return response.data
}

export async function getRecentTransactions(limit: number = 10) {
  const response = await api.get('/dashboard/recent-transactions', { params: { limit } })
  return response.data
}

// Imports
export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/imports/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function confirmImport(importId: string, data: {
  account_id: string
  column_mapping: {
    date_col: number
    amount_col: number
    description_col: number
    debit_col?: number
    credit_col?: number
  }
  date_format: string
  save_format?: boolean
  format_name?: string
}) {
  const response = await api.post(`/imports/${importId}/confirm`, data)
  return response.data
}

export async function getImportStatus(importId: string) {
  const response = await api.get(`/imports/${importId}/status`)
  return response.data
}

export async function getImportHistory(limit: number = 20) {
  const response = await api.get('/imports/history', { params: { limit } })
  return response.data
}

// Settings
export async function getSettings() {
  const response = await api.get('/settings')
  return response.data
}

export async function updateAISettings(data: {
  provider?: string
  model?: string
  auto_categorize?: boolean
  clean_merchants?: boolean
  detect_format?: boolean
}) {
  const response = await api.patch('/settings/ai', data)
  return response.data
}

export async function testAIConnection() {
  const response = await api.post('/settings/ai/test')
  return response.data
}
```

### Step 5: Frontend - Create Formatters

Create `frontend/src/lib/formatters.ts`:

```typescript
export function formatCurrency(amount: number): string {
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  })
  return formatter.format(amount)
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatMonth(monthStr: string): string {
  const [year, month] = monthStr.split('-')
  const date = new Date(parseInt(year), parseInt(month) - 1)
  return date.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  })
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}
```

### Step 6: Frontend - Update Types

Add to `frontend/src/types/index.ts`:

```typescript
// Transaction types
export interface Transaction {
  id: string
  hash: string
  date: string
  amount: number
  raw_description: string
  clean_merchant: string | null
  category_id: string | null
  account_id: string
  is_recurring: boolean
  recurring_group_id: string | null
  notes: string | null
  ai_categorized: boolean
  created_at: string
  updated_at: string
}

export interface TransactionListResponse {
  items: Transaction[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Dashboard types
export interface DashboardSummary {
  month: string
  total_income: number
  total_expenses: number
  net: number
  by_category: CategoryTotal[]
  vs_last_month: {
    income_change_pct: number
    expense_change_pct: number
  }
}

export interface CategoryTotal {
  category_id: string
  category_name: string
  amount: number
  percent: number
}

export interface MonthTrend {
  month: string
  income: number
  expenses: number
  net: number
}

export interface RecentTransaction {
  id: string
  date: string
  merchant: string
  category: string
  amount: number
}

// Account types
export interface Account {
  id: string
  name: string
  account_type: string
  is_active: boolean
  created_at: string
}

// Category types
export interface Category {
  id: string
  name: string
  parent_id: string | null
  color: string | null
  icon: string | null
  is_system: boolean
  children?: Category[]
}

// Settings types
export interface AISettings {
  provider: string
  model: string
  auto_categorize: boolean
  clean_merchants: boolean
  detect_format: boolean
}

export interface AvailableProvider {
  id: string
  name: string
  requires_key: boolean
  models: string[]
}

export interface SettingsResponse {
  ai: AISettings
  available_providers: AvailableProvider[]
}

// Import types
export interface DetectedFormat {
  columns: {
    date: number | null
    amount: number | null
    description: number | null
    category: number | null
    debit: number | null
    credit: number | null
    balance: number | null
  }
  date_format: string
  amount_style: 'signed' | 'separate_columns' | 'parentheses_negative'
  skip_rows: number
  source_guess: string | null
  confidence: number
}

export interface ImportUploadResponse {
  import_id: string
  filename: string
  row_count: number
  headers: string[]
  preview_rows: string[][]
  detected_format?: DetectedFormat | null
}
```

### Step 7: Frontend - Transaction List Page

Update `frontend/src/pages/Transactions.tsx`:

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTransactions, getCategories, getAccounts, updateTransaction, bulkCategorize } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatDate } from '@/lib/formatters'

export default function Transactions() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)

  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions', page, search, selectedAccount, selectedCategory],
    queryFn: () => getTransactions({
      page,
      per_page: 50,
      search: search || undefined,
      account_id: selectedAccount || undefined,
      category_id: selectedCategory || undefined,
    }),
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  })

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateTransaction(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setEditingId(null)
    },
  })

  const bulkCategorizeMutation = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) => 
      bulkCategorize(ids, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setSelectedIds(new Set())
    },
  })

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const selectAll = () => {
    if (selectedIds.size === transactions?.items?.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(transactions?.items?.map((t: any) => t.id)))
    }
  }

  const handleBulkCategorize = (categoryId: string) => {
    if (categoryId && selectedIds.size > 0) {
      bulkCategorizeMutation.mutate({
        ids: Array.from(selectedIds),
        categoryId,
      })
    }
  }

  // Flatten categories for dropdown
  const flatCategories = categories?.flatMap((cat: any) => [
    cat,
    ...(cat.children || [])
  ]) || []

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Transactions</h1>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Search..."
          className="border rounded px-3 py-2"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
        
        <select
          className="border rounded px-3 py-2"
          value={selectedAccount}
          onChange={(e) => {
            setSelectedAccount(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All Accounts</option>
          {accounts?.map((acc: any) => (
            <option key={acc.id} value={acc.id}>{acc.name}</option>
          ))}
        </select>

        <select
          className="border rounded px-3 py-2"
          value={selectedCategory}
          onChange={(e) => {
            setSelectedCategory(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All Categories</option>
          {flatCategories.map((cat: any) => (
            <option key={cat.id} value={cat.id}>
              {cat.parent_id ? '  ' : ''}{cat.name}
            </option>
          ))}
        </select>
      </div>

      {/* Bulk Actions */}
      {selectedIds.size > 0 && (
        <div className="flex gap-2 items-center bg-blue-50 p-3 rounded">
          <span className="text-sm">{selectedIds.size} selected</span>
          <select
            className="border rounded px-2 py-1 text-sm"
            defaultValue=""
            onChange={(e) => handleBulkCategorize(e.target.value)}
            disabled={bulkCategorizeMutation.isPending}
          >
            <option value="">Change category...</option>
            {flatCategories.map((cat: any) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          {bulkCategorizeMutation.isPending && (
            <span className="text-sm text-gray-500">Updating...</span>
          )}
          <Button variant="outline" size="sm" onClick={() => setSelectedIds(new Set())}>
            Clear selection
          </Button>
        </div>
      )}

      {/* Transaction Table */}
      <div className="border rounded overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds.size === transactions?.items?.length && transactions?.items?.length > 0}
                  onChange={selectAll}
                />
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Merchant</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Category</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {transactions?.items?.map((txn: any) => (
              <tr key={txn.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(txn.id)}
                    onChange={() => toggleSelect(txn.id)}
                  />
                </td>
                <td className="px-4 py-3 text-sm">{formatDate(txn.date)}</td>
                <td className="px-4 py-3">
                  <div className="text-sm font-medium">
                    {txn.clean_merchant || txn.raw_description}
                  </div>
                  {txn.clean_merchant && txn.clean_merchant !== txn.raw_description && (
                    <div className="text-xs text-gray-500 truncate max-w-xs">
                      {txn.raw_description}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  {editingId === txn.id ? (
                    <select
                      className="border rounded px-2 py-1 text-sm"
                      defaultValue={txn.category_id || ''}
                      onChange={(e) => {
                        updateMutation.mutate({
                          id: txn.id,
                          data: { category_id: e.target.value || null }
                        })
                      }}
                      onBlur={() => setEditingId(null)}
                      autoFocus
                    >
                      <option value="">Uncategorized</option>
                      {flatCategories.map((cat: any) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.parent_id ? '  ' : ''}{cat.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <button
                      className="text-sm text-left hover:text-blue-600 flex items-center gap-1"
                      onClick={() => setEditingId(txn.id)}
                    >
                      {flatCategories.find((c: any) => c.id === txn.category_id)?.name || 
                        <span className="text-gray-400">Uncategorized</span>}
                      {txn.ai_categorized && (
                        <span className="text-xs text-purple-500" title="AI categorized">✨</span>
                      )}
                    </button>
                  )}
                </td>
                <td className={`px-4 py-3 text-sm text-right font-medium ${
                  txn.amount < 0 ? 'text-red-600' : 'text-green-600'
                }`}>
                  {formatCurrency(txn.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500">
          Showing {transactions?.items?.length || 0} of {transactions?.total || 0}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="px-3 py-2 text-sm">
            Page {page} of {transactions?.pages || 1}
          </span>
          <Button
            variant="outline"
            disabled={page >= (transactions?.pages || 1)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
```

### Step 8: Frontend - Dashboard Page

Update `frontend/src/pages/Dashboard.tsx`:

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardSummary, getDashboardTrends, getRecentTransactions } from '@/lib/api'
import { formatCurrency, formatMonth, formatPercent } from '@/lib/formatters'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard-summary', selectedMonth],
    queryFn: () => getDashboardSummary(selectedMonth),
  })

  const { data: trends } = useQuery({
    queryKey: ['dashboard-trends'],
    queryFn: () => getDashboardTrends(6),
  })

  const { data: recentTransactions } = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => getRecentTransactions(5),
  })

  const navigateMonth = (direction: number) => {
    const [year, month] = selectedMonth.split('-').map(Number)
    let newMonth = month + direction
    let newYear = year
    
    if (newMonth > 12) {
      newMonth = 1
      newYear++
    } else if (newMonth < 1) {
      newMonth = 12
      newYear--
    }
    
    setSelectedMonth(`${newYear}-${String(newMonth).padStart(2, '0')}`)
  }

  if (summaryLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-6">
      {/* Month Selector */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1 border rounded hover:bg-gray-50"
            onClick={() => navigateMonth(-1)}
          >
            ◄
          </button>
          <span className="px-4 py-1 font-medium">{formatMonth(selectedMonth)}</span>
          <button
            className="px-3 py-1 border rounded hover:bg-gray-50"
            onClick={() => navigateMonth(1)}
          >
            ►
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-lg p-4">
          <div className="text-sm text-gray-500">Spent</div>
          <div className="text-2xl font-bold text-red-600">
            {formatCurrency(summary?.total_expenses || 0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {formatPercent(summary?.vs_last_month?.expense_change_pct || 0)} vs last month
          </div>
        </div>
        
        <div className="bg-white border rounded-lg p-4">
          <div className="text-sm text-gray-500">Income</div>
          <div className="text-2xl font-bold text-green-600">
            {formatCurrency(summary?.total_income || 0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {formatPercent(summary?.vs_last_month?.income_change_pct || 0)} vs last month
          </div>
        </div>
        
        <div className="bg-white border rounded-lg p-4">
          <div className="text-sm text-gray-500">Net</div>
          <div className={`text-2xl font-bold ${(summary?.net || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(summary?.net || 0)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="bg-white border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">Spending by Category</h2>
          <div className="space-y-3">
            {summary?.by_category?.slice(0, 8).map((cat: any) => (
              <div key={cat.category_id}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{cat.category_name}</span>
                  <span className="font-medium">{formatCurrency(cat.amount)}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${Math.min(cat.percent, 100)}%` }}
                  />
                </div>
              </div>
            ))}
            {(!summary?.by_category || summary.by_category.length === 0) && (
              <p className="text-gray-500 text-sm">No expenses this month</p>
            )}
          </div>
        </div>

        {/* Recent Transactions */}
        <div className="bg-white border rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Recent Transactions</h2>
            <Link to="/transactions" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {recentTransactions?.map((txn: any) => (
              <div key={txn.id} className="flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium">{txn.merchant}</div>
                  <div className="text-xs text-gray-500">{txn.category}</div>
                </div>
                <div className={`text-sm font-medium ${txn.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCurrency(txn.amount)}
                </div>
              </div>
            ))}
            {(!recentTransactions || recentTransactions.length === 0) && (
              <p className="text-gray-500 text-sm">No transactions yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Trends Chart (simple bar representation) */}
      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-4">Monthly Trends</h2>
        <div className="flex items-end gap-2 h-40">
          {trends?.map((month: any) => {
            const maxExpense = Math.max(...(trends?.map((t: any) => t.expenses) || [1]))
            const height = maxExpense > 0 ? (month.expenses / maxExpense) * 100 : 0
            return (
              <div key={month.month} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-red-200 rounded-t"
                  style={{ height: `${height}%`, minHeight: month.expenses > 0 ? '4px' : '0' }}
                  title={formatCurrency(month.expenses)}
                />
                <div className="text-xs text-gray-500 mt-1">
                  {month.month.split('-')[1]}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

---

## Final Steps

1. **Rebuild and restart:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

2. **Check for errors:**
   ```bash
   docker compose logs api --tail 50
   docker compose logs frontend --tail 50
   ```

3. **Test the endpoints:**
   ```bash
   # Health check
   curl http://localhost:8000/api/v1/health
   
   # Transactions with filters
   curl "http://localhost:8000/api/v1/transactions?page=1&per_page=10"
   curl "http://localhost:8000/api/v1/transactions?search=netflix"
   
   # Dashboard summary
   curl http://localhost:8000/api/v1/dashboard/summary
   curl "http://localhost:8000/api/v1/dashboard/summary?month=2025-01"
   
   # Dashboard trends
   curl http://localhost:8000/api/v1/dashboard/trends
   
   # Recent transactions
   curl http://localhost:8000/api/v1/dashboard/recent-transactions
   ```

4. **Test the UI:**
   - Go to http://localhost:5173
   - Check Dashboard shows summary cards and category breakdown
   - Navigate months with ◄ ► buttons
   - Go to Transactions page
   - Test search (type in search box)
   - Test account/category filters
   - Click a category to edit inline
   - Select multiple transactions with checkboxes
   - Use "Change category..." dropdown to bulk update

---

## Verification Checklist

- [ ] Dashboard shows spending summary for current month
- [ ] Month selector navigates between months
- [ ] Category breakdown shows top spending categories with bars
- [ ] Recent transactions widget shows latest transactions
- [ ] Trends chart shows 6 months of expense bars
- [ ] Transaction list loads with pagination info
- [ ] Search filters transactions by merchant/description
- [ ] Account dropdown filters by account
- [ ] Category dropdown filters by category
- [ ] Clicking category opens inline dropdown
- [ ] Changing category saves (no page reload needed)
- [ ] AI-categorized transactions show ✨ indicator
- [ ] Checkbox selection works (individual and select all)
- [ ] Bulk categorize dropdown updates selected transactions
- [ ] "Clear selection" button works
- [ ] Pagination Previous/Next buttons work
- [ ] Page count displays correctly

---

## Do NOT Implement Yet

- Recharts visualization library (keep simple bars for now)
- Budget targets
- Recurring transactions page (Phase 5)
- Alerts system (Phase 5)
- Export functionality

Keep it functional first. Pretty charts can come later.
