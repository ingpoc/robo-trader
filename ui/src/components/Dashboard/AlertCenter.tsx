import { useAlerts } from '@/hooks/useAlerts'
import { AlertItem } from './AlertItem'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export function AlertCenter() {
  const { alerts, isLoading, handleAction, isHandlingAction } = useAlerts()

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 p-4 bg-white border border-gray-200 card-shadow rounded-lg">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Active Alerts</div>
        <div className="flex flex-col gap-3">
          <div className="h-20 bg-gray-100 skeleton-shimmer rounded-lg" />
          <div className="h-16 bg-gray-100 skeleton-shimmer rounded-lg" />
          <div className="h-24 bg-gray-100 skeleton-shimmer rounded-lg" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-3 sm:p-4 bg-white border border-gray-200 card-shadow rounded-lg">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">Active Alerts</div>
        {alerts.length > 0 && (
          <div className="text-xs text-gray-500 hidden sm:block">
            {alerts.length} active
          </div>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="py-8 sm:py-12 text-center">
          <div className="text-gray-400 mb-2">
            <svg className="w-6 h-6 sm:w-8 sm:h-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-xs sm:text-sm text-gray-500">No active alerts</div>
        </div>
      ) : (
        <div className="flex flex-col gap-2 sm:gap-3 max-h-80 sm:max-h-96 overflow-y-auto">
          {alerts.map((alert) => (
            <AlertItem
              key={alert.id}
              alert={alert}
              onAction={handleAction}
              isHandlingAction={isHandlingAction}
            />
          ))}
        </div>
      )}
    </div>
  )
}