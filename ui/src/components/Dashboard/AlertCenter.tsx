import { useAlerts } from '@/hooks/useAlerts'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'

export function AlertCenter() {
  const { alerts, isLoading, handleAction, isHandlingAction } = useAlerts()

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
        <h3 className="text-lg font-semibold text-gray-900">Active Alerts</h3>
        <div className="text-sm text-gray-600">Loading alerts...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
      <h3 className="text-lg font-semibold text-gray-900">Active Alerts</h3>

      {alerts.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500">
          No active alerts
        </div>
      ) : (
        <div className="flex flex-col gap-3 max-h-96 overflow-y-auto">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3 border rounded ${
                alert.severity === 'critical'
                  ? 'border-red-200 bg-red-50'
                  : alert.severity === 'high'
                    ? 'border-orange-200 bg-orange-50'
                    : alert.severity === 'medium'
                      ? 'border-yellow-200 bg-yellow-50'
                      : 'border-blue-200 bg-blue-50'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`px-2 py-0.5 text-xs rounded ${
                      alert.severity === 'critical'
                        ? 'bg-red-100 text-red-900'
                        : alert.severity === 'high'
                          ? 'bg-orange-100 text-orange-900'
                          : alert.severity === 'medium'
                            ? 'bg-yellow-100 text-yellow-900'
                            : 'bg-blue-100 text-blue-900'
                    }`}
                  >
                    {alert.severity.toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-gray-900">{alert.title}</span>
                </div>
                <span className="text-xs text-gray-500">
                  {formatDateTime(alert.timestamp)}
                </span>
              </div>

              <div className="text-sm text-gray-700 mb-3">{alert.message}</div>

              {alert.symbol && (
                <div className="text-xs text-gray-600 mb-2">
                  Symbol: <span className="font-medium">{alert.symbol}</span>
                </div>
              )}

              {alert.actionable && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction({ alertId: alert.id, action: 'acknowledge' })}
                    disabled={isHandlingAction}
                  >
                    Acknowledge
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
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