import { useEffect, useRef, useState } from 'react'
import { formatCurrency, formatNumber, formatPercent } from '@/utils/format'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, PieChart, Users, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  label: string
  value: number
  format?: 'currency' | 'number' | 'percent'
  change?: number
  changeLabel?: string
  tooltip?: string
  icon?: 'activity' | 'dollar' | 'pie' | 'users' | 'alert'
  variant?: 'default' | 'hero' | 'compact'
  trend?: 'up' | 'down' | 'neutral'
}

export function MetricCard({
  label,
  value,
  format = 'number',
  change,
  changeLabel,
  tooltip,
  icon = 'activity',
  variant = 'default',
  trend,
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(value)
  const previousValueRef = useRef(value)

  useEffect(() => {
    const previous = previousValueRef.current
    const diff = value - previous
    const steps = 20
    const increment = diff / steps
    let current = previous
    let step = 0

    const timer = setInterval(() => {
      step++
      current += increment
      setDisplayValue(current)

      if (step >= steps) {
        clearInterval(timer)
        setDisplayValue(value)
        previousValueRef.current = value
      }
    }, 10)

    return () => clearInterval(timer)
  }, [value])

  const formatValue = (val: number) => {
    switch (format) {
      case 'currency':
        return formatCurrency(val)
      case 'percent':
        return formatPercent(val, 1)
      default:
        return formatNumber(val, 0)
    }
  }

  const getIcon = () => {
    switch (icon) {
      case 'dollar':
        return DollarSign
      case 'pie':
        return PieChart
      case 'users':
        return Users
      case 'alert':
        return AlertTriangle
      default:
        return Activity
    }
  }

  const getTrendIcon = () => {
    if (trend === 'up') return TrendingUp
    if (trend === 'down') return TrendingDown
    return Minus
  }

  const getTrendColor = () => {
    if (trend === 'up') return 'text-emerald-600'
    if (trend === 'down') return 'text-rose-600'
    return 'text-warmgray-500'
  }

  const Icon = getIcon()
  const TrendIcon = getTrendIcon()

  const cardContent = (
    <div
      className={cn(
        "group relative overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow duration-300 rounded-lg animate-fade-in",
        variant === 'hero' && "bg-warmgray-50 shadow-sm",
        variant === 'compact' && "p-4 rounded-lg"
      )}
      role="region"
      aria-labelledby={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
    >

      <div className="relative z-10 p-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={cn(
              "p-2 rounded-lg",
              variant === 'hero'
                ? "bg-copper-100 text-copper-600"
                : "bg-warmgray-100 text-warmgray-700"
            )}>
              <Icon className="w-4 h-4" />
            </div>
            <div
              id={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
              className="text-sm font-semibold text-warmgray-700 leading-none"
            >
              {label}
            </div>
          </div>
          {trend && (
            <div className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded", getTrendColor(),
              trend === 'up' ? 'bg-emerald-50' :
              trend === 'down' ? 'bg-rose-50' : 'bg-warmgray-50'
            )}>
              <TrendIcon className="w-3 h-3" />
              <span className="sr-only">{trend} trend</span>
            </div>
          )}
        </div>

        <div
          className={cn(
            "font-bold text-warmgray-900 tabular-nums leading-none mb-2",
            variant === 'hero' ? "text-4xl" : "text-3xl",
            variant === 'compact' && "text-2xl"
          )}
          aria-live="polite"
          aria-atomic="true"
        >
          {formatValue(displayValue)}
        </div>

        {change !== undefined && (
          <div
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1 rounded text-xs font-semibold tabular-nums",
              change >= 0
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-rose-50 text-rose-700'
            )}
            aria-label={`Change: ${change >= 0 ? 'positive' : 'negative'} ${Math.abs(change)} percent`}
          >
            {changeLabel || `${change >= 0 ? '+' : ''}${formatNumber(change, 1)}%`}
          </div>
        )}
      </div>
    </div>
  )

  if (tooltip) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          {cardContent}
        </TooltipTrigger>
        <TooltipContent>
          <p>{tooltip}</p>
        </TooltipContent>
      </Tooltip>
    )
  }

  return cardContent
}
