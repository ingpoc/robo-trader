/**
 * Account Status Card Component
 * Displays key account metrics in a grid layout
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { DollarSign, TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react'
import type { AccountOverviewResponse, PerformanceMetricsResponse } from '../types'

export interface AccountStatusCardProps {
  accountOverview: AccountOverviewResponse | null
  metrics: PerformanceMetricsResponse | null
  onRefresh: () => void
  isRefreshing?: boolean
}

export const AccountStatusCard: React.FC<AccountStatusCardProps> = ({
  accountOverview,
  metrics,
  onRefresh,
  isRefreshing = false
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  if (!accountOverview) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground bg-muted h-4 w-20 rounded" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold bg-muted h-8 w-24 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const cards = [
    {
      label: 'Account Balance',
      value: accountOverview.balance,
      icon: DollarSign,
      color: 'text-blue-600'
    },
    {
      label: 'Deployed Capital',
      value: accountOverview.deployed_capital,
      icon: Activity,
      color: 'text-orange-600'
    },
    {
      label: 'Monthly P&L',
      value: metrics?.total_pnl || 0,
      icon: metrics?.total_pnl && metrics.total_pnl >= 0 ? TrendingUp : TrendingDown,
      color: metrics?.total_pnl && metrics.total_pnl >= 0 ? 'text-emerald-600' : 'text-red-600'
    },
    {
      label: 'Win Rate',
      value: metrics?.win_rate || 0,
      icon: Activity,
      color: 'text-purple-600',
      isPercent: true
    }
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Account Overview</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, index) => {
          const Icon = card.icon
          const displayValue = card.isPercent
            ? `${(card.value as number).toFixed(1)}%`
            : formatCurrency(card.value as number)

          return (
            <Card key={index}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {card.label}
                  </CardTitle>
                  <Icon className={`w-4 h-4 ${card.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{displayValue}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

export default AccountStatusCard
