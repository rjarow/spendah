import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAccount, getTransactions, getCategories, updateTransaction, updateAccount } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { Transaction, Category } from '@/types'
import { ArrowLeft, ChevronLeft, ChevronRight, Pencil } from 'lucide-react'

interface FlatCategory extends Omit<Category, 'parent_id'> {
  parent_id: string | null | undefined
}

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

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingStartingBalance, setEditingStartingBalance] = useState(false)
  const [startingBalanceValue, setStartingBalanceValue] = useState('')

  const { data: account, isLoading: accountLoading } = useQuery({
    queryKey: ['account', id],
    queryFn: () => getAccount(id!),
    enabled: !!id,
  })

  const { data: transactions, isLoading: txnLoading } = useQuery({
    queryKey: ['transactions', { account_id: id, page }],
    queryFn: () => getTransactions({ account_id: id, page, per_page: 50 }),
    enabled: !!id,
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  })

  const updateMutation = useMutation({
    mutationFn: ({ txnId, data }: { txnId: string; data: Partial<Transaction> }) =>
      updateTransaction(txnId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setEditingId(null)
    },
  })

  const updateBalanceMutation = useMutation({
    mutationFn: (balance: number) => updateAccount(id!, { current_balance: balance }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account', id] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setEditingStartingBalance(false)
    },
  })

  const flatCategories: FlatCategory[] = categories?.items?.flatMap((cat: Category): FlatCategory[] => [
    cat,
    ...(cat.children || [])
  ]) || []

  if (accountLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading account...</div>
  }

  if (!account) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-gray-500 mb-4">Account not found</p>
        <Link to="/accounts">
          <Button variant="outline">Back to Accounts</Button>
        </Link>
      </div>
    )
  }

  const displayBalance = account.calculated_balance ?? account.current_balance

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/accounts" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{account.name}</h1>
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
              {accountTypeLabels[account.account_type] || account.account_type}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900">
            {formatCurrency(displayBalance)}
          </div>
          <div className="text-sm text-gray-500">Calculated balance</div>
        </div>
      </div>

      {/* Starting balance (de-emphasized) */}
      <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
        <div>
          <span className="text-sm text-gray-500">Starting balance: </span>
          {editingStartingBalance ? (
            <form
              className="inline-flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                const val = parseFloat(startingBalanceValue)
                if (!isNaN(val)) {
                  updateBalanceMutation.mutate(val)
                }
              }}
            >
              <span className="text-sm text-gray-500">$</span>
              <input
                type="number"
                step="0.01"
                value={startingBalanceValue}
                onChange={(e) => setStartingBalanceValue(e.target.value)}
                className="w-28 px-2 py-1 border rounded text-sm"
                autoFocus
              />
              <Button type="submit" size="sm" disabled={updateBalanceMutation.isPending}>
                Save
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setEditingStartingBalance(false)}
              >
                Cancel
              </Button>
            </form>
          ) : (
            <>
              <span className="text-sm font-medium text-gray-700">
                {formatCurrency(account.current_balance)}
              </span>
              <button
                onClick={() => {
                  setStartingBalanceValue(account.current_balance.toString())
                  setEditingStartingBalance(true)
                }}
                className="ml-2 text-gray-400 hover:text-gray-600"
              >
                <Pencil className="h-3 w-3 inline" />
              </button>
            </>
          )}
        </div>
        <p className="text-xs text-gray-400">
          Your balance before any imported transactions
        </p>
      </div>

      {/* Transactions */}
      <div className="bg-white border rounded-lg shadow-sm">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Transactions</h2>
          <p className="text-sm text-gray-500">
            {transactions?.total || 0} transaction{(transactions?.total || 0) !== 1 ? 's' : ''}
          </p>
        </div>

        {txnLoading ? (
          <div className="p-8 text-center text-gray-500">Loading transactions...</div>
        ) : !transactions?.items?.length ? (
          <div className="p-8 text-center text-gray-500">
            <p className="mb-2">No transactions yet</p>
            <p className="text-sm">Import a CSV to get started</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Merchant</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Category</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.items.map((txn: Transaction) => (
                    <tr key={txn.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">{formatDate(txn.date)}</td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium">
                          {txn.clean_merchant || txn.raw_description}
                        </div>
                        {txn.clean_merchant && txn.clean_merchant !== txn.raw_description && (
                          <div className="text-xs text-gray-500 truncate max-w-xs">
                            {txn.raw_description}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editingId === txn.id ? (
                          <select
                            className="border rounded px-2 py-1 text-sm"
                            defaultValue={txn.category_id || ''}
                            onChange={(e) => {
                              updateMutation.mutate({
                                txnId: txn.id,
                                data: { category_id: e.target.value || null },
                              })
                            }}
                            onBlur={() => setEditingId(null)}
                            autoFocus
                          >
                            <option value="">Uncategorized</option>
                            {flatCategories.map((cat: FlatCategory) => (
                              <option key={cat.id} value={cat.id}>
                                {cat.parent_id ? '  ' : ''}{cat.name}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <button
                            className="text-sm text-left hover:text-blue-600"
                            onClick={() => setEditingId(txn.id)}
                          >
                            {flatCategories.find((c: FlatCategory) => c.id === txn.category_id)?.name || (
                              <span className="text-gray-400">Uncategorized</span>
                            )}
                            {txn.ai_categorized && (
                              <span className="text-xs text-purple-500 ml-1" title="AI categorized">AI</span>
                            )}
                          </button>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${
                        txn.amount < 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {formatCurrency(txn.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t flex justify-between items-center">
              <span className="text-sm text-gray-500">
                Showing {transactions.items.length} of {transactions.total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <span className="px-3 py-1 text-sm text-gray-600">
                  Page {page} of {transactions.pages || 1}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= (transactions.pages || 1)}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
