import { useEffect, useRef, useState } from 'react'
import { formatCurrency, formatNumber } from '@/utils/format'

interface MetricCardProps {
  label: string
  value: number
  format?: 'currency' | 'number' | 'percent'
  change?: number
  changeLabel?: string
}

export function MetricCard({
  label,
  value,
  format = 'number',
  change,
  changeLabel,
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

  return (
    <div
      className="flex flex-col gap-2 p-6 bg-white/80 backdrop-blur-sm border border-gray-200/50 card-shadow rounded-lg relative overflow-hidden group"
      role="region"
      aria-labelledby={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
    >
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/50 to-gray-50/30 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <div className="relative z-10">
        <div
          id={`metric-${label.replace(/\s+/g, '-').toLowerCase()}`}
          className="text-xs font-semibold text-gray-600 uppercase tracking-wider leading-none mb-1"
        >
          {label}
        </div>
        <div
          className="text-3xl font-bold text-gray-900 tabular-nums leading-none mb-2 metric-pulse"
          aria-live="polite"
          aria-atomic="true"
        >
          {formatValue(displayValue)}
        </div>
        {change !== undefined && (
          <div
            className={`text-sm font-medium tabular-nums flex items-center gap-1 ${
              change >= 0 ? 'text-success' : 'text-error'
            }`}
            aria-label={`Change: ${change >= 0 ? 'positive' : 'negative'} ${Math.abs(change)} percent`}
          >
            <div className={`w-2 h-2 rounded-full ${
              change >= 0 ? 'bg-success' : 'bg-error'
            }`} />
            {changeLabel || `${change >= 0 ? '+' : ''}${formatNumber(change, 1)}%`}
          </div>
        )}
      </div>

      {/* Decorative element */}
      <div className="absolute top-4 right-4 w-8 h-8 bg-accent/5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </div>
  )
}
