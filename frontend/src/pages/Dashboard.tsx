import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardSummary, getDashboardTrends, getRecentTransactions, getUpcomingRenewals, getBudgets, getNetWorth, getAccountBalances, getCategoryTrends } from '@/lib/api'
import { formatCurrency, formatMonth, formatPercent } from '@/lib/formatters'
import { Link } from 'react-router-dom'
import BudgetSummaryWidget from '@/components/BudgetSummaryWidget'
import { ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, Wallet, PiggyBank, CreditCard } from 'lucide-react'

export default function Dashboard() {
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard-summary', selectedMonth],
    queryFn: () => getDashboardSummary(selectedMonth),
  })

  const { data: accountBalances } = useQuery({
    queryKey: ['account-balances'],
    queryFn: () => getAccountBalances(),
  })

  const { data: categoryTrends } = useQuery({
    queryKey: ['category-trends'],
    queryFn: () => getCategoryTrends(3),
  })

  const { data: recentTransactions } = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => getRecentTransactions(5),
  })

  const { data: upcomingRenewals } = useQuery({
    queryKey: ['upcoming-renewals'],
    queryFn: () => getUpcomingRenewals(30),
  })

  const { data: budgets } = useQuery({
    queryKey: ['budgets', selectedMonth],
    queryFn: () => getBudgets(true),
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

  const spendingSpikes = categoryTrends?.categories.filter(c => c.is_spike) || []
  const savingsRate = summary?.savings_rate
  const savingsRateColor = savingsRate === null ? 'text-gray-500' : savingsRate >= 20 ? 'text-green-600' : savingsRate >= 10 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">Net Worth</div>
            <Wallet className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`text-2xl font-bold ${accountBalances?.net_worth && accountBalances.net_worth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(accountBalances?.net_worth || 0)}
          </div>
          {accountBalances?.change_from_last_month !== null && accountBalances?.change_from_last_month !== undefined && (
            <div className={`text-xs flex items-center gap-1 mt-1 ${accountBalances.change_from_last_month >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {accountBalances.change_from_last_month >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              {formatCurrency(Math.abs(accountBalances.change_from_last_month))} vs last month
            </div>
          )}
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">Monthly Spend</div>
            <CreditCard className="w-4 h-4 text-gray-400" />
          </div>
          <div className="text-2xl font-bold text-red-600">
            {formatCurrency(summary?.total_expenses || 0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {summary?.daily_average_spend && `${formatCurrency(summary.daily_average_spend)}/day avg`}
            {summary?.projected_spend && ` • ${formatCurrency(summary.projected_spend)} projected`}
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">Savings Rate</div>
            <PiggyBank className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`text-2xl font-bold ${savingsRateColor}`}>
            {savingsRate !== null ? `${savingsRate.toFixed(1)}%` : 'N/A'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {savingsRate === null ? 'No income this month' : savingsRate >= 20 ? 'Excellent!' : savingsRate >= 10 ? 'Good' : 'Needs improvement'}
          </div>
        </div>
      </div>

      {accountBalances?.accounts && accountBalances.accounts.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Accounts</h2>
            <Link to="/accounts" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {accountBalances.accounts.map((account) => (
              <Link
                key={account.id}
                to={`/accounts/${account.id}`}
                className="flex-shrink-0 min-w-[160px] p-3 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="text-xs text-gray-500 truncate">{account.name}</div>
                <div className={`text-lg font-bold ${account.is_asset ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(account.calculated_balance)}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Spending by Category</h2>
            <Link to="/transactions" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {summary?.by_category?.slice(0, 8).map((cat) => {
              const trend = categoryTrends?.categories.find(t => t.category_id === cat.category_id)
              const isUp = trend && trend.change_pct && trend.change_pct > 0
              const isDown = trend && trend.change_pct && trend.change_pct < 0
              return (
                <div key={cat.category_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="flex items-center gap-1">
                      {cat.category_name}
                      {isUp && <TrendingUp className="w-3 h-3 text-red-500" />}
                      {isDown && <TrendingDown className="w-3 h-3 text-green-500" />}
                    </span>
                    <span className="font-medium">{formatCurrency(cat.amount)}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${Math.min(cat.percent, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
            {(!summary?.by_category || summary.by_category.length === 0) && (
              <p className="text-gray-500 text-sm">No expenses this month</p>
            )}
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Budget Progress</h2>
            <Link to="/budgets" className="text-sm text-blue-600 hover:underline">
              View All →
            </Link>
          </div>
          <BudgetSummaryWidget month={selectedMonth} />
        </div>
      </div>

      {spendingSpikes.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-3">Spending Spikes</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {spendingSpikes.map((spike) => (
              <div key={spike.category_id} className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="font-medium text-red-800">{spike.category_name}</div>
                <div className="text-sm text-red-600">
                  {spike.change_pct && spike.change_pct > 0 ? '+' : ''}{spike.change_pct?.toFixed(0) || 0}% vs prior month
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Recent Transactions</h2>
            <Link to="/transactions" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {recentTransactions?.map((txn) => (
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

        <div className="bg-white border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">Upcoming Renewals</h2>
          <div className="space-y-3">
            {upcomingRenewals?.renewals?.slice(0, 5).map((renewal) => (
              <div key={renewal.recurring_group_id} className="flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium">{renewal.merchant}</div>
                  <div className="text-xs text-gray-500">
                    {renewal.days_until === 0 ? 'Today' :
                     renewal.days_until === 1 ? 'Tomorrow' :
                     `In ${renewal.days_until} days`}
                  </div>
                </div>
                <div className="text-sm font-medium text-red-600">
                  {formatCurrency(renewal.amount)}
                </div>
              </div>
            ))}
            {(!upcomingRenewals?.renewals || upcomingRenewals.renewals.length === 0) && (
              <p className="text-sm text-gray-500">No upcoming renewals in next 30 days</p>
            )}
          </div>
          {upcomingRenewals?.total_upcoming_30_days > 0 && (
            <div className="mt-3 pt-3 border-t text-sm">
              <span className="text-gray-500">Total next 30 days:</span>
              <span className="font-medium text-red-600 ml-2">
                {formatCurrency(upcomingRenewals.total_upcoming_30_days)}
              </span>
            </div>
          )}
        </div>
      </div>

    </div>
  )
}
