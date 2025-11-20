/**
 * Performance Charts Component
 * Displays performance trend and asset allocation charts
 */

import React from 'react'
import { ChartCard } from '@/components/Dashboard/ChartCard'

export interface PerformanceChartsProps {
  analytics: any | null
  portfolio: any | null
  detailed?: boolean
}

export const PerformanceCharts: React.FC<PerformanceChartsProps> = ({ analytics, portfolio, detailed = false }) => {
  const chartData = analytics?.chart_data?.map((point: any) => ({
    name: new Date(point.timestamp).toLocaleDateString('en-US', { weekday: 'short' }),
    value: point.value,
  })) || []

  const total = portfolio ? (portfolio.exposure_total || 0) + (portfolio.cash?.free || 0) : 0
  const allocationData = portfolio && total > 0
    ? [
        { name: 'Cash', value: ((portfolio.cash?.free || 0) / total) * 100 },
        { name: 'Equity', value: ((portfolio.exposure_total || 0) / total) * 100 },
      ]
    : [
        { name: 'Cash', value: 100 },
        { name: 'Equity', value: 0 },
      ]

  if (detailed) {
    return (
      <div className="grid grid-cols-1 gap-6 animate-slide-in-up-luxury">
        <div style={{ animationDelay: '100ms' }}>
          <ChartCard title="Performance Trend" type="line" data={chartData} isLoading={false} detailed />
        </div>
        <div style={{ animationDelay: '200ms' }}>
          <ChartCard title="Asset Allocation" type="pie" data={allocationData} showLegend isLoading={false} detailed />
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div style={{ animationDelay: '100ms' }} className="animate-slide-in-up-luxury">
        <ChartCard title="Performance Trend" type="line" data={chartData} isLoading={false} />
      </div>
      <div style={{ animationDelay: '150ms' }} className="animate-slide-in-up-luxury">
        <ChartCard title="Asset Allocation" type="pie" data={allocationData} showLegend isLoading={false} />
      </div>
    </div>
  )
}

export default PerformanceCharts
