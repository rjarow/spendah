import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getNetWorthHistory } from '@/lib/api'
import { formatCurrency, formatMonth } from '@/lib/formatters'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { NetWorthHistoryPoint } from '@/types'

const periodRanges = {
  '3M': { months: 3 },
  '6M': { months: 6 },
  '1Y': { months: 12 },
  'All Time': { months: 999 },
}

export default function NetWorthChart() {
  const [selectedPeriod, setSelectedPeriod] = useState<'3M' | '6M' | '1Y' | 'All Time'>('6M')

  const { data: history, isLoading, error } = useQuery({
    queryKey: ['net-worth-history', selectedPeriod],
    queryFn: () => {
      const endDate = new Date()
      const startDate = new Date()
      startDate.setMonth(startDate.getMonth() - periodRanges[selectedPeriod].months)

      const startDateStr = startDate.toISOString().split('T')[0]
      const endDateStr = endDate.toISOString().split('T')[0]

      return getNetWorthHistory(startDateStr, endDateStr)
    },
  })

  if (isLoading) {
    return (
      <div className="bg-white border rounded-lg p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center text-gray-500">
            Loading net worth history...
          </div>
        </div>
      </div>
    )
  }

  if (error || !history || history.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-6">
        <div className="text-center text-gray-500">
          <p>No historical data available yet.</p>
          <p className="text-sm mt-1">Account balances will be tracked over time.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Net Worth Trend</h2>
        <div className="flex gap-2">
          {Object.keys(periodRanges).map((period) => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period as typeof selectedPeriod)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                selectedPeriod === period
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history}>
            <XAxis
              dataKey="date"
              tickFormatter={(date) => formatMonth(date)}
              tick={{ fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              dy={10}
            />
            <YAxis
              tickFormatter={(value) => formatCurrency(value)}
              tick={{ fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={70}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="bg-white border rounded-lg shadow-lg p-3">
                      <p className="text-sm text-gray-500 mb-2">{formatMonth(data.date)}</p>
                      <div className="space-y-1">
                        <p className="text-xs text-gray-500">Net Worth</p>
                        <p className="text-sm font-semibold text-blue-600">
                          {formatCurrency(data.net_worth)}
                        </p>
                        <p className="text-xs text-green-600">Assets: {formatCurrency(data.total_assets)}</p>
                        <p className="text-xs text-red-600">Liabilities: {formatCurrency(data.total_liabilities)}</p>
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />
            <Line
              type="monotone"
              dataKey="net_worth"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 6 }}
              name="Net Worth"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
