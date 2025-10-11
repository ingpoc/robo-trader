import { useAlerts } from '@/hooks/useAlerts'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'

export function AlertCenter() {
  const { alerts, isLoading, handleAction, isHandlingAction } = useAlerts()

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 p-4 bg-white border border-gray-200 card-shadow">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Active Alerts</div>
        <div className="h-16 bg-gray-100 skeleton-shimmer" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-4 bg-white border border-gray-200 card-shadow">
      <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Active Alerts</div>

      {alerts.length === 0 ? (
        <div className="py-8 text-center text-13 text-gray-400">
          No alerts
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="p-3 border border-gray-200 bg-white hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`text-11 font-medium uppercase tracking-wider ${
                    alert.severity === 'critical'
                      ? 'text-gray-900 font-semibold'
                      : alert.severity === 'high'
                        ? 'text-gray-700'
                        : alert.severity === 'medium'
                          ? 'text-gray-600'
                          : 'text-gray-500'
                  }`}
                >
                  {alert.severity}
                </div>
                <div className="text-sm font-medium text-gray-900">{alert.title}</div>
                <div className="ml-auto text-11 text-gray-500">
                  {formatDateTime(alert.timestamp)}
                </div>
              </div>

              <div className="text-13 text-gray-700 leading-relaxed">{alert.message}</div>

              {alert.symbol && (
                <div className="text-11 text-gray-500 mt-1 uppercase tracking-wider">
                  {alert.symbol}
                </div>
              )}

              {alert.actionable && (
                <div className="flex gap-2 mt-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAction({ alertId: alert.id, action: 'acknowledge' })}
                    disabled={isHandlingAction}
                  >
                    Acknowledge
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAction({ alertId: alert.id, action: 'dismiss' })}
                    disabled={isHandlingAction}
                  >
                    Dismiss
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}