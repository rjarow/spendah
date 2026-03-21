import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardSummary, getDashboardTrends, getRecentTransactions, getUpcomingRenewals, getBudgets, getNetWorth } from '@/lib/api'
import { formatCurrency, formatMonth, formatPercent } from '@/lib/formatters'
import { Link } from 'react-router-dom'
import BudgetSummaryWidget from '@/components/BudgetSummaryWidget'
import NetWorthWidget from '@/components/NetWorthWidget'
import FinancialHealthScore from '@/components/FinancialHealthScore'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

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

  const { data: upcomingRenewals } = useQuery({
    queryKey: ['upcoming-renewals'],
    queryFn: () => getUpcomingRenewals(30),
  })

  const { data: budgets } = useQuery({
    queryKey: ['budgets', selectedMonth],
    queryFn: () => getBudgets(true),
  })

  const { data: netWorth } = useQuery({
    queryKey: ['net-worth'],
    queryFn: () => getNetWorth(),
  })

  const chartData = trends?.map(t => ({
    date: new Date(t.month + '-01').toLocaleDateString('en-US', { month: 'short' }),
    netWorth: t.net,
    income: t.income,
    expenses: t.expenses,
  })) || Array.from({ length: 6 }, (_, i) => {
    const date = new Date()
    date.setMonth(date.getMonth() - i)
    return {
      date: date.toLocaleDateString('en-US', { month: 'short' }),
      netWorth: 0,
      income: 0,
      expenses: 0,
    }
  }).reverse()

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Net Worth</h2>
            <Link to="/net-worth" className="text-sm text-blue-600 hover:underline">
              View Details →
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-500">Net Worth</div>
              <div className={`text-2xl font-bold ${netWorth?.net_worth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(netWorth?.net_worth || 0)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Assets</div>
              <div className="text-lg font-bold text-green-600">{formatCurrency(netWorth?.total_assets || 0)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Liabilities</div>
              <div className="text-lg font-bold text-red-600">{formatCurrency(netWorth?.total_liabilities || 0)}</div>
            </div>
          </div>
          <div className="mt-4 h-24">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorNetWorth" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={netWorth?.net_worth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={netWorth?.net_worth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb"/>
                <XAxis dataKey="date" hide tick={{ fontSize: 10 }}/>
                <YAxis hide domain={['dataMin', 'dataMax']} tick={{ fontSize: 10 }}/>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-white border rounded p-2 shadow-sm">
                          <div className="text-sm font-medium">{payload[0].payload.date}</div>
                          <div className="text-sm font-bold" style={{ color: netWorth?.net_worth >= 0 ? '#22c55e' : '#ef4444' }}>
                            {formatCurrency(payload[0].value)}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Area type="monotone" dataKey="netWorth" stroke={netWorth?.net_worth >= 0 ? '#22c55e' : '#ef4444'} strokeWidth={2} fillOpacity={1} fill="url(#colorNetWorth)"/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <FinancialHealthScore month={selectedMonth} />
        </div>
      </div>

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
          <div className="text-sm text-gray-500">Budgets</div>
          <div className="text-2xl font-bold">
            {budgets?.total || 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {budgets?.total > 0 ? 'Active this month' : 'No budgets set'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Spending by Category</h2>
            <Link to="/transactions" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {summary?.by_category?.slice(0, 8).map((cat) => (
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
