import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, updateAlert, deleteAlert, getAlertSettings, updateAlertSettings } from '@/lib/api'
import { Button } from '@/components/ui/button'

const SEVERITY_STYLES: Record<string, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  attention: 'bg-red-50 border-red-200 text-red-800',
}

const SEVERITY_LABELS: Record<string, string> = {
  info: 'ℹ️ INFO',
  warning: '⚡ WARNING',
  attention: '⚠️ ATTENTION',
}

const TYPE_LABELS: Record<string, string> = {
  large_purchase: 'Large Purchase',
  price_increase: 'Price Increase',
  new_recurring: 'New Subscription',
  unusual_merchant: 'New Merchant',
  annual_charge: 'Annual Charge',
}

export default function Insights() {
  const queryClient = useQueryClient()
  const [showDismissed, setShowDismissed] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts', { is_dismissed: showDismissed ? undefined : false }],
    queryFn: () => getAlerts({
      is_dismissed: showDismissed ? undefined : false,
      limit: 100
    }),
  })

  const { data: settings } = useQuery({
    queryKey: ['alert-settings'],
    queryFn: getAlertSettings,
  })

  const dismissMutation = useMutation({
    mutationFn: (id: string) => updateAlert(id, { is_dismissed: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const updateSettingsMutation = useMutation({
    mutationFn: updateAlertSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-settings'] })
    },
  })

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  const alerts = alertsData?.items || []
  const unreadCount = alertsData?.unread_count || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Insights & Alerts</h1>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500">{unreadCount} unread</p>
          )}
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showDismissed}
              onChange={(e) => setShowDismissed(e.target.checked)}
              className="rounded"
            />
            Show dismissed
          </label>
          <Button
            variant="outline"
            onClick={() => setShowSettings(!showSettings)}
          >
            ⚙️ Settings
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && settings && (
        <div className="bg-gray-50 border rounded-lg p-4 space-y-4">
          <h2 className="font-semibold">Alert Settings</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Large Purchase Multiplier
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                className="border rounded px-3 py-2 w-full"
                value={settings.large_purchase_multiplier}
                onChange={(e) => updateSettingsMutation.mutate({
                  large_purchase_multiplier: parseFloat(e.target.value)
                })}
              />
              <p className="text-xs text-gray-500 mt-1">
                Alert when purchase exceeds Nx category average
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                New Merchant Threshold
              </label>
              <input
                type="number"
                step="50"
                min="0"
                className="border rounded px-3 py-2 w-full"
                value={settings.unusual_merchant_threshold}
                onChange={(e) => updateSettingsMutation.mutate({
                  unusual_merchant_threshold: parseFloat(e.target.value)
                })}
              />
              <p className="text-xs text-gray-500 mt-1">
                Alert for first-time merchants over this amount
              </p>
            </div>
          </div>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings.alerts_enabled}
              onChange={(e) => updateSettingsMutation.mutate({
                alerts_enabled: e.target.checked
              })}
              className="rounded"
            />
            <span className="text-sm">Enable alerts</span>
          </label>
        </div>
      )}

      {/* Alerts List */}
      <div className="space-y-4">
        {alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-4xl mb-2">🎉</p>
            <p>No alerts! Everything looks good.</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-4 ${SEVERITY_STYLES[alert.severity]} ${
                alert.is_dismissed ? 'opacity-50' : ''
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs font-medium mb-1">
                    {SEVERITY_LABELS[alert.severity]}
                  </div>
                  <div className="font-semibold">{alert.title}</div>
                  <div className="text-sm mt-1">{alert.description}</div>
                  <div className="text-xs mt-2 opacity-75">
                    {TYPE_LABELS[alert.type]} • {new Date(alert.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {!alert.is_dismissed && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => dismissMutation.mutate(alert.id)}
                    >
                      Dismiss
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (confirm('Delete this alert permanently?')) {
                        deleteMutation.mutate(alert.id)
                      }
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
