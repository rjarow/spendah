import { useQuery } from '@tanstack/react-query'
import { getNetWorthBreakdown } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Wallet, TrendingUp, TrendingDown, RefreshCw, ChevronRight } from 'lucide-react'
import type { AccountWithBalance } from '@/types'
import NetWorthChart from '@/components/NetWorthChart'

const accountTypeLabels: Record<string, string> = {
  checking: 'Checking',
  savings: 'Savings',
  credit_card: 'Credit Card',
  investment: 'Investment',
  loan: 'Loan',
  mortgage: 'Mortgage',
  cash: 'Cash',
  other: 'Other',
}

export default function NetWorth() {
  const { data: breakdown, isLoading: breakdownLoading, refetch } = useQuery({
    queryKey: ['net-worth-breakdown'],
    queryFn: getNetWorthBreakdown,
    refetchOnWindowFocus: false,
  })

  const groupAccountsByType = (accounts: AccountWithBalance[]) => {
    const assets: AccountWithBalance[] = []
    const liabilities: AccountWithBalance[] = []

    accounts.forEach(account => {
      const isLiability = ['credit_card', 'loan', 'mortgage', 'other'].includes(account.account_type)
      if (isLiability) {
        liabilities.push(account)
      } else {
        assets.push(account)
      }
    })

    return { assets, liabilities }
  }

  if (breakdownLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p className="text-gray-500">Loading net worth...</p>
        </div>
      </div>
    )
  }

  const { assets, liabilities } = groupAccountsByType(breakdown?.accounts || [])
  const netWorth = breakdown?.net_worth ?? 0
  const assetsTotal = breakdown?.total_assets ?? 0
  const liabilitiesTotal = breakdown?.total_liabilities ?? 0

  const AccountRow = ({ account }: { account: AccountWithBalance }) => {
    const displayBalance = account.calculated_balance ?? account.current_balance
    return (
      <Link
        to={`/accounts/${account.id}`}
        className="block p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex justify-between items-center">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">{account.name}</span>
              <span className="text-xs text-gray-500">
                {accountTypeLabels[account.account_type] || account.account_type}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-medium text-gray-900">
              {formatCurrency(displayBalance)}
            </span>
            <ChevronRight className="h-4 w-4 text-gray-400" />
          </div>
        </div>
      </Link>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Net Worth</h1>
          <p className="text-sm text-gray-500 mt-1">
            Your total financial position across all accounts
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Hero Section */}
      <div className="bg-white border rounded-lg shadow-sm p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">Total Assets</p>
            <p className={`text-2xl font-bold ${assetsTotal >= 0 ? 'text-green-600' : 'text-gray-900'}`}>
              {formatCurrency(assetsTotal)}
            </p>
          </div>

          <div className="text-center border-x border-gray-200">
            <p className="text-sm text-gray-500 mb-2">Net Worth</p>
            <p className={`text-4xl font-bold ${netWorth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(netWorth)}
            </p>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">Total Liabilities</p>
            <p className={`text-2xl font-bold ${liabilitiesTotal > 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(liabilitiesTotal)}
            </p>
          </div>
        </div>
      </div>

      <NetWorthChart />

      {/* Assets Section */}
      <div className="bg-white border rounded-lg shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-green-600" />
            <h2 className="text-lg font-semibold">Assets</h2>
            <span className="text-sm text-gray-500 ml-2">
              {formatCurrency(assetsTotal)}
            </span>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {assets.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-500">
              No assets configured
            </div>
          ) : (
            assets.map((account) => (
              <AccountRow key={account.id} account={account} />
            ))
          )}
        </div>
      </div>

      {/* Liabilities Section */}
      <div className="bg-white border rounded-lg shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-600" />
            <h2 className="text-lg font-semibold">Liabilities</h2>
            <span className="text-sm text-gray-500 ml-2">
              {formatCurrency(liabilitiesTotal)}
            </span>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {liabilities.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-500">
              No liabilities configured
            </div>
          ) : (
            liabilities.map((account) => (
              <AccountRow key={account.id} account={account} />
            ))
          )}
        </div>
      </div>

      {!breakdown?.accounts || breakdown.accounts.length === 0 ? (
        <div className="bg-white border rounded-lg shadow-sm p-6 text-center">
          <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Add your first account</h3>
          <p className="text-gray-500 mb-4">
            Create an account to start tracking your net worth
          </p>
          <Link to="/accounts">
            <Button>Create Account</Button>
          </Link>
        </div>
      ) : null}
    </div>
  )
}
