import { useAlerts } from '@/hooks/useAlerts'
import { AlertItem } from './AlertItem'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/badge'
import { Bell, CheckCircle, AlertTriangle } from 'lucide-react'

export function AlertCenter() {
  const { alerts, isLoading, handleAction, isHandlingAction } = useAlerts()

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-white to-red-50/50 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Bell className="w-5 h-5 text-red-600" />
            </div>
            Active Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            <div className="h-20 bg-gray-100 animate-shimmer rounded-lg" />
            <div className="h-16 bg-gray-100 animate-shimmer rounded-lg" />
            <div className="h-24 bg-gray-100 animate-shimmer rounded-lg" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-white to-red-50/50 backdrop-blur-sm hover:shadow-xl transition-all duration-300">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Bell className="w-5 h-5 text-red-600" />
            </div>
            Active Alerts
          </div>
          {alerts.length > 0 && (
            <Badge variant="destructive" className="text-xs">
              {alerts.length} active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="py-12 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <div className="text-sm font-medium text-gray-700 mb-1">All Clear</div>
            <div className="text-sm text-gray-500">No active alerts at this time</div>
          </div>
        ) : (
          <div className="flex flex-col gap-3 max-h-80 overflow-y-auto">
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
      </CardContent>
    </Card>
  )
}