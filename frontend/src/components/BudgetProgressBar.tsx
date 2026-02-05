import { cn } from "@/lib/utils"

interface BudgetProgressBarProps {
  budgetName: string
  spent: number
  limit: number
  percentUsed: number
  compact?: boolean
}

export function BudgetProgressBar({
  budgetName,
  spent,
  limit,
  percentUsed,
  compact = false
}: BudgetProgressBarProps) {
  const remaining = limit - spent
  const isOverBudget = spent > limit
  const formattedSpent = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(spent)
  const formattedLimit = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(limit)
  const formattedRemaining = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(remaining)

  const getColorClasses = () => {
    if (isOverBudget) {
      return 'bg-red-500'
    }
    if (percentUsed >= 90) {
      return 'bg-red-400'
    }
    if (percentUsed >= 75) {
      return 'bg-yellow-500'
    }
    return 'bg-green-500'
  }

  const getTextColorClass = () => {
    if (isOverBudget) {
      return 'text-red-600'
    }
    if (percentUsed >= 90) {
      return 'text-red-600'
    }
    if (percentUsed >= 75) {
      return 'text-yellow-600'
    }
    return 'text-green-600'
  }

  const progressBarWidth = Math.min(percentUsed, 100)
  const barClass = getColorClasses()
  const textClass = getTextColorClass()

  if (compact) {
    return (
      <div className="space-y-1 w-full">
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium text-gray-900 truncate flex-1 pr-2" title={budgetName}>
            {budgetName}
          </span>
          <span className={cn("text-xs font-semibold", textClass)}>
            {isOverBudget ? `+${formattedRemaining}` : formattedRemaining}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={cn(barClass, "h-full rounded-full transition-all duration-300")}
            style={{ width: `${barClass.includes('red-500') ? Math.min(percentUsed, 100) : progressBarWidth}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2 w-full">
      <div className="flex justify-between items-center">
        <span className="font-semibold text-gray-900">{budgetName}</span>
        <div className="flex items-center gap-2 text-sm">
          {isOverBudget && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              Over budget
            </span>
          )}
          <span className={cn("font-bold", textClass)}>
            {isOverBudget ? `+${formattedRemaining}` : formattedRemaining}
          </span>
          <span className="text-gray-500">of {formattedLimit}</span>
        </div>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={cn(barClass, "h-full rounded-full transition-all duration-300")}
          style={{ width: `${barClass.includes('red-500') ? Math.min(percentUsed, 100) : progressBarWidth}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-600">
        <span>{formattedSpent} spent</span>
        <span>{percentUsed.toFixed(0)}%</span>
      </div>
    </div>
  )
}
