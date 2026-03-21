import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getAccounts } from '@/lib/api'
import { formatCurrency } from '@/lib/formatters'
import { Plus, ChevronRight } from 'lucide-react'
import CreateAccountModal from '@/components/accounts/CreateAccountModal'
import type { Account } from '@/types'

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

export default function Accounts() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const accounts = data?.items || []

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
        <div className="text-sm text-gray-400 mb-4">Create your first account to get started</div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          Create Account
        </button>
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

  const groupedAccounts = accounts.reduce(
    (groups, account) => {
      const typeGroup = groups[account.account_type] || []
      typeGroup.push(account)
      groups[account.account_type] = typeGroup
      return groups
    },
    {} as Record<string, Account[]>
  )

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
                const displayBalance = account.calculated_balance ?? account.current_balance
                return (
                  <Link
                    key={account.id}
                    to={`/accounts/${account.id}`}
                    className="block p-6 hover:bg-gray-50 transition-colors"
                  >
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
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-2xl font-bold text-gray-900">
                          {formatCurrency(displayBalance)}
                        </div>
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </div>

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
