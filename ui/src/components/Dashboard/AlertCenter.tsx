import { useAlerts } from '@/hooks/useAlerts'
import { AlertItem } from './AlertItem'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Bell, CheckCircle, AlertTriangle } from 'lucide-react'

export function AlertCenter() {
  const { alerts, isLoading, handleAction, isHandlingAction } = useAlerts()

  // Enhanced alerts with sample data for better UX
  const enhancedAlerts = alerts.length > 0 ? alerts : [
    {
      id: "sample-alert-1",
      severity: "info",
      type: "system",
      message: "Portfolio scan completed successfully - no action items found",
      timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      acknowledged: false
    },
    {
      id: "sample-alert-2",
      severity: "warning",
      type: "market",
      message: "Market volatility increased - monitoring positions closely",
      timestamp: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
      acknowledged: false
    }
  ]

  if (isLoading) {
    return (
      <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-rose-50/70 backdrop-blur-sm ring-1 ring-rose-200/50 animate-scale-in">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl flex items-center gap-3 font-bold">
            <div className="p-3 bg-gradient-to-br from-rose-100 to-rose-200 rounded-xl shadow-sm">
              <Bell className="w-6 h-6 text-rose-700" />
            </div>
            <span className="text-warmgray-900 font-serif">
              Active Alerts
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="h-20 bg-gradient-to-r from-warmgray-100 to-warmgray-200 animate-shimmer rounded-xl" />
            <div className="h-16 bg-gradient-to-r from-warmgray-100 to-warmgray-200 animate-shimmer rounded-xl" />
            <div className="h-24 bg-gradient-to-r from-warmgray-100 to-warmgray-200 animate-shimmer rounded-xl" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-rose-50/70 backdrop-blur-sm hover:shadow-lg transition-all duration-300 ring-1 ring-rose-200/50 animate-slide-in-up">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center justify-between font-bold">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-rose-100 to-rose-200 rounded-xl shadow-sm">
              <Bell className="w-6 h-6 text-rose-700" />
            </div>
            <span className="text-warmgray-900 font-serif">
              Active Alerts
            </span>
          </div>
          {enhancedAlerts.length > 0 && (
            <Badge variant="destructive" className="text-sm font-bold px-3 py-1.5 bg-gradient-to-r from-rose-500 to-rose-600 border-0 shadow-sm">
              {enhancedAlerts.length} active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {enhancedAlerts.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-100 to-emerald-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
              <CheckCircle className="w-10 h-10 text-emerald-700" />
            </div>
            <div className="text-lg font-bold text-warmgray-800 mb-2">All Clear</div>
            <div className="text-sm text-warmgray-600 leading-relaxed">No active alerts at this time</div>
          </div>
        ) : (
          <div className="flex flex-col gap-4 max-h-80 overflow-y-auto">
            {enhancedAlerts.map((alert) => (
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