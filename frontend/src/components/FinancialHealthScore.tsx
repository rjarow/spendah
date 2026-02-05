import { useQuery } from '@tanstack/react-query'
import { getBudgets, getNetWorth, getUpcomingRenewals } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { TrendingUp, CheckCircle, AlertCircle, Shield } from 'lucide-react'

interface FinancialHealthScoreProps {
  month?: string
}

export default function FinancialHealthScore({ month }: FinancialHealthScoreProps) {
  const { data: budgets } = useQuery({
    queryKey: ['budgets', month],
    queryFn: () => getBudgets(true),
  })

  const { data: netWorth } = useQuery({
    queryKey: ['net-worth'],
    queryFn: getNetWorth,
  })

  const { data: upcomingRenewals } = useQuery({
    queryKey: ['upcoming-renewals'],
    queryFn: () => getUpcomingRenewals(30),
  })

  if (!budgets?.items || budgets.items.length === 0 || !netWorth || !upcomingRenewals) {
    return null
  }

  const totalBudgets = budgets.items.length
  const onTrackBudgets = budgets.items.filter((b) => !b.is_over_budget).length
  const budgetHealthScore = totalBudgets > 0 ? Math.round((onTrackBudgets / totalBudgets) * 100) : 0

  const lastMonthNetWorth = netWorth.total_assets - netWorth.total_liabilities
  const isNetWorthGrowing = lastMonthNetWorth > 0 && netWorth.net_worth > lastMonthNetWorth

  const monthlyRenewalCost = upcomingRenewals.total_upcoming_30_days || 0
  const hasTooManyRenewals = monthlyRenewalCost > 300

  const totalScore = Math.min(100, Math.round(
    (budgetHealthScore * 0.4) +
    (isNetWorthGrowing ? 30 : 10) +
    (hasTooManyRenewals ? 10 : 20)
  ))

  const scoreColor = totalScore >= 70 ? 'text-green-600' : totalScore >= 40 ? 'text-yellow-600' : 'text-red-600'
  const scoreBg = totalScore >= 70 ? 'bg-green-50' : totalScore >= 40 ? 'bg-yellow-50' : 'bg-red-50'

  const getScoreColor = () => {
    if (totalScore >= 70) return '#22c55e'
    if (totalScore >= 40) return '#eab308'
    return '#ef4444'
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-gray-900">Financial Health Score</h3>
        <div className={`flex items-center gap-1 px-2 py-1 rounded ${scoreBg} ${scoreColor} text-xs font-bold`}>
          {totalScore}/100
        </div>
      </div>

      <div className="flex items-center justify-center py-4">
        <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="10"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={getScoreColor()}
            strokeWidth="10"
            strokeDasharray={`${totalScore * 2.51} 251`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <Shield className="w-6 h-6" />
          <span className="text-xs font-semibold mt-1">{totalScore}</span>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-gray-700">
            <CheckCircle className="w-4 h-4" />
            Budgets
          </span>
          <span className={`font-medium ${budgetHealthScore >= 70 ? 'text-green-600' : budgetHealthScore >= 40 ? 'text-yellow-600' : 'text-red-600'}`}>
            {budgetHealthScore}%
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-gray-700">
            {isNetWorthGrowing ? <TrendingUp className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            Net Worth
          </span>
          <span className={isNetWorthGrowing ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
            {isNetWorthGrowing ? 'Growing' : 'Declining'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-gray-700">
            <AlertCircle className="w-4 h-4" />
            Subscriptions
          </span>
          <span className={hasTooManyRenewals ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
            {hasTooManyRenewals ? 'High' : 'Controlled'}
          </span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t text-xs text-gray-500">
        <span className="font-medium">Next steps:</span>
        {totalScore < 70 && (
          <span className="block mt-1">
            Review over-budget categories and consider subscription management
          </span>
        )}
      </div>
    </div>
  )
}
