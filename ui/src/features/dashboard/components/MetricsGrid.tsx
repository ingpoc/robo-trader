/**
 * Metrics Grid Component
 * Displays key portfolio metrics in a responsive grid
 */

import React from 'react'
import { MetricCard } from '@/components/Dashboard/MetricCard'
import { DashboardData } from '@/types/api'

export interface MetricsGridProps {
  portfolio: DashboardData['portfolio'] | null
  analytics: any | null
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({ portfolio, analytics }) => {
  const summary = portfolio?.summary
  const paperTrading = analytics?.paper_trading
  const metrics = [
    {
      label: "Available Cash",
      value: summary?.cash_available ?? portfolio?.cash.free ?? 0,
      format: "currency",
      icon: "dollar",
      tooltip: "Capital available for new paper-trading positions."
    },
    {
      label: "Portfolio Value",
      value: summary?.total_balance ?? analytics?.portfolio_value ?? portfolio?.cash.total ?? 0,
      format: "currency",
      icon: "pie",
      tooltip: "Current paper-trading equity across the active operator portfolio."
    },
    {
      label: "Active Positions",
      value: summary?.active_positions ?? portfolio?.holdings?.length ?? 0,
      format: "number",
      icon: "users",
      tooltip: "Number of open paper-trading positions."
    },
    {
      label: "Concentration Risk",
      value: analytics?.portfolio?.concentration_risk || 0,
      format: "percent",
      icon: "alert",
      changeLabel: analytics?.portfolio?.dominant_sector,
      tooltip: "Largest single-position concentration as a share of deployed paper capital."
    },
    {
      label: "30d P&L",
      value: analytics?.pnl_absolute ?? paperTrading?.pnl ?? 0,
      format: "currency",
      icon: "activity",
      tooltip: "Aggregate paper-trading profit and loss over the active dashboard window."
    },
    {
      label: "AI Win Rate",
      value: paperTrading?.win_rate ?? analytics?.win_rate ?? 0,
      format: "percent",
      icon: "trending-up",
      tooltip: "Share of closed paper trades that finished positive."
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
      {metrics.map((metric) => (
        <div key={metric.label}>
          <MetricCard
            label={metric.label}
            value={metric.value}
            format={metric.format as any}
            icon={metric.icon as any}
            variant="hero"
            changeLabel={metric.changeLabel}
            tooltip={metric.tooltip}
          />
        </div>
      ))}
    </div>
  )
}

export default MetricsGrid
