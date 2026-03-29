/**
 * Performance Metrics Component
 * Displays key trading performance statistics in a dense operator grid.
 */

import React from 'react'

import type { PerformanceMetricsResponse } from '../types'

export interface PerformanceMetricsProps {
  metrics: PerformanceMetricsResponse | null
  isLoading?: boolean
}

export const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({
  metrics,
  isLoading = false,
}) => {
  const getNumber = (value: number | undefined | null) => value ?? 0

  if (isLoading) {
    return (
      <div className="grid gap-px rounded-2xl border border-border/70 bg-border/70 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse bg-muted/20" />
        ))}
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-6">
        <p className="text-sm font-semibold text-foreground">No performance metrics yet</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Closed trades will populate expectancy, drawdown, and streak statistics as the paper account builds history.
        </p>
      </div>
    )
  }

  const metricItems = [
    { label: 'Winning Trades', value: getNumber(metrics.winning_trades).toString(), detail: 'Closed winners' },
    { label: 'Losing Trades', value: getNumber(metrics.losing_trades).toString(), detail: 'Closed losers' },
    { label: 'Win Rate', value: `${getNumber(metrics.win_rate).toFixed(1)}%`, detail: 'Win ratio' },
    { label: 'Profit Factor', value: getNumber(metrics.profit_factor).toFixed(2), detail: 'Gross wins / gross losses' },
    { label: 'Avg Win', value: formatCurrency(Math.abs(getNumber(metrics.avg_win))), detail: 'Average positive close' },
    { label: 'Avg Loss', value: formatCurrency(Math.abs(getNumber(metrics.avg_loss))), detail: 'Average negative close' },
    { label: 'Best Trade', value: formatCurrency(getNumber(metrics.best_trade)), detail: 'Largest realized win' },
    { label: 'Worst Trade', value: formatCurrency(getNumber(metrics.worst_trade)), detail: 'Largest realized loss' },
  ]

  return (
    <div className="grid gap-px overflow-hidden rounded-2xl border border-border/70 bg-border/70 md:grid-cols-2 xl:grid-cols-4">
      {metricItems.map((item) => (
        <div key={item.label} className="bg-white/80 px-5 py-5 dark:bg-warmgray-800/80">
          <p className="desk-kicker">{item.label}</p>
          <p className="mt-3 text-2xl font-semibold text-foreground">{item.value}</p>
          <p className="mt-2 text-sm text-muted-foreground">{item.detail}</p>
        </div>
      ))}
    </div>
  )
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

export default PerformanceMetrics
