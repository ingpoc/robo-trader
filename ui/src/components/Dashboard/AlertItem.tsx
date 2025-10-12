import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'
import { ChevronDown, ChevronRight, AlertTriangle, Info, XCircle, CheckCircle } from 'lucide-react'

interface AlertItemProps {
  alert: {
    id: string
    title: string
    message: string
    severity: 'critical' | 'high' | 'medium' | 'low'
    timestamp: string
    symbol?: string
    actionable?: boolean
    details?: string
    category?: string
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
    bgColor: 'bg-orange-50 border-orange-200',
    badgeColor: 'bg-orange-100 text-orange-800 border-orange-200',
    textColor: 'text-orange-900',
    icon: AlertTriangle,
    iconColor: 'text-orange-600'
  },
  medium: {
    bgColor: 'bg-yellow-50 border-yellow-200',
    badgeColor: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    textColor: 'text-yellow-900',
    icon: AlertTriangle,
    iconColor: 'text-yellow-600'
  },
  low: {
    bgColor: 'bg-blue-50 border-blue-200',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
    textColor: 'text-blue-900',
    icon: Info,
    iconColor: 'text-blue-600'
  }
}

export function AlertItem({ alert, onAction, isHandlingAction }: AlertItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const config = severityConfig[alert.severity]
  const Icon = config.icon

  const handleAction = (action: string) => {
    onAction({ alertId: alert.id, action })
  }

  return (
    <div className={`p-4 border rounded-xl transition-all duration-300 hover:shadow-md ${config.bgColor} group`}>
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
              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
                {alert.category}
              </span>
            )}
            <div className="ml-auto text-xs text-gray-500 font-medium">
              {formatDateTime(alert.timestamp)}
            </div>
          </div>

          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h4 className={`text-sm font-bold ${config.textColor} mb-2 leading-tight`}>
                {alert.title}
              </h4>
              <p className="text-sm text-gray-700 leading-relaxed mb-2">
                {alert.message}
              </p>
              {alert.symbol && (
                <div className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-md border">
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
                  className="text-gray-600 hover:text-gray-900 hover:bg-gray-100 p-2 rounded-lg transition-colors"
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
                    className="text-gray-600 hover:text-gray-700 hover:bg-gray-50 px-3 py-2 rounded-lg transition-colors"
                    title="Dismiss alert"
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </div>

          {isExpanded && alert.details && (
            <div className="mt-4 pt-4 border-t border-gray-200 bg-gray-50/50 rounded-lg p-3">
              <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {alert.details}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}