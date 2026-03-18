import React, { useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, ChevronDown, ChevronRight, Info, XCircle } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAccount } from '@/contexts/AccountContext'
import { useDashboardData } from '../hooks/useDashboardData'

type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

const severityConfig: Record<AlertSeverity, { container: string; badge: string; text: string; icon: typeof AlertTriangle }> = {
  critical: {
    container: 'border-red-200 bg-red-50',
    badge: 'border-red-200 bg-red-100 text-red-800',
    text: 'text-red-900',
    icon: XCircle,
  },
  high: {
    container: 'border-red-200 bg-red-50',
    badge: 'border-red-200 bg-red-100 text-red-800',
    text: 'text-red-900',
    icon: AlertTriangle,
  },
  medium: {
    container: 'border-amber-200 bg-amber-50',
    badge: 'border-amber-200 bg-amber-100 text-amber-800',
    text: 'text-amber-900',
    icon: AlertTriangle,
  },
  low: {
    container: 'border-slate-200 bg-slate-50',
    badge: 'border-slate-200 bg-slate-100 text-slate-700',
    text: 'text-slate-900',
    icon: Info,
  },
  info: {
    container: 'border-blue-200 bg-blue-50',
    badge: 'border-blue-200 bg-blue-100 text-blue-800',
    text: 'text-blue-900',
    icon: Info,
  },
}

const formatTimestamp = (timestamp: string) =>
  new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(timestamp))

const AlertRow: React.FC<{
  alert: {
    id: string
    title?: string
    message: string
    severity: AlertSeverity
    timestamp: string
    details?: string
  }
}> = ({ alert }) => {
  const [expanded, setExpanded] = useState(false)
  const config = severityConfig[alert.severity] ?? severityConfig.info
  const Icon = config.icon

  return (
    <div className={`rounded-xl border p-4 ${config.container}`}>
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-background/80 p-2">
          <Icon className={`h-4 w-4 ${config.text}`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <Badge variant="outline" className={config.badge}>
              {alert.severity.toUpperCase()}
            </Badge>
            <span className="text-xs text-muted-foreground">{formatTimestamp(alert.timestamp)}</span>
          </div>
          <h4 className={`mb-1 text-sm font-semibold ${config.text}`}>
            {alert.title || alert.message}
          </h4>
          <p className="text-sm text-muted-foreground">{alert.message}</p>
          {alert.details && expanded && (
            <div className="mt-3 rounded-lg border border-border bg-background/80 p-3 text-sm text-muted-foreground">
              {alert.details}
            </div>
          )}
        </div>
        {alert.details && (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="rounded-md p-2 text-muted-foreground hover:bg-background hover:text-foreground"
            aria-label={expanded ? 'Collapse details' : 'Expand details'}
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

export const AlertsSummary: React.FC = () => {
  const { alerts, isLoading } = useDashboardData()
  const { selectedAccount } = useAccount()
  const visibleAlerts = selectedAccount
    ? alerts.filter(alert => !(alert.title === 'Paper Account' && alert.message.includes('no account was explicitly selected')))
    : alerts

  if (isLoading) {
    return (
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3 text-xl font-bold">
            <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
              <Bell className="h-6 w-6" />
            </div>
            <span className="font-serif text-card-foreground">Active Alerts</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="h-20 animate-pulse rounded-xl bg-muted" />
            <div className="h-16 animate-pulse rounded-xl bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center justify-between text-xl font-bold">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
              <Bell className="h-6 w-6" />
            </div>
            <span className="font-serif text-card-foreground">Active Alerts</span>
          </div>
          {visibleAlerts.length > 0 && (
            <Badge variant="outline" className="px-3 py-1.5 text-sm font-semibold">
              {visibleAlerts.length} active
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {visibleAlerts.length === 0 ? (
          <div className="py-16 text-center">
            <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
              <CheckCircle className="h-10 w-10 text-emerald-700" />
            </div>
            <div className="mb-2 text-lg font-semibold text-foreground">All Clear</div>
            <div className="text-sm leading-relaxed text-muted-foreground">No active alerts at this time</div>
          </div>
        ) : (
          <div className="flex max-h-80 flex-col gap-4 overflow-y-auto">
            {visibleAlerts.map((alert) => (
              <AlertRow key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AlertsSummary
