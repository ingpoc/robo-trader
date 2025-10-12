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
        "group relative overflow-hidden border-0 bg-gradient-to-br from-white/90 to-gray-50/70 backdrop-blur-sm shadow-professional hover:shadow-professional-hover transition-all duration-300 rounded-xl animate-scale-in",
        variant === 'hero' && "from-blue-50/90 to-indigo-50/70 shadow-blue-100/50 ring-1 ring-blue-100/50",
        variant === 'compact' && "p-4 rounded-lg"
      )}
      role="region"
      aria-labelledby={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
    >
      {/* Professional gradient overlay */}
      <div className="absolute inset-0 bg-gradient-professional opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      {/* Animated border glow */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 -m-px" />

      <div className="relative z-10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-3 rounded-xl shadow-sm",
              variant === 'hero'
                ? "bg-gradient-to-br from-blue-100 to-blue-200 text-blue-700 shadow-blue-100/50"
                : "bg-gradient-to-br from-gray-100 to-gray-200 text-gray-700 shadow-gray-100/50"
            )}>
              <Icon className="w-5 h-5" />
            </div>
            <div
              id={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
              className="text-sm font-bold text-gray-800 uppercase tracking-wider leading-none"
            >
              {label}
            </div>
          </div>
          {trend && (
            <div className={cn("flex items-center gap-1 text-sm font-semibold px-2 py-1 rounded-full", getTrendColor(),
              trend === 'up' ? 'bg-green-50 text-green-700' :
              trend === 'down' ? 'bg-red-50 text-red-700' : 'bg-gray-50 text-gray-700'
            )}>
              <TrendIcon className="w-4 h-4" />
              <span className="sr-only">{trend} trend</span>
            </div>
          )}
        </div>

        <div
          className={cn(
            "font-black text-gray-900 tabular-nums leading-none mb-3",
            variant === 'hero' ? "text-5xl bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent" : "text-4xl",
            variant === 'compact' && "text-3xl"
          )}
          aria-live="polite"
          aria-atomic="true"
        >
          {formatValue(displayValue)}
        </div>

        {change !== undefined && (
          <div
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold tabular-nums shadow-sm",
              change >= 0
                ? 'bg-gradient-to-r from-green-100 to-green-200 text-green-800 border border-green-200'
                : 'bg-gradient-to-r from-red-100 to-red-200 text-red-800 border border-red-200'
            )}
            aria-label={`Change: ${change >= 0 ? 'positive' : 'negative'} ${Math.abs(change)} percent`}
          >
            <div className={cn("w-2 h-2 rounded-full animate-pulse",
              change >= 0 ? 'bg-green-500' : 'bg-red-500'
            )} />
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
