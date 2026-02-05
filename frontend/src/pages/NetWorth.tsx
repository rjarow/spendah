import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getNetWorth, getNetWorthBreakdown, updateAccountBalance } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Wallet, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import type { AccountWithBalance } from '@/types'
import NetWorthChart from '@/components/NetWorthChart'

const accountTypeLabels: Record<string, string> = {
  bank: 'Bank',
  credit: 'Credit Card',
  debit: 'Debit Card',
  cash: 'Cash',
  other: 'Other',
}

export default function NetWorth() {
  const queryClient = useQueryClient()
  const [editingBalance, setEditingBalance] = useState<{ accountId: string; currentBalance: number } | null>(null)
  const [showUpdateForm, setShowUpdateForm] = useState<Record<string, boolean>>({})

  const { data: breakdown, isLoading: breakdownLoading, refetch } = useQuery({
    queryKey: ['net-worth-breakdown'],
    queryFn: getNetWorthBreakdown,
    refetchOnWindowFocus: false,
  })

  const updateBalanceMutation = useMutation({
    mutationFn: ({ id, balance }: { id: string; balance: number }) => updateAccountBalance(id, balance),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['net-worth-breakdown'] })
      setEditingBalance(null)
    },
  })

  const handleUpdateBalance = (account: AccountWithBalance) => {
    setEditingBalance({ accountId: account.id, currentBalance: account.current_balance })
    setShowUpdateForm(prev => ({ ...prev, [account.id]: true }))
  }

  const handleSubmitBalance = (e: React.FormEvent, accountId: string) => {
    e.preventDefault()
    if (editingBalance && editingBalance.accountId === accountId) {
      updateBalanceMutation.mutate({ id: accountId, balance: editingBalance.currentBalance })
    }
  }

  const groupAccountsByType = (accounts: AccountWithBalance[]) => {
    const assets: AccountWithBalance[] = []
    const liabilities: AccountWithBalance[] = []

    accounts.forEach(account => {
      const isLiability = account.type === 'credit'
      if (isLiability) {
        liabilities.push(account)
      } else {
        assets.push(account)
      }
    })

    return { assets, liabilities }
  }

  const calculateGroupTotal = (accounts: AccountWithBalance[]) => {
    return accounts.reduce((sum, account) => sum + account.current_balance, 0)
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
  const assetsTotal = calculateGroupTotal(assets)
  const liabilitiesTotal = calculateGroupTotal(liabilities)
  const netWorth = assetsTotal - liabilitiesTotal

  const formatLastUpdated = (updatedAt?: string) => {
    if (!updatedAt) return 'Not updated yet'
    const now = new Date()
    const updated = new Date(updatedAt)
    const diffMs = now.getTime() - updated.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Updated today'
    if (diffDays === 1) return 'Updated yesterday'
    return `Updated ${diffDays} days ago`
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
        <Button onClick={() => refetch()} variant="outline" size="sm" disabled={updateBalanceMutation.isPending}>
          <RefreshCw className={`h-4 w-4 mr-2 ${updateBalanceMutation.isPending ? 'animate-spin' : ''}`} />
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
            {breakdown?.accounts?.[0]?.balance_updated_at && (
              <p className="text-xs text-gray-400 mt-1">
                {formatLastUpdated(breakdown.accounts[0].balance_updated_at)}
              </p>
            )}
          </div>
          
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">Total Liabilities</p>
            <p className={`text-2xl font-bold ${liabilitiesTotal >= 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(Math.abs(liabilitiesTotal))}
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
              <div key={account.id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{account.name}</span>
                      <span className="text-xs text-gray-500">
                        {accountTypeLabels[account.type] || account.type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span>Balance: {formatCurrency(account.current_balance)}</span>
                      {account.balance_updated_at && (
                        <span>{formatLastUpdated(account.balance_updated_at)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {showUpdateForm[account.id] ? (
                      <form onSubmit={(e) => handleSubmitBalance(e, account.id)} className="flex gap-2">
                        <input
                          type="number"
                          step="0.01"
                          value={editingBalance?.currentBalance || account.current_balance}
                          onChange={(e) => setEditingBalance({
                            accountId: account.id,
                            currentBalance: parseFloat(e.target.value)
                          })}
                          className="w-32 px-2 py-1 border rounded text-sm"
                          autoFocus
                        />
                        <Button
                          type="submit"
                          size="sm"
                          disabled={updateBalanceMutation.isPending}
                        >
                          {updateBalanceMutation.isPending ? 'Updating...' : 'Save'}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setShowUpdateForm(prev => ({ ...prev, [account.id]: false }))}
                        >
                          Cancel
                        </Button>
                      </form>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpdateBalance(account)}
                      >
                        Update Balance
                      </Button>
                    )}
                  </div>
                </div>
              </div>
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
              {formatCurrency(Math.abs(liabilitiesTotal))}
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
              <div key={account.id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{account.name}</span>
                      <span className="text-xs text-gray-500">
                        {accountTypeLabels[account.type] || account.type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span className="text-red-600">Balance: {formatCurrency(account.current_balance)}</span>
                      {account.balance_updated_at && (
                        <span>{formatLastUpdated(account.balance_updated_at)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {showUpdateForm[account.id] ? (
                      <form onSubmit={(e) => handleSubmitBalance(e, account.id)} className="flex gap-2">
                        <input
                          type="number"
                          step="0.01"
                          value={editingBalance?.currentBalance || account.current_balance}
                          onChange={(e) => setEditingBalance({
                            accountId: account.id,
                            currentBalance: parseFloat(e.target.value)
                          })}
                          className="w-32 px-2 py-1 border rounded text-sm"
                          autoFocus
                        />
                        <Button
                          type="submit"
                          size="sm"
                          disabled={updateBalanceMutation.isPending}
                        >
                          {updateBalanceMutation.isPending ? 'Updating...' : 'Save'}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setShowUpdateForm(prev => ({ ...prev, [account.id]: false }))}
                        >
                          Cancel
                        </Button>
                      </form>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpdateBalance(account)}
                      >
                        Update Balance
                      </Button>
                    )}
                  </div>
                </div>
              </div>
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
