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
    <div className="flex flex-col gap-2 p-4 bg-white border border-gray-200 rounded">
      <div className="text-2xl font-semibold text-gray-900 rolling-number">
        {formatValue(displayValue)}
      </div>
      <div className="text-sm text-gray-600">{label}</div>
      {change !== undefined && (
        <div className="text-xs text-gray-500">
          {changeLabel || `${change >= 0 ? '+' : ''}${formatNumber(change, 1)}%`}
        </div>
      )}
    </div>
  )
}
