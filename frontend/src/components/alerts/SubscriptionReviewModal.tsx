import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { triggerSubscriptionReview, type SubscriptionReviewResponse, type SubscriptionInsight } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { formatCurrency } from '@/lib/formatters'

interface Props {
  isOpen: boolean
  onClose: () => void
}

const INSIGHT_ICONS: Record<string, string> = {
  unused: '💤',
  price_increase: '📈',
  high_cost: '💸',
  annual_upcoming: '📅',
  duplicate: '👯',
}

const INSIGHT_COLORS: Record<string, string> = {
  unused: 'bg-yellow-50 border-yellow-200',
  price_increase: 'bg-red-50 border-red-200',
  high_cost: 'bg-orange-50 border-orange-200',
  annual_upcoming: 'bg-blue-50 border-blue-200',
  duplicate: 'bg-purple-50 border-purple-200',
}

export default function SubscriptionReviewModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient()
  const [reviewData, setReviewData] = useState<SubscriptionReviewResponse | null>(null)

  const reviewMutation = useMutation({
    mutationFn: triggerSubscriptionReview,
    onSuccess: (data) => {
      setReviewData(data)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-bold">Subscription Review</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {!reviewData && !reviewMutation.isPending && (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">
                Run an AI-powered review of your subscriptions to find savings opportunities.
              </p>
              <Button onClick={() => reviewMutation.mutate()}>
                🔍 Start Review
              </Button>
            </div>
          )}

          {reviewMutation.isPending && (
            <div className="text-center py-8">
              <p className="text-gray-600">Analyzing your subscriptions...</p>
            </div>
          )}

          {reviewMutation.error && (
            <div className="text-center py-8 text-red-600">
              Error running review. Please try again.
            </div>
          )}

          {reviewData && (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold">{reviewData.subscription_count}</div>
                  <div className="text-sm text-gray-500">Subscriptions</div>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold text-red-600">
                    {formatCurrency(reviewData.total_monthly_cost)}
                  </div>
                  <div className="text-sm text-gray-500">Monthly</div>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <div className="text-2xl font-bold text-red-600">
                    {formatCurrency(reviewData.total_yearly_cost)}
                  </div>
                  <div className="text-sm text-gray-500">Yearly</div>
                </div>
              </div>

              {/* AI Summary */}
              <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <p className="text-sm">{reviewData.summary}</p>
              </div>

              {/* Insights */}
              {reviewData.insights.length > 0 ? (
                <div className="space-y-3">
                  <h3 className="font-semibold">Recommendations</h3>
                  {reviewData.insights.map((insight, i) => (
                    <div
                      key={i}
                      className={`border rounded p-3 ${INSIGHT_COLORS[insight.type] || 'bg-gray-50'}`}
                    >
                      <div className="flex gap-2 items-start">
                        <span className="text-xl">{INSIGHT_ICONS[insight.type] || '💡'}</span>
                        <div className="flex-1">
                          <div className="font-medium">
                            {insight.merchant} - {formatCurrency(insight.amount)}/{insight.frequency}
                          </div>
                          <div className="text-sm text-gray-700 mt-1">{insight.insight}</div>
                          <div className="text-sm font-medium text-gray-900 mt-2">
                            💡 {insight.recommendation}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-500">
                  🎉 No issues found! Your subscriptions look healthy.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex justify-end gap-2">
          {reviewData && (
            <Button variant="outline" onClick={() => setReviewData(null)}>
              Run Again
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
