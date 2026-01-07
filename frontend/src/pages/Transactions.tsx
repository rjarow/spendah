import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTransactions, getCategories, getAccounts, updateTransaction, bulkCategorize } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatDate } from '@/lib/formatters'

export default function Transactions() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)

  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions', page, search, selectedAccount, selectedCategory],
    queryFn: () => getTransactions({
      page,
      per_page: 50,
      search: search || undefined,
      account_id: selectedAccount || undefined,
      category_id: selectedCategory || undefined,
    }),
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
  })

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateTransaction(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setEditingId(null)
    },
  })

  const bulkCategorizeMutation = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) =>
      bulkCategorize(ids, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setSelectedIds(new Set())
    },
  })

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const selectAll = () => {
    if (selectedIds.size === transactions?.items?.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(transactions?.items?.map((t: any) => t.id)))
    }
  }

  const handleBulkCategorize = (categoryId: string) => {
    if (categoryId && selectedIds.size > 0) {
      bulkCategorizeMutation.mutate({
        ids: Array.from(selectedIds),
        categoryId,
      })
    }
  }

  const flatCategories = categories?.items?.flatMap((cat: any) => [
    cat,
    ...(cat.children || [])
  ]) || []

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Transactions</h1>

      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Search..."
          className="border rounded px-3 py-2"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />

        <select
          className="border rounded px-3 py-2"
          value={selectedAccount}
          onChange={(e) => {
            setSelectedAccount(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All Accounts</option>
          {accounts?.items?.map((acc: any) => (
            <option key={acc.id} value={acc.id}>{acc.name}</option>
          ))}
        </select>

        <select
          className="border rounded px-3 py-2"
          value={selectedCategory}
          onChange={(e) => {
            setSelectedCategory(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All Categories</option>
          {flatCategories.map((cat: any) => (
            <option key={cat.id} value={cat.id}>
              {cat.parent_id ? '  ' : ''}{cat.name}
            </option>
          ))}
        </select>
      </div>

      {selectedIds.size > 0 && (
        <div className="flex gap-2 items-center bg-blue-50 p-3 rounded">
          <span className="text-sm">{selectedIds.size} selected</span>
          <select
            className="border rounded px-2 py-1 text-sm"
            defaultValue=""
            onChange={(e) => handleBulkCategorize(e.target.value)}
            disabled={bulkCategorizeMutation.isPending}
          >
            <option value="">Change category...</option>
            {flatCategories.map((cat: any) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          {bulkCategorizeMutation.isPending && (
            <span className="text-sm text-gray-500">Updating...</span>
          )}
          <Button variant="outline" size="sm" onClick={() => setSelectedIds(new Set())}>
            Clear selection
          </Button>
        </div>
      )}

      <div className="border rounded overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds.size === transactions?.items?.length && transactions?.items?.length > 0}
                  onChange={selectAll}
                />
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Merchant</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Category</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {transactions?.items?.map((txn: any) => (
              <tr key={txn.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(txn.id)}
                    onChange={() => toggleSelect(txn.id)}
                  />
                </td>
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
                          id: txn.id,
                          data: { category_id: e.target.value || null }
                        })
                      }}
                      onBlur={() => setEditingId(null)}
                      autoFocus
                    >
                      <option value="">Uncategorized</option>
                      {flatCategories.map((cat: any) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.parent_id ? '  ' : ''}{cat.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <button
                      className="text-sm text-left hover:text-blue-600 flex items-center gap-1"
                      onClick={() => setEditingId(txn.id)}
                    >
                      {flatCategories.find((c: any) => c.id === txn.category_id)?.name ||
                        <span className="text-gray-400">Uncategorized</span>}
                      {txn.ai_categorized && (
                        <span className="text-xs text-purple-500" title="AI categorized">✨</span>
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

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500">
          Showing {transactions?.items?.length || 0} of {transactions?.total || 0}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="px-3 py-2 text-sm">
            Page {page} of {transactions?.pages || 1}
          </span>
          <Button
            variant="outline"
            disabled={page >= (transactions?.pages || 1)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
