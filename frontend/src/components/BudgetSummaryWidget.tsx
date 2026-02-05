import { useQuery } from '@tanstack/react-query'
import { getBudgets, type BudgetProgress } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { Link } from 'react-router-dom'

interface BudgetSummaryWidgetProps {
  month?: string
}

export default function BudgetSummaryWidget({ month }: BudgetSummaryWidgetProps) {
  const { data: budgets, isLoading, error } = useQuery({
    queryKey: ['budgets', month],
    queryFn: () => getBudgets(true),
  })

  if (isLoading) {
    return (
      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-4">Budget Summary</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="flex justify-between text-sm">
                <div className="h-4 w-24 bg-gray-200 rounded" />
                <div className="h-4 w-12 bg-gray-200 rounded" />
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2 mt-1">
                <div className="h-2 bg-gray-200 rounded-full" style={{ width: '50%' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error || !budgets?.items || budgets.items.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Budget Summary</h2>
          <Link to="/budgets" className="text-sm text-blue-600 hover:underline">
            Set up budgets →
          </Link>
        </div>
        <div className="text-center py-8">
          <p className="text-gray-500 text-sm">No budgets set up yet</p>
          <Link
            to="/budgets"
            className="inline-block mt-3 px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            Create your first budget
          </Link>
        </div>
      </div>
    )
  }

  const topBudgets = [...budgets.items]
    .filter((b) => b.percent_used > 0)
    .sort((a, b) => b.percent_used - a.percent_used)
    .slice(0, 5)

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Budget Summary</h2>
        <Link to="/budgets" className="text-sm text-blue-600 hover:underline">
          View All →
        </Link>
      </div>
      <div className="space-y-3">
        {topBudgets.map((budget) => {
          const progress: BudgetProgress = {
            budget_id: budget.id,
            spent: budget.current_period_spent,
            remaining: budget.remaining,
            percent_used: budget.percent_used,
            is_over_budget: budget.is_over_budget,
          }
          return (
            <div key={budget.id} className="flex justify-between items-center text-sm">
              <div className="flex-1 pr-2">
                <div className="font-medium truncate" title={budget.category_name}>
                  {budget.category_name}
                </div>
                {budget.is_over_budget && (
                  <div className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium mt-1">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    Over
                  </div>
                )}
              </div>
              <div className={`text-xs font-semibold ${budget.is_over_budget ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(budget.remaining)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
