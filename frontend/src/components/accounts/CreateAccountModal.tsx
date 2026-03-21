import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAccount } from '@/lib/api'
import type { AccountType } from '@/types'
import { X, Save } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

interface CreateAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const ACCOUNT_TYPE_OPTIONS = [
  { value: 'checking', label: 'Checking Account' },
  { value: 'savings', label: 'Savings Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'investment', label: 'Investment Account' },
  { value: 'loan', label: 'Loan' },
  { value: 'mortgage', label: 'Mortgage' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
]

function CreateAccountModal({ isOpen, onClose, onSuccess }: CreateAccountModalProps) {
  const [name, setName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('checking')
  const [startingBalance, setStartingBalance] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (data: { name: string; account_type: AccountType; starting_balance?: number }) =>
      createAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      onSuccess()
      resetForm()
    },
  })

  const resetForm = () => {
    setName('')
    setAccountType('checking')
    setStartingBalance('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    const data: { name: string; account_type: AccountType; starting_balance?: number } = {
      name: name.trim(),
      account_type: accountType,
    }

    const bal = parseFloat(startingBalance)
    if (!isNaN(bal)) {
      data.starting_balance = bal
    }

    mutation.mutate(data)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Create Account</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <Label htmlFor="account-name">Account Name *</Label>
            <Input
              id="account-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Main Checking"
              className="mt-1.5"
              required
            />
          </div>

          <div>
            <Label htmlFor="account-type">Account Type *</Label>
            <select
              id="account-type"
              value={accountType}
              onChange={(e) => setAccountType(e.target.value as AccountType)}
              className="w-full mt-1.5 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {ACCOUNT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="starting-balance">Starting Balance (optional)</Label>
            <div className="relative mt-1.5">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
              <input
                id="starting-balance"
                type="number"
                step="0.01"
                value={startingBalance}
                onChange={(e) => setStartingBalance(e.target.value)}
                placeholder="0.00"
                className="w-full pl-8 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Your balance before any imported transactions. Leave blank for $0.
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
              disabled={mutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || !name.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
            >
              <Save className="h-4 w-4 inline mr-2" />
              {mutation.isPending ? 'Creating...' : 'Create Account'}
            </button>
          </div>
        </form>

        {mutation.isError && (
          <div className="mx-6 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">Failed to create account. Please try again.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default CreateAccountModal
