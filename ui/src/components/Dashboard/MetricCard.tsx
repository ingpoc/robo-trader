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
    <div className="flex flex-col gap-1 p-4 bg-gray-50 border border-gray-200 card-shadow">
      <div className="text-11 font-medium text-gray-500 uppercase tracking-wider leading-none">
        {label}
      </div>
      <div className="text-32 font-light text-gray-900 tabular-nums leading-none mt-2">
        {formatValue(displayValue)}
      </div>
      {change !== undefined && (
        <div className="text-11 text-gray-500 tabular-nums mt-1">
          {changeLabel || `${change >= 0 ? '+' : ''}${formatNumber(change, 1)}%`}
        </div>
      )}
    </div>
  )
}
