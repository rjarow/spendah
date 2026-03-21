import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, updateAlert, deleteAlert, getAlertSettings, updateAlertSettings, getSpendingByCategory, getMerchantRanking, getMonthlySummary, getAnomalies } from '@/lib/api'
import { Button } from '@/components/ui/button'
import SubscriptionReviewModal from '@/components/alerts/SubscriptionReviewModal'
import { formatCurrency } from '@/lib/formatters'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend } from 'recharts'
import { Link } from 'react-router-dom'

const SEVERITY_STYLES: Record<string, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  attention: 'bg-red-50 border-red-200 text-red-800',
}

const SEVERITY_LABELS: Record<string, string> = {
  info: 'INFO',
  warning: 'WARNING',
  attention: 'ATTENTION',
}

const TYPE_LABELS: Record<string, string> = {
  large_purchase: 'Large Purchase',
  price_increase: 'Price Increase',
  new_recurring: 'New Subscription',
  unusual_merchant: 'New Merchant',
  annual_charge: 'Annual Charge',
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

export default function Insights() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'trends' | 'alerts'>('trends')
  const [showDismissed, setShowDismissed] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [months, setMonths] = useState(6)

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts', { is_dismissed: showDismissed ? undefined : false }],
    queryFn: () => getAlerts({
      is_dismissed: showDismissed ? undefined : false,
      limit: 100,
    }),
  })

  const { data: settings } = useQuery({
    queryKey: ['alert-settings'],
    queryFn: getAlertSettings,
  })

  const { data: spendingByCategory } = useQuery({
    queryKey: ['spending-by-category', months],
    queryFn: () => getSpendingByCategory(months),
  })

  const { data: merchantRanking } = useQuery({
    queryKey: ['merchant-ranking', 3],
    queryFn: () => getMerchantRanking(3, 10),
  })

  const { data: monthlySummary } = useQuery({
    queryKey: ['monthly-summary', 12],
    queryFn: () => getMonthlySummary(12),
  })

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', 3],
    queryFn: () => getAnomalies(3),
  })

  const dismissMutation = useMutation({
    mutationFn: (data: { id: string; is_read: boolean }) => updateAlert(data.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const updateSettingsMutation = useMutation({
    mutationFn: updateAlertSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-settings'] })
    },
  })

  const alerts = alertsData?.items || []
  const unreadCount = alertsData?.unread_count || 0

  const monthlyChartData = monthlySummary?.months.map(m => ({
    month: new Date(m.month + '-01').toLocaleDateString('en-US', { month: 'short' }),
    income: m.income,
    expenses: Math.abs(m.expenses),
    net: m.net,
    savingsRate: m.savings_rate || 0,
  })) || []

  const currentMonthCategories = spendingByCategory?.categories.map(c => {
    const currentMonth = spendingByCategory.months[spendingByCategory.months.length - 1]
    const currentAmount = c.monthly_totals.find(t => t.month === currentMonth)?.amount || 0
    return {
      name: c.category_name,
      value: currentAmount,
    }
  }).filter(c => c.value > 0) || []

  const savingsRateData = monthlySummary?.months.map(m => ({
    month: new Date(m.month + '-01').toLocaleDateString('en-US', { month: 'short' }),
    savingsRate: m.savings_rate || 0,
  })) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Insights & Alerts</h1>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500">{unreadCount} unread alerts</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            className={`px-4 py-2 rounded-lg font-medium ${activeTab === 'trends' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            onClick={() => setActiveTab('trends')}
          >
            Trends
          </button>
          <button
            className={`px-4 py-2 rounded-lg font-medium ${activeTab === 'alerts' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            onClick={() => setActiveTab('alerts')}
          >
            Alerts {unreadCount > 0 && `(${unreadCount})`}
          </button>
        </div>
      </div>

      {activeTab === 'trends' && (
        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">Monthly Overview</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v / 1000}k`} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Legend />
                  <Bar dataKey="income" fill="#10b981" name="Income" />
                  <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Spending by Category</h2>
              {currentMonthCategories.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={currentMonthCategories}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {currentMonthCategories.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No spending data this month</p>
              )}
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Savings Rate Trend</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={savingsRateData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                    <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                    <Line type="monotone" dataKey="savingsRate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Top Merchants</h2>
              <div className="space-y-3">
                {merchantRanking?.merchants.slice(0, 8).map((m, i) => (
                  <div key={i} className="flex justify-between items-center">
                    <div>
                      <div className="text-sm font-medium">{m.merchant}</div>
                      <div className="text-xs text-gray-500">{m.transaction_count} transactions • {m.category}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">{formatCurrency(m.total)}</div>
                      {m.change_pct !== null && (
                        <div className={`text-xs ${m.change_pct > 0 ? 'text-red-500' : 'text-green-500'}`}>
                          {m.change_pct > 0 ? '+' : ''}{m.change_pct.toFixed(0)}%
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {(!merchantRanking?.merchants || merchantRanking.merchants.length === 0) && (
                  <p className="text-gray-500 text-sm">No merchant data</p>
                )}
              </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Spending Anomalies</h2>
              <div className="space-y-3">
                {anomalies?.anomalies.map((a, i) => (
                  <div key={i} className={`p-3 rounded-lg border ${a.severity === 'high' ? 'bg-red-50 border-red-200' : a.severity === 'medium' ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-sm font-medium">{a.description}</div>
                        <div className="text-xs text-gray-500">{a.category}</div>
                      </div>
                      <div className="text-sm font-medium">{formatCurrency(a.amount)}</div>
                    </div>
                    {a.transaction_id && (
                      <Link to={`/transactions?id=${a.transaction_id}`} className="text-xs text-blue-600 hover:underline mt-1 inline-block">
                        View transaction
                      </Link>
                    )}
                  </div>
                ))}
                {(!anomalies?.anomalies || anomalies.anomalies.length === 0) && (
                  <p className="text-gray-500 text-sm">No anomalies detected</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'alerts' && (
        <>
          <div className="flex gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={showDismissed}
                onChange={(e) => setShowDismissed(e.target.checked)}
                className="rounded"
              />
              Show dismissed
            </label>
            <Button onClick={() => setShowReviewModal(true)}>
              Subscription Review
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowSettings(!showSettings)}
            >
              Settings
            </Button>
          </div>

          {showSettings && settings && (
            <div className="bg-gray-50 border rounded-lg p-4 space-y-4">
              <h2 className="font-semibold">Alert Settings</h2>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Large Purchase Multiplier
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    className="border rounded px-3 py-2 w-full"
                    value={settings.large_purchase_multiplier}
                    onChange={(e) => updateSettingsMutation.mutate({
                      large_purchase_multiplier: parseFloat(e.target.value),
                    })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Alert when purchase exceeds Nx category average
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    New Merchant Threshold
                  </label>
                  <input
                    type="number"
                    step="50"
                    min="0"
                    className="border rounded px-3 py-2 w-full"
                    value={settings.unusual_merchant_threshold}
                    onChange={(e) => updateSettingsMutation.mutate({
                      unusual_merchant_threshold: parseFloat(e.target.value),
                    })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Alert for first-time merchants over this amount
                  </p>
                </div>
              </div>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings.alerts_enabled}
                  onChange={(e) => updateSettingsMutation.mutate({
                    alerts_enabled: e.target.checked,
                  })}
                  className="rounded"
                />
                <span className="text-sm">Enable alerts</span>
              </label>
            </div>
          )}

          {alertsLoading ? (
            <div className="p-4">Loading...</div>
          ) : (
            <div className="space-y-4">
              {alerts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p className="text-4xl mb-2">No alerts! Everything looks good.</p>
                </div>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`border rounded-lg p-4 ${SEVERITY_STYLES[alert.severity]} ${
                      alert.is_dismissed ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-xs font-medium mb-1">
                          {SEVERITY_LABELS[alert.severity]}
                        </div>
                        <div className="font-semibold">{alert.title}</div>
                        <div className="text-sm mt-1">{alert.description}</div>
                        <div className="text-xs mt-2 opacity-75">
                          {TYPE_LABELS[alert.type]} • {new Date(alert.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {!alert.is_dismissed && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => dismissMutation.mutate({
                              id: alert.id,
                              is_read: true,
                            })}
                          >
                            Dismiss
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            if (confirm('Delete this alert permanently?')) {
                              deleteMutation.mutate(alert.id)
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          <SubscriptionReviewModal
            isOpen={showReviewModal}
            onClose={() => setShowReviewModal(false)}
          />
        </>
      )}
    </div>
  )
}
