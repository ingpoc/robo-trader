/**
 * Paper Trading Feature Component
 * Main orchestrator for paper trading account management
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { TrendingUp, BarChart3, Lightbulb } from 'lucide-react'
import { AccountStatusCard } from './components/AccountStatusCard'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { UnrealizedPnLCard } from './components/UnrealizedPnLCard'
import { PositionsTable } from './components/PositionsTable'
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { TradeExecutionForm } from './components/TradeExecutionForm'
import { AILearningPanel } from './components/AILearningPanel'
import { ClosePositionDialog } from './components/ClosePositionDialog'
import { PositionModifierDialog } from './components/PositionModifierDialog'
import { RiskValidationDialog } from './components/RiskValidationDialog'
import type {
  AccountOverviewResponse,
  OpenPositionResponse,
  ClosedTradeResponse,
  PerformanceMetricsResponse,
  ExecuteBuyRequest,
  ExecuteSellRequest,
  ClosePositionRequest,
  TradeFormData,
  TradeValidationResult,
  DailyReflection,
  StrategyInsight
} from './types'

export interface PaperTradingFeatureProps {
  accountOverview: AccountOverviewResponse | null
  openPositions: OpenPositionResponse[]
  closedTrades: ClosedTradeResponse[]
  performanceMetrics: PerformanceMetricsResponse | null
  dailyReflection: DailyReflection | null
  strategyInsights: StrategyInsight[]
  onExecuteBuy: (request: ExecuteBuyRequest) => Promise<void>
  onExecuteSell: (request: ExecuteSellRequest) => Promise<void>
  onClosePosition: (request: ClosePositionRequest) => Promise<void>
  onModifyPosition: (tradeId: string, stopLoss?: number, target?: number) => Promise<void>
  onRefresh: () => Promise<void>
  isLoading?: boolean
}

export const PaperTradingFeature: React.FC<PaperTradingFeatureProps> = ({
  accountOverview,
  openPositions,
  closedTrades,
  performanceMetrics,
  dailyReflection,
  strategyInsights,
  onExecuteBuy,
  onExecuteSell,
  onClosePosition,
  onModifyPosition,
  onRefresh,
  isLoading = false
}) => {
  // Dialog states
  const [closeDialogOpen, setCloseDialogOpen] = useState(false)
  const [modifyDialogOpen, setModifyDialogOpen] = useState(false)
  const [riskDialogOpen, setRiskDialogOpen] = useState(false)

  // Selected position for dialogs
  const [selectedPosition, setSelectedPosition] = useState<OpenPositionResponse | null>(null)

  // Pending trade for risk validation
  const [pendingTrade, setPendingTrade] = useState<{
    data: TradeFormData
    validation: TradeValidationResult
  } | null>(null)

  // Loading states
  const [isExecuting, setIsExecuting] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Calculate totals
  const totalUnrealizedPnL = openPositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)
  const totalUnrealizedPnLPct = accountOverview && accountOverview.balance > 0
    ? (totalUnrealizedPnL / accountOverview.balance) * 100
    : 0

  // Handle close position dialog
  const handleOpenCloseDialog = (position: OpenPositionResponse) => {
    setSelectedPosition(position)
    setCloseDialogOpen(true)
  }

  const handleConfirmClose = async (exitPrice: number) => {
    if (!selectedPosition) return

    setIsExecuting(true)
    try {
      await onClosePosition({
        trade_id: selectedPosition.trade_id,
        exit_price: exitPrice
      })
      setCloseDialogOpen(false)
      setSelectedPosition(null)
    } finally {
      setIsExecuting(false)
    }
  }

  // Handle modify position dialog
  const handleOpenModifyDialog = (position: OpenPositionResponse) => {
    setSelectedPosition(position)
    setModifyDialogOpen(true)
  }

  const handleConfirmModify = async (stopLoss?: number, target?: number) => {
    if (!selectedPosition) return

    setIsExecuting(true)
    try {
      await onModifyPosition(selectedPosition.trade_id, stopLoss, target)
      setModifyDialogOpen(false)
      setSelectedPosition(null)
    } finally {
      setIsExecuting(false)
    }
  }

  // Handle trade execution form submission
  const handleTradeSubmit = async (data: TradeFormData, validation: TradeValidationResult) => {
    if (validation.riskLevel === 'high') {
      // Show risk validation dialog for high-risk trades
      setPendingTrade({ data, validation })
      setRiskDialogOpen(true)
      return
    }

    // Execute trade directly for low/medium risk
    await executeTrade(data)
  }

  const handleConfirmRiskTrade = async () => {
    if (!pendingTrade) return

    setRiskDialogOpen(false)
    await executeTrade(pendingTrade.data)
    setPendingTrade(null)
  }

  const executeTrade = async (data: TradeFormData) => {
    setIsExecuting(true)
    try {
      if (data.type === 'BUY') {
        await onExecuteBuy({
          symbol: data.symbol,
          quantity: data.quantity,
          entry_price: data.entryPrice,
          stop_loss: data.stopLoss,
          target: data.target,
          strategy: data.strategy
        })
      } else {
        await onExecuteSell({
          symbol: data.symbol,
          quantity: data.quantity,
          exit_price: data.entryPrice,
          stop_loss: data.stopLoss,
          target: data.target,
          strategy: data.strategy
        })
      }
    } finally {
      setIsExecuting(false)
    }
  }

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
      {/* Account Status Cards */}
      <AccountStatusCard
        accountOverview={accountOverview}
        metrics={performanceMetrics}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="positions" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="hidden sm:inline">Positions</span>
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </TabsTrigger>
          <TabsTrigger value="learning" className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4" />
            <span className="hidden sm:inline">Learning</span>
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
              <PerformanceMetrics
                metrics={performanceMetrics}
                isLoading={isLoading}
              />
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PositionsTable
              positions={openPositions}
              onClosePosition={handleOpenCloseDialog}
              onModifyLevels={handleOpenModifyDialog}
              isLoading={isLoading}
            />
            <TradeExecutionForm
              accountOverview={accountOverview}
              positions={openPositions}
              onSubmit={handleTradeSubmit}
              isLoading={isExecuting}
            />
          </div>
        </TabsContent>

        {/* Positions Tab */}
        <TabsContent value="positions">
          <PositionsTable
            positions={openPositions}
            onClosePosition={handleOpenCloseDialog}
            onModifyLevels={handleOpenModifyDialog}
            isLoading={isLoading}
          />
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <TradeHistoryTable
            trades={closedTrades}
            isLoading={isLoading}
          />
        </TabsContent>

        {/* Learning Tab */}
        <TabsContent value="learning">
          <AILearningPanel
            dailyReflection={dailyReflection}
            strategyInsights={strategyInsights}
            isLoading={isLoading}
          />
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <ClosePositionDialog
        isOpen={closeDialogOpen}
        position={selectedPosition}
        onClose={() => {
          setCloseDialogOpen(false)
          setSelectedPosition(null)
        }}
        onConfirm={handleConfirmClose}
        isLoading={isExecuting}
      />

      <PositionModifierDialog
        isOpen={modifyDialogOpen}
        position={selectedPosition}
        onClose={() => {
          setModifyDialogOpen(false)
          setSelectedPosition(null)
        }}
        onConfirm={handleConfirmModify}
        isLoading={isExecuting}
      />

      <RiskValidationDialog
        isOpen={riskDialogOpen}
        tradeData={pendingTrade ? {
          symbol: pendingTrade.data.symbol,
          type: pendingTrade.data.type,
          quantity: pendingTrade.data.quantity,
          entryPrice: pendingTrade.data.entryPrice,
          stopLoss: pendingTrade.data.stopLoss,
          target: pendingTrade.data.target,
          totalValue: pendingTrade.data.quantity * pendingTrade.data.entryPrice
        } : null}
        validationResult={pendingTrade?.validation || null}
        onClose={() => {
          setRiskDialogOpen(false)
          setPendingTrade(null)
        }}
        onConfirm={handleConfirmRiskTrade}
        isLoading={isExecuting}
      />
    </div>
  )
}

export default PaperTradingFeature
