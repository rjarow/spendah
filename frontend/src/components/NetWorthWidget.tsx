import { useQuery } from '@tanstack/react-query'
import { getNetWorth, getNetWorthHistory } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface NetWorthWidgetProps {
  compact?: boolean
}

export default function NetWorthWidget({ compact = false }: NetWorthWidgetProps) {
  const { data: currentNetWorth, isLoading: currentLoading } = useQuery({
    queryKey: ['net-worth'],
    queryFn: getNetWorth,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['net-worth-history'],
    queryFn: async () => {
      const now = new Date()
      const lastMonth = new Date(now)
      lastMonth.setMonth(lastMonth.getMonth() - 1)

      return getNetWorthHistory(
        lastMonth.toISOString().split('T')[0],
        now.toISOString().split('T')[0]
      )
    },
  })

  if (currentLoading || historyLoading) {
    return (
      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-4">
          {compact ? 'Net Worth' : 'Financial Health'}
        </h2>
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="flex justify-between text-sm mb-1">
                <div className="h-4 w-24 bg-gray-200 rounded" />
                <div className="h-4 w-16 bg-gray-200 rounded" />
              </div>
              <div className="h-16 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  const netWorth = currentNetWorth?.net_worth || 0
  const assets = currentNetWorth?.total_assets || 0
  const liabilities = currentNetWorth?.total_liabilities || 0

  const lastMonthNetWorth = history?.[0]?.net_worth || netWorth
  const change = netWorth - lastMonthNetWorth
  const changePercent = lastMonthNetWorth !== 0 ? (change / lastMonthNetWorth) * 100 : 0

  const trendIcon = change > 0 ? (
    <TrendingUp className="w-4 h-4 text-green-600" />
  ) : change < 0 ? (
    <TrendingDown className="w-4 h-4 text-red-600" />
  ) : (
    <Minus className="w-4 h-4 text-gray-400" />
  )

  const trendColor = change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-400'
  const trendBg = change > 0 ? 'bg-green-50' : change < 0 ? 'bg-red-50' : 'bg-gray-50'

  const chartData = history?.map((point) => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    netWorth: point.net_worth,
  })) || []

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">
          {compact ? 'Net Worth' : 'Financial Health'}
        </h2>
        <Link to="/net-worth" className="text-sm text-blue-600 hover:underline">
          View Details →
        </Link>
      </div>

      {compact ? (
        <>
          <div className="flex items-end gap-3 mb-3">
            <div className={`text-2xl font-bold ${netWorth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(netWorth)}
            </div>
            <div className={`flex items-center gap-1 px-2 py-1 rounded ${trendBg} ${trendColor} text-sm font-medium`}>
              {trendIcon}
              <span>{change >= 0 ? '+' : ''}{change.toFixed(0)}</span>
              <span className="text-gray-500 text-xs">({changePercent.toFixed(1)}%)</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500 mb-1">Assets</div>
              <div className="font-medium text-green-600">{formatCurrency(assets)}</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Liabilities</div>
              <div className="font-medium text-red-600">{formatCurrency(liabilities)}</div>
            </div>
          </div>

          <div className="mt-4 h-16">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorNetWorth" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={netWorth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={netWorth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0}/>
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
                          <div className="text-sm font-bold" style={{ color: netWorth >= 0 ? '#22c55e' : '#ef4444' }}>
                            {formatCurrency(payload[0].value)}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Area type="monotone" dataKey="netWorth" stroke={netWorth >= 0 ? '#22c55e' : '#ef4444'} strokeWidth={2} fillOpacity={1} fill="url(#colorNetWorth)"/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <div className="text-sm text-gray-500">Net Worth</div>
              <div className={`text-xl font-bold ${netWorth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(netWorth)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Assets</div>
              <div className="text-lg font-bold text-green-600">{formatCurrency(assets)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Liabilities</div>
              <div className="text-lg font-bold text-red-600">{formatCurrency(liabilities)}</div>
            </div>
          </div>

          <div className={`flex items-center gap-2 px-3 py-2 rounded ${trendBg} ${trendColor} text-sm`}>
            {trendIcon}
            <span className="font-medium">
              {change >= 0 ? '+' : ''}{change.toFixed(0)}
            </span>
            <span className="text-gray-500">
              ({changePercent.toFixed(1)}% vs last month)
            </span>
          </div>

          <div className="mt-4 h-24">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorNetWorth2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={netWorth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={netWorth >= 0 ? '#22c55e' : '#ef4444'} stopOpacity={0}/>
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
                          <div className="text-sm font-bold" style={{ color: netWorth >= 0 ? '#22c55e' : '#ef4444' }}>
                            {formatCurrency(payload[0].value)}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Area type="monotone" dataKey="netWorth" stroke={netWorth >= 0 ? '#22c55e' : '#ef4444'} strokeWidth={2} fillOpacity={1} fill="url(#colorNetWorth2)"/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
