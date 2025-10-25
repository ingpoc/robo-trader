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
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 animate-slide-in-up">
      <MetricCard
        label="Available Cash"
        value={portfolio?.cash.free || 0}
        format="currency"
        icon="dollar"
        variant="hero"
        tooltip="The amount of cash available for trading and investments"
      />
      <MetricCard
        label="Total Exposure"
        value={portfolio?.exposure_total || 0}
        format="currency"
        icon="pie"
        variant="hero"
        tooltip="Total market value of all your current positions"
      />
      <MetricCard
        label="Active Positions"
        value={portfolio?.holdings?.length || 0}
        format="number"
        icon="users"
        variant="hero"
        tooltip="Number of different securities you currently hold"
      />
      <MetricCard
        label="Risk Score"
        value={analytics?.portfolio?.concentration_risk || 0}
        format="percent"
        icon="alert"
        variant="hero"
        changeLabel={analytics?.portfolio?.dominant_sector}
        tooltip="Portfolio concentration risk based on sector allocation"
      />
      <MetricCard
        label="Paper Trading P&L"
        value={analytics?.paper_trading?.pnl || 0}
        format="currency"
        icon="activity"
        variant="hero"
        tooltip="Claude's paper trading performance today"
      />
      <MetricCard
        label="AI Win Rate"
        value={analytics?.paper_trading?.win_rate || 0}
        format="percent"
        icon="trending-up"
        variant="hero"
        tooltip="Claude's trading success rate in paper account"
      />
    </div>
  )
}

export default MetricsGrid
