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
  const metrics = [
    {
      label: "Available Cash",
      value: portfolio?.cash.free || 0,
      format: "currency",
      icon: "dollar",
      tooltip: "The amount of cash available for trading and investments"
    },
    {
      label: "Total Exposure",
      value: portfolio?.exposure_total || 0,
      format: "currency",
      icon: "pie",
      tooltip: "Total market value of all your current positions"
    },
    {
      label: "Active Positions",
      value: portfolio?.holdings?.length || 0,
      format: "number",
      icon: "users",
      tooltip: "Number of different securities you currently hold"
    },
    {
      label: "Risk Score",
      value: analytics?.portfolio?.concentration_risk || 0,
      format: "percent",
      icon: "alert",
      changeLabel: analytics?.portfolio?.dominant_sector,
      tooltip: "Portfolio concentration risk based on sector allocation"
    },
    {
      label: "Paper Trading P&L",
      value: analytics?.paper_trading?.pnl || 0,
      format: "currency",
      icon: "activity",
      tooltip: "Claude's paper trading performance today"
    },
    {
      label: "AI Win Rate",
      value: analytics?.paper_trading?.win_rate || 0,
      format: "percent",
      icon: "trending-up",
      tooltip: "Claude's trading success rate in paper account"
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
      {metrics.map((metric, index) => (
        <div
          key={metric.label}
          style={{ animationDelay: `${index * 50}ms` }}
          className="animate-metric-pop"
        >
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
