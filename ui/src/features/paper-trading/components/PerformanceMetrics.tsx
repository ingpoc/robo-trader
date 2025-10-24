/**
 * Performance Metrics Component
 * Displays key trading performance statistics
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TrendingUp, TrendingDown, Target, Trophy, AlertTriangle, Zap } from 'lucide-react'
import { SkeletonCard } from '@/components/common/SkeletonLoader'
import type { PerformanceMetricsResponse } from '../types'

export interface PerformanceMetricsProps {
  metrics: PerformanceMetricsResponse | null
  isLoading?: boolean
}

export const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({
  metrics,
  isLoading = false
}) => {
  if (isLoading || !metrics) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <SkeletonCard key={i} className="h-24" />
        ))}
      </div>
    )
  }

  const metricItems = [
    {
      label: 'Winning Trades',
      value: metrics.winning_trades,
      icon: TrendingUp,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50'
    },
    {
      label: 'Losing Trades',
      value: metrics.losing_trades,
      icon: TrendingDown,
      color: 'text-red-600',
      bg: 'bg-red-50'
    },
    {
      label: 'Win Rate',
      value: `${metrics.win_rate.toFixed(1)}%`,
      icon: Target,
      color: 'text-blue-600',
      bg: 'bg-blue-50'
    },
    {
      label: 'Avg Win',
      value: `₹${Math.abs(metrics.avg_win).toLocaleString('en-IN')}`,
      icon: TrendingUp,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50'
    },
    {
      label: 'Avg Loss',
      value: `₹${Math.abs(metrics.avg_loss).toLocaleString('en-IN')}`,
      icon: TrendingDown,
      color: 'text-red-600',
      bg: 'bg-red-50'
    },
    {
      label: 'Profit Factor',
      value: metrics.profit_factor.toFixed(2),
      icon: Zap,
      color: 'text-amber-600',
      bg: 'bg-amber-50'
    },
    {
      label: 'Best Trade',
      value: `₹${metrics.best_trade.toLocaleString('en-IN')}`,
      icon: Trophy,
      color: 'text-yellow-600',
      bg: 'bg-yellow-50'
    },
    {
      label: 'Worst Trade',
      value: `₹${metrics.worst_trade.toLocaleString('en-IN')}`,
      icon: AlertTriangle,
      color: 'text-orange-600',
      bg: 'bg-orange-50'
    }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {metricItems.map((item, index) => {
            const Icon = item.icon
            return (
              <div
                key={index}
                className={`${item.bg} p-3 rounded-lg border border-gray-200 dark:border-gray-700`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-muted-foreground">{item.label}</span>
                  <Icon className={`w-4 h-4 ${item.color}`} />
                </div>
                <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

export default PerformanceMetrics
