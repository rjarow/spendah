import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getBudgets, getCategories, createBudget, updateBudget, deleteBudget, getBudgetProgress, getBudgetSuggestions, acceptBudgetSuggestions } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { BudgetProgressBar } from '@/components/BudgetProgressBar'
import { formatCurrency } from '@/lib/formatters'
import { Trash2, Edit, Plus, Target, AlertCircle, Calendar, Sparkles } from 'lucide-react'
import type { Budget, BudgetProgress, Category, BudgetSuggestion } from '@/types'

export default function Budgets() {
  const queryClient = useQueryClient()
  const [showDialog, setShowDialog] = useState(false)
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null)
  const [formData, setFormData] = useState({
    category_id: '',
    amount: '',
    period: 'monthly' as 'weekly' | 'monthly' | 'yearly',
    start_date: new Date().toISOString().split('T')[0],
  })
  const [viewPeriod, setViewPeriod] = useState<'current' | 'previous' | 'last30' | 'last90'>('current')

  // Get date ranges for historical views (must be before query that uses it)
  const getDateRange = () => {
    const today = new Date()
    switch (viewPeriod) {
      case 'last30':
        return {
          start: new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: today.toISOString().split('T')[0]
        }
      case 'last90':
        return {
          start: new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: today.toISOString().split('T')[0]
        }
      case 'previous':
        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
        const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
        return {
          start: lastMonth.toISOString().split('T')[0],
          end: lastMonthEnd.toISOString().split('T')[0]
        }
      default: // current
        return null
    }
  }

  const dateRange = getDateRange()

  const { data: budgets, isLoading: budgetsLoading } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => getBudgets(true),
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  })

  const { data: suggestions } = useQuery({
    queryKey: ['budget-suggestions'],
    queryFn: () => getBudgetSuggestions(3),
  })

  const acceptSuggestionMutation = useMutation({
    mutationFn: acceptBudgetSuggestions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['budget-suggestions'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: createBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setShowDialog(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setShowDialog(false)
      setEditingBudget(null)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
    },
  })

  // Fetch progress data for historical periods
  const { data: progressData } = useQuery({
    queryKey: ['budgets-progress', dateRange?.start, dateRange?.end],
    queryFn: () => {
      if (!dateRange) return null
      return Promise.all(
        budgets?.items.map((budget: Budget) =>
          getBudgetProgress(budget.id, dateRange.start)
        ) || []
      )
    },
    enabled: !!dateRange && !!budgets?.items,
    staleTime: 5 * 60 * 1000,
  })

  const flatCategories = categories?.items?.flatMap((cat: Category) => [
    cat,
    ...(cat.children || [])
  ]) || []

  const resetForm = () => {
    setFormData({
      category_id: '',
      amount: '',
      period: 'monthly',
      start_date: new Date().toISOString().split('T')[0],
    })
  }

  const handleOpenCreateDialog = () => {
    resetForm()
    setEditingBudget(null)
    setShowDialog(true)
  }

  const handleOpenEditDialog = (budget: Budget) => {
    setFormData({
      category_id: budget.category_id || '',
      amount: budget.amount.toString(),
      period: budget.period,
      start_date: budget.start_date,
    })
    setEditingBudget(budget)
    setShowDialog(true)
  }

  const handleSubmit = () => {
    const data = {
      category_id: formData.category_id || null,
      amount: parseFloat(formData.amount) || 0,
      period: formData.period,
      start_date: formData.start_date,
    }

    if (editingBudget) {
      updateMutation.mutate({ id: editingBudget.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this budget?')) {
      deleteMutation.mutate(id)
    }
  }

  const getPeriodLabel = (period: string) => {
    switch (period) {
      case 'current': return 'Current Period'
      case 'previous': return 'Previous Period'
      case 'last30': return 'Last 30 Days'
      case 'last90': return 'Last 90 Days'
      default: return period
    }
  }

  if (budgetsLoading) {
    return <div className="p-4">Loading budgets...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Budgets</h1>
          <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-2">
            <Calendar className="h-4 w-4 text-gray-500" />
            <select
              value={viewPeriod}
              onChange={(e) => setViewPeriod(e.target.value as any)}
              className="text-sm text-gray-700 bg-transparent border-none focus:ring-0 cursor-pointer"
            >
              <option value="current">Current Period</option>
              <option value="previous">Previous Period</option>
              <option value="last30">Last 30 Days</option>
              <option value="last90">Last 90 Days</option>
            </select>
          </div>
        </div>
        <Button onClick={handleOpenCreateDialog}>
          <Plus className="h-4 w-4 mr-2" />
          Add Budget
        </Button>
      </div>

      {suggestions && suggestions.items && suggestions.items.length > 0 && (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold text-gray-900">Budget Suggestions</h2>
          </div>
          <p className="text-sm text-gray-600">
            Based on your spending patterns, we recommend setting up these budgets:
          </p>
          <div className="grid gap-3">
            {suggestions.items.map((suggestion: BudgetSuggestion) => (
              <div key={suggestion.category_id} className="bg-white rounded-lg p-4 flex items-center justify-between shadow-sm">
                <div>
                  <h3 className="font-medium text-gray-900">{suggestion.category_name}</h3>
                  <p className="text-sm text-gray-500">
                    Avg ${formatCurrency(suggestion.avg_monthly_spend)}/mo over 3 months ({suggestion.transaction_count} transactions)
                  </p>
                  <p className="text-sm font-medium text-purple-600 mt-1">
                    Suggested budget: {formatCurrency(suggestion.suggested_amount)}/mo
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => acceptSuggestionMutation.mutate([{
                    category_id: suggestion.category_id,
                    amount: suggestion.suggested_amount,
                    period: 'monthly',
                  }])}
                  disabled={acceptSuggestionMutation.isPending}
                >
                  Accept
                </Button>
              </div>
            ))}
          </div>
          {suggestions.items.length > 1 && (
            <div className="pt-2 border-t border-purple-200">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => acceptSuggestionMutation.mutate(
                  suggestions.items.map((s: BudgetSuggestion) => ({
                    category_id: s.category_id,
                    amount: s.suggested_amount,
                    period: 'monthly' as const,
                  }))
                )}
                disabled={acceptSuggestionMutation.isPending}
                className="text-purple-700 hover:text-purple-800 hover:bg-purple-100"
              >
                Accept All Suggestions
              </Button>
            </div>
          )}
        </div>
      )}

      {(!budgets?.items || budgets.items.length === 0) ? (
        <div className="bg-white border rounded-lg p-8 text-center">
          <Target className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">No budgets set up yet</h2>
          <p className="text-gray-500 mb-4">
            Create budgets to track your spending and get notified when you're approaching or exceeding your limits.
          </p>
          <Button onClick={handleOpenCreateDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Create Your First Budget
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {budgets.items.map((budget: Budget) => {
            const progress = progressData?.find((p: BudgetProgress) => p?.id === budget.id)
            const displayBudget = progress || budget

            return (
              <div
                key={budget.id}
                className="bg-white border rounded-lg p-6 space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                      {displayBudget.category_name}
                      {displayBudget.category_id === null && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          Overall Budget
                        </span>
                      )}
                      {displayBudget.is_over_budget && (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                    </h3>
                    <p className="text-sm text-gray-500 capitalize">
                      {budget.period} budget {viewPeriod !== 'current' && `(as of ${getPeriodLabel(viewPeriod)})`}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenEditDialog(budget)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(budget.id)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <BudgetProgressBar
                  budgetName={displayBudget.category_name}
                  spent={displayBudget.spent || 0}
                  limit={displayBudget.amount}
                  percentUsed={displayBudget.percent_used || 0}
                />

                <div className="text-sm text-gray-600 pt-2 border-t">
                  <div className="flex justify-between">
                    <span>Spent:</span>
                    <span className={displayBudget.is_over_budget ? 'text-red-600 font-medium' : ''}>
                      {formatCurrency(displayBudget.spent || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span>Remaining:</span>
                    <span className={displayBudget.is_over_budget ? 'text-red-600 font-medium' : ''}>
                      {formatCurrency(displayBudget.remaining || 0)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                {editingBudget ? 'Edit Budget' : 'Create Budget'}
              </h2>
              <button
                onClick={() => {
                  setShowDialog(false)
                  setEditingBudget(null)
                  resetForm()
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category (optional)
                </label>
                <select
                  value={formData.category_id}
                  onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="">Overall Budget (all categories)</option>
                  {flatCategories.map((cat: Category) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.parent_id ? '  ' : ''}{cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Amount
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Period
                </label>
                <select
                  value={formData.period}
                  onChange={(e) => setFormData({ ...formData, period: e.target.value as any })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="outline"
                onClick={() => {
                  setShowDialog(false)
                  setEditingBudget(null)
                  resetForm()
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!formData.amount || createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingBudget
                  ? 'Save Changes'
                  : 'Create Budget'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
