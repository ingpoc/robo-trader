import { useEffect, useRef, useState } from 'react'
import { formatCurrency, formatNumber } from '@/utils/format'
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
        return `${formatNumber(val, 1)}%`
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
    if (trend === 'up') return 'text-green-600'
    if (trend === 'down') return 'text-red-600'
    return 'text-gray-500'
  }

  const Icon = getIcon()
  const TrendIcon = getTrendIcon()

  const cardContent = (
    <div
      className={cn(
        "group relative overflow-hidden border-0 bg-gradient-to-br from-white to-gray-50/50 shadow-lg hover:shadow-xl transition-all duration-300 rounded-xl",
        variant === 'hero' && "from-blue-50 to-indigo-50/50 shadow-blue-100/50",
        variant === 'compact' && "p-4 rounded-lg"
      )}
      role="region"
      aria-labelledby={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <div className="relative z-10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2 rounded-lg",
              variant === 'hero' ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
            )}>
              <Icon className="w-5 h-5" />
            </div>
            <div
              id={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
              className="text-sm font-semibold text-gray-700 uppercase tracking-wider leading-none"
            >
              {label}
            </div>
          </div>
          {trend && (
            <div className={cn("flex items-center gap-1 text-sm font-medium", getTrendColor())}>
              <TrendIcon className="w-4 h-4" />
              <span className="sr-only">{trend} trend</span>
            </div>
          )}
        </div>

        <div
          className={cn(
            "font-bold text-gray-900 tabular-nums leading-none mb-3 metric-pulse",
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
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium tabular-nums ${
              change >= 0
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }`}
            aria-label={`Change: ${change >= 0 ? 'positive' : 'negative'} ${Math.abs(change)} percent`}
          >
            <div className={`w-2 h-2 rounded-full ${
              change >= 0 ? 'bg-green-500' : 'bg-red-500'
            }`} />
            {changeLabel || `${change >= 0 ? '+' : ''}${formatNumber(change, 1)}%`}
          </div>
        )}
      </div>

      {/* Decorative gradient border */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 -m-px" />
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
