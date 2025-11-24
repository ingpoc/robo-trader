/**
 * Paper Trading Feature Component
 * READ-ONLY observatory for AI paper trading - all trades executed via MCP
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TrendingUp, BarChart3, History } from 'lucide-react'
import { AccountStatusCard } from './components/AccountStatusCard'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { UnrealizedPnLCard } from './components/UnrealizedPnLCard'
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { RealTimePositionsTable } from './components/RealTimePositionsTable'
import { AIAutomationControlPanel } from './components/AIAutomationControlPanel'
import type {
  AccountOverviewResponse,
  OpenPositionResponse,
  ClosedTradeResponse,
  PerformanceMetricsResponse
} from './types'

export interface PaperTradingFeatureProps {
  accountOverview: AccountOverviewResponse | null
  openPositions: OpenPositionResponse[]
  closedTrades: ClosedTradeResponse[]
  performanceMetrics: PerformanceMetricsResponse | null
  onRefresh: () => Promise<void>
  isLoading?: boolean
}

export const PaperTradingFeature: React.FC<PaperTradingFeatureProps> = ({
  accountOverview,
  openPositions,
  closedTrades,
  performanceMetrics,
  onRefresh,
  isLoading = false
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const totalUnrealizedPnL = openPositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)
  const totalUnrealizedPnLPct = accountOverview && accountOverview.balance > 0
    ? (totalUnrealizedPnL / accountOverview.balance) * 100
    : 0

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* AI Automation Control Panel */}
      <AIAutomationControlPanel />

      {/* Account Status Cards */}
      <AccountStatusCard
        accountOverview={accountOverview}
        metrics={performanceMetrics}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Tabs - Read-only observatory */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="positions" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="hidden sm:inline">Positions</span>
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <UnrealizedPnLCard
              totalUnrealizedPnL={totalUnrealizedPnL}
              unrealizedPnLPct={totalUnrealizedPnLPct}
              positions={openPositions}
            />
            <Card>
              <PerformanceMetrics metrics={performanceMetrics} isLoading={isLoading} />
            </Card>
          </div>
        </TabsContent>

        {/* Positions Tab - Real-time with Zerodha data */}
        <TabsContent value="positions">
          <RealTimePositionsTable
            positions={openPositions}
            isLoading={isLoading}
          />
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <TradeHistoryTable trades={closedTrades} isLoading={isLoading} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default PaperTradingFeature
