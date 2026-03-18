import { useAlerts } from '@/hooks/useAlerts'
import { AlertItem } from './AlertItem'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Bell, CheckCircle } from 'lucide-react'

type DashboardAlert = {
  id: string
  title?: string
  message: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  timestamp: string
  symbol?: string
  actionable?: boolean
  details?: string
  category?: string
  type?: string
  acknowledged?: boolean
}

interface AlertCenterProps {
  alerts?: DashboardAlert[]
  isLoading?: boolean
}

export function AlertCenter({ alerts: providedAlerts, isLoading: providedLoading = false }: AlertCenterProps = {}) {
  const alertsQuery = useAlerts()
  const alerts = providedAlerts ?? alertsQuery.alerts
  const isLoading = providedAlerts ? providedLoading : alertsQuery.isLoading
  const isHandlingAction = providedAlerts ? false : alertsQuery.isHandlingAction
  const handleAction = providedAlerts
    ? () => undefined
    : alertsQuery.handleAction

  if (isLoading) {
    return (
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl flex items-center gap-3 font-bold">
            <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
              <Bell className="w-6 h-6" />
            </div>
            <span className="font-serif text-card-foreground">
              Active Alerts
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="h-20 rounded-xl bg-muted animate-pulse" />
            <div className="h-16 rounded-xl bg-muted animate-pulse" />
            <div className="h-24 rounded-xl bg-muted animate-pulse" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center justify-between font-bold">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
              <Bell className="w-6 h-6" />
            </div>
            <span className="font-serif text-card-foreground">
              Active Alerts
            </span>
          </div>
          {alerts.length > 0 && (
            <Badge variant="outline" className="px-3 py-1.5 text-sm font-semibold">
              {alerts.length} active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="py-16 text-center">
            <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
              <CheckCircle className="w-10 h-10 text-emerald-700" />
            </div>
            <div className="mb-2 text-lg font-semibold text-foreground">All Clear</div>
            <div className="text-sm leading-relaxed text-muted-foreground">No active alerts at this time</div>
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
