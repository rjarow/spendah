import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAccounts, updateAccountBalance, createAccount } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { X, Check, AlertCircle, Plus } from 'lucide-react'
import CreateAccountModal from '@/components/accounts/CreateAccountModal'

interface UpdateBalanceModalProps {
  account: {
    id: string
    name: string
    current_balance: number
    balance_updated_at: string
  }
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

function UpdateBalanceModal({ account, isOpen, onClose, onSuccess }: UpdateBalanceModalProps) {
  const [balance, setBalance] = useState(account.current_balance.toString())
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (balanceAmount: number) => updateAccountBalance(account.id, balanceAmount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      onSuccess()
    }
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; type: string }) => createAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const balanceAmount = parseFloat(balance)
    if (isNaN(balanceAmount) || balanceAmount < 0) {
      return
    }
    mutation.mutate(balanceAmount)
  }

  if (!isOpen) return null

  const calculateDaysAgo = (dateString: string) => {
    const now = new Date()
    const updated = new Date(dateString)
    const diffTime = Math.abs(now.getTime() - updated.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const daysAgo = calculateDaysAgo(account.balance_updated_at)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Update Balance</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Account Name
            </label>
            <input
              type="text"
              value={account.name}
              disabled
              className="w-full px-3 py-2 border rounded-lg bg-gray-100 cursor-not-allowed"
            />
          </div>

          <div>
            <label htmlFor="balance" className="block text-sm font-medium text-gray-700 mb-2">
              Current Balance
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                $
              </span>
              <input
                id="balance"
                type="number"
                step="0.01"
                min="0"
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
                className="w-full pl-8 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertCircle className="h-4 w-4" />
            <span>Balance updated {daysAgo} day{daysAgo !== 1 ? 's' : ''} ago</span>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
              disabled={mutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || isNaN(parseFloat(balance))}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  Updating...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Check className="h-4 w-4" />
                  Update Balance
                </span>
              )}
            </button>
          </div>
        </form>

        {mutation.isError && (
          <div className="mx-6 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">Failed to update balance. Please try again.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Accounts() {
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState<{
    id: string
    name: string
    current_balance: number
    balance_updated_at: string
  } | null>(null)

  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const accounts = data?.items || []

  const handleUpdateBalance = (account: typeof selectedAccount) => {
    setSelectedAccount(account)
    setIsUpdateModalOpen(true)
  }

  const handleBalanceUpdated = () => {
    setIsUpdateModalOpen(false)
    setSelectedAccount(null)
  }

  const calculateDaysAgo = (dateString: string) => {
    const now = new Date()
    const updated = new Date(dateString)
    const diffTime = Math.abs(now.getTime() - updated.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading accounts...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-600">Failed to load accounts</div>
      </div>
    )
  }

  if (accounts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-gray-500 mb-4">No accounts found</div>
        <div className="text-sm text-gray-400">Create your first account to get started</div>
      </div>
    )
  }

  const groupedAccounts = accounts.reduce(
    (groups, account) => {
      const typeGroup = groups[account.type] || []
      typeGroup.push(account)
      groups[account.type] = typeGroup
      return groups
    },
    {} as Record<string, typeof accounts>
  )

  const typeLabels: Record<string, string> = {
    checking: 'Checking Accounts',
    savings: 'Savings Accounts',
    credit_card: 'Credit Cards',
    investment: 'Investment Accounts',
    loan: 'Loans',
    mortgage: 'Mortgages',
    cash: 'Cash',
    other: 'Other',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Accounts</h1>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          Create Account
        </button>
      </div>

      <div className="space-y-6">
        {Object.entries(groupedAccounts).map(([type, typeAccounts]) => (
          <div key={type} className="bg-white rounded-lg shadow border">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold text-gray-900">
                {typeLabels[type] || type}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {typeAccounts.length} account{typeAccounts.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="divide-y">
              {typeAccounts.map((account) => {
                const daysAgo = calculateDaysAgo(account.balance_updated_at)
                return (
                  <div key={account.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-medium text-gray-900">
                            {account.name}
                          </h3>
                          <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
                            {type}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          Balance updated {daysAgo} day{daysAgo !== 1 ? 's' : ''} ago
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="text-2xl font-bold text-gray-900">
                            {formatCurrency(account.current_balance)}
                          </div>
                        </div>
                        <button
                          onClick={() => handleUpdateBalance(account)}
                          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
                        >
                          Update Balance
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {isUpdateModalOpen && selectedAccount && (
        <UpdateBalanceModal
          account={selectedAccount}
          isOpen={isUpdateModalOpen}
          onClose={handleBalanceUpdated}
          onSuccess={handleBalanceUpdated}
        />
      )}

      {isCreateModalOpen && (
        <CreateAccountModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={() => setIsCreateModalOpen(false)}
        />
      )}
    </div>
  )
}
