import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, updateAlert, markAllAlertsRead } from '@/lib/api'
import { Link } from 'react-router-dom'

const SEVERITY_ICONS: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚡',
  attention: '⚠️',
}

export default function AlertBell() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: alertsData } = useQuery({
    queryKey: ['alerts', { limit: 5 }],
    queryFn: () => getAlerts({ limit: 5, is_dismissed: false }),
    refetchInterval: 30000,
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => updateAlert(id, { is_read: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: markAllAlertsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = alertsData?.unread_count || 0
  const alerts = alertsData?.items || []

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full"
      >
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
          <div className="p-3 border-b flex justify-between items-center">
            <span className="font-semibold">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllReadMutation.mutate()}
                className="text-xs text-blue-600 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No notifications
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 ${
                    !alert.is_read ? 'bg-blue-50/50' : ''
                  }`}
                  onClick={() => {
                    if (!alert.is_read) {
                      markReadMutation.mutate(alert.id)
                    }
                  }}
                >
                  <div className="flex gap-2">
                    <span>{SEVERITY_ICONS[alert.severity]}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {alert.title}
                      </div>
                      <div className="text-xs text-gray-600 line-clamp-2">
                        {alert.description}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(alert.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    {!alert.is_read && (
                      <span className="h-2 w-2 bg-blue-500 rounded-full flex-shrink-0 mt-1" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-2 border-t">
            <Link
              to="/insights"
              className="block text-center text-sm text-blue-600 hover:underline"
              onClick={() => setIsOpen(false)}
            >
              View all alerts →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
