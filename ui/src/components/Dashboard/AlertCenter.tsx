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
      <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-red-50/70 backdrop-blur-sm ring-1 ring-red-100/50 animate-scale-in">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl flex items-center gap-3 font-bold">
            <div className="p-3 bg-gradient-to-br from-red-100 to-red-200 rounded-xl shadow-sm">
              <Bell className="w-6 h-6 text-red-700" />
            </div>
            <span className="bg-gradient-to-r from-red-700 to-red-600 bg-clip-text text-transparent">
              Active Alerts
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="h-20 bg-gradient-to-r from-gray-100 to-gray-200 animate-shimmer rounded-xl" />
            <div className="h-16 bg-gradient-to-r from-gray-100 to-gray-200 animate-shimmer rounded-xl" />
            <div className="h-24 bg-gradient-to-r from-gray-100 to-gray-200 animate-shimmer rounded-xl" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-red-50/70 backdrop-blur-sm hover:shadow-professional-hover transition-all duration-300 ring-1 ring-red-100/50 animate-slide-in-up">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center justify-between font-bold">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-red-100 to-red-200 rounded-xl shadow-sm">
              <Bell className="w-6 h-6 text-red-700" />
            </div>
            <span className="bg-gradient-to-r from-red-700 to-red-600 bg-clip-text text-transparent">
              Active Alerts
            </span>
          </div>
          {alerts.length > 0 && (
            <Badge variant="destructive" className="text-sm font-bold px-3 py-1.5 bg-gradient-to-r from-red-500 to-red-600 border-0 shadow-sm">
              {alerts.length} active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-green-100 to-green-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
              <CheckCircle className="w-10 h-10 text-green-700" />
            </div>
            <div className="text-lg font-bold text-gray-800 mb-2">All Clear</div>
            <div className="text-sm text-gray-600 leading-relaxed">No active alerts at this time</div>
          </div>
        ) : (
          <div className="flex flex-col gap-4 max-h-80 overflow-y-auto">
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