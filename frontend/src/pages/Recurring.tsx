import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRecurringGroups,
  detectRecurring,
  applyDetection,
  updateRecurringGroup,
  deleteRecurringGroup,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatDate } from '@/lib/formatters'

const FREQUENCY_LABELS: Record<string, string> = {
  weekly: 'Weekly',
  biweekly: 'Every 2 weeks',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
}

export default function Recurring() {
  const queryClient = useQueryClient()
  const [showInactive, setShowInactive] = useState(false)
  const [showDetection, setShowDetection] = useState(false)

  const { data: groups, isLoading } = useQuery({
    queryKey: ['recurring-groups', showInactive],
    queryFn: () => getRecurringGroups(showInactive),
  })

  const detectMutation = useMutation({
    mutationFn: detectRecurring,
    onSuccess: () => {
      setShowDetection(true)
    },
  })

  const applyMutation = useMutation({
    mutationFn: (index: number) => applyDetection(index),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
      detectMutation.reset()
      setShowDetection(false)
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateRecurringGroup(id, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRecurringGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-groups'] })
    },
  })

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Recurring Charges</h1>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
          <Button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
          >
            {detectMutation.isPending ? 'Detecting...' : '🔍 Detect Recurring'}
          </Button>
        </div>
      </div>

      {/* Detection Results */}
      {showDetection && detectMutation.data && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold">
              Detected {detectMutation.data.total_found} Recurring Pattern(s)
            </h2>
            <Button variant="outline" size="sm" onClick={() => setShowDetection(false)}>
              Dismiss
            </Button>
          </div>

              {detectMutation.data.detected.length === 0 ? (
            <p className="text-sm text-gray-600">No new recurring patterns found.</p>
          ) : (
            <div className="space-y-3">
              {detectMutation.data.detected.map((detection: any, index: number) => (
                <div
                  key={index}
                  className="bg-white rounded p-3 flex justify-between items-center"
                >
                  <div>
                    <div className="font-medium">{detection.suggested_name}</div>
                    <div className="text-sm text-gray-500">
                      {formatCurrency(detection.average_amount)} • {FREQUENCY_LABELS[detection.frequency]}
                      • {detection.transaction_ids.length} transactions
                      • {Math.round(detection.confidence * 100)}% confidence
                    </div>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyMutation.mutate(index)}
                    disabled={applyMutation.isPending}
                  >
                    Add
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary */}
      {groups && groups.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">{groups.filter(g => g.is_active).length}</div>
              <div className="text-sm text-gray-500">Active Subscriptions</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {formatCurrency(
                  groups
                    .filter(g => g.is_active && g.frequency === 'monthly')
                    .reduce((sum, g) => sum + (g.expected_amount || 0), 0)
                )}
              </div>
              <div className="text-sm text-gray-500">Monthly Total</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {formatCurrency(
                  groups
                    .filter(g => g.is_active)
                    .reduce((sum, g) => {
                      const amount = g.expected_amount || 0
                      switch (g.frequency) {
                        case 'weekly': return sum + amount * 52
                        case 'biweekly': return sum + amount * 26
                        case 'monthly': return sum + amount * 12
                        case 'quarterly': return sum + amount * 4
                        case 'yearly': return sum + amount
                        default: return sum + amount * 12
                      }
                    }, 0)
                )}
              </div>
              <div className="text-sm text-gray-500">Yearly Total</div>
            </div>
          </div>
        </div>
      )}

      {/* Recurring Groups List */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Name</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Amount</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Frequency</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Last Seen</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Next Expected</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Transactions</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {groups?.map((group) => (
              <tr
                key={group.id}
                className={`border-t ${!group.is_active ? 'opacity-50 bg-gray-50' : ''}`}
              >
                <td className="px-4 py-3">
                  <div className="font-medium">{group.name}</div>
                  <div className="text-xs text-gray-500">{group.merchant_pattern}</div>
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.expected_amount ? formatCurrency(group.expected_amount) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {FREQUENCY_LABELS[group.frequency] || group.frequency}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.last_seen_date ? formatDate(group.last_seen_date) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.next_expected_date ? formatDate(group.next_expected_date) : '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {group.transaction_count || 0}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex gap-1 justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        toggleActiveMutation.mutate({
                          id: group.id,
                          isActive: !group.is_active,
                        })
                      }
                    >
                      {group.is_active ? 'Pause' : 'Resume'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (confirm('Delete this recurring group? Transactions will be unlinked.')) {
                          deleteMutation.mutate(group.id)
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {(!groups || groups.length === 0) && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  No recurring charges yet. Click "Detect Recurring" to find patterns in your transactions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
