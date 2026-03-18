import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'
import { ChevronDown, ChevronRight, AlertTriangle, Info, XCircle, CheckCircle } from 'lucide-react'

interface AlertItemProps {
  alert: {
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
  onAction: (params: { alertId: string, action: string }) => void
  isHandlingAction: boolean
}

const severityConfig = {
  critical: {
    bgColor: 'bg-red-50 border-red-200',
    badgeColor: 'bg-red-100 text-red-800 border-red-200',
    textColor: 'text-red-900',
    icon: XCircle,
    iconColor: 'text-red-600'
  },
  high: {
    bgColor: 'bg-red-50 border-red-200',
    badgeColor: 'bg-red-100 text-red-800 border-red-200',
    textColor: 'text-red-900',
    icon: AlertTriangle,
    iconColor: 'text-red-600'
  },
  medium: {
    bgColor: 'bg-amber-50 border-amber-200',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
    textColor: 'text-amber-900',
    icon: AlertTriangle,
    iconColor: 'text-amber-600'
  },
  low: {
    bgColor: 'bg-slate-50 border-slate-200',
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
    textColor: 'text-slate-900',
    icon: Info,
    iconColor: 'text-slate-600'
  },
  info: {
    bgColor: 'bg-blue-50 border-blue-200',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
    textColor: 'text-blue-900',
    icon: Info,
    iconColor: 'text-blue-600'
  }
}

export function AlertItem({ alert, onAction, isHandlingAction }: AlertItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const config = severityConfig[alert.severity] || severityConfig.info
  const Icon = config.icon

  const handleAction = (action: string) => {
    onAction({ alertId: alert.id, action })
  }

  // Provide default title if not present
  const alertTitle = alert.title || alert.message.substring(0, 50) + (alert.message.length > 50 ? '...' : '')

  return (
    <div className={`group rounded-xl border p-4 transition-shadow duration-200 hover:shadow-sm ${config.bgColor}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          <div className={`p-2 rounded-lg ${config.bgColor.replace('border-', 'bg-').replace('-200', '-100')}`}>
            <Icon className={`w-4 h-4 ${config.iconColor}`} />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${config.badgeColor} shadow-sm`}>
              {alert.severity.toUpperCase()}
            </span>
            {alert.category && (
              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-warmgray-100 text-warmgray-700 border border-warmgray-200">
                {alert.category}
              </span>
            )}
            <div className="ml-auto text-xs text-warmgray-500 font-medium">
              {formatDateTime(alert.timestamp)}
            </div>
          </div>

          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h4 className={`text-sm font-bold ${config.textColor} mb-2 leading-tight`}>
                {alertTitle}
              </h4>
              <p className="mb-2 text-sm leading-relaxed text-muted-foreground">
                {alert.message}
              </p>
              {alert.symbol && (
                <div className="inline-flex items-center rounded-md border bg-background px-2 py-1 text-xs font-semibold text-foreground">
                  {alert.symbol}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2 flex-shrink-0">
              {alert.details && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                  aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </Button>
              )}

              {alert.actionable && (
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAction('acknowledge')}
                    disabled={isHandlingAction}
                    className="text-green-600 hover:text-green-700 hover:bg-green-50 px-3 py-2 rounded-lg transition-colors"
                    title="Acknowledge alert"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAction('dismiss')}
                    disabled={isHandlingAction}
                    className="rounded-lg px-3 py-2 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                    title="Dismiss alert"
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </div>

          {isExpanded && alert.details && (
            <div className="mt-4 rounded-lg border border-border/60 bg-background/80 p-3 pt-4">
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                {alert.details}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
