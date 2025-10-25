/**
 * Custom hooks for paper trading functionality
 */

import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  AccountOverviewResponse,
  OpenPositionResponse,
  ClosedTradeResponse,
  ExecuteBuyRequest,
  ExecuteSellRequest,
  ClosePositionRequest,
  PerformanceMetricsResponse,
} from '../types/paperTrading'

/**
 * Hook for managing paper trading account and positions.
 * Provides queries and mutations for all paper trading operations.
 */
export function usePaperTrading(accountId?: string) {
  const queryClient = useQueryClient()

  // Query: Get account overview
  const accountOverview = useQuery({
    queryKey: ['paper-account-overview', accountId],
    queryFn: async () => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/overview`)
      if (!response.ok) throw new Error('Failed to fetch account overview')
      return response.json() as Promise<AccountOverviewResponse>
    },
    enabled: !!accountId && accountId !== '',
    refetchInterval: 5000, // Refresh every 5 seconds for real-time P&L updates
  })

  // Query: Get open positions
  const openPositions = useQuery({
    queryKey: ['paper-positions', accountId],
    queryFn: async () => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/positions`)
      if (!response.ok) throw new Error('Failed to fetch positions')
      const data = await response.json()
      // Extract positions array and transform field names
      const positions = (data.positions || []).map((pos: any) => ({
        trade_id: pos.id || `${pos.symbol}_${Date.now()}`,
        symbol: pos.symbol,
        trade_type: pos.action === 'SELL' ? 'SELL' : 'BUY',
        quantity: pos.quantity,
        entry_price: pos.entryPrice,
        current_price: pos.ltp,
        current_value: pos.quantity * pos.ltp,
        unrealized_pnl: pos.pnl,
        unrealized_pnl_pct: pos.pnlPercent,
        stop_loss: pos.stopLoss,
        target_price: pos.target,
        entry_date: pos.entryDate,
        days_held: pos.daysHeld,
        strategy_rationale: pos.strategy,
        ai_suggested: false,
      }))
      return positions as Promise<OpenPositionResponse[]>
    },
    enabled: !!accountId && accountId !== '',
    refetchInterval: 2000, // Refresh every 2 seconds for real-time price updates
  })

  // Query: Get trade history
  const tradeHistory = useQuery({
    queryKey: ['paper-trades', accountId],
    queryFn: async () => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/trades?limit=50`)
      if (!response.ok) throw new Error('Failed to fetch trade history')
      const data = await response.json()
      // Extract trades array and transform field names
      const trades = (data.trades || []).map((trade: any) => ({
        trade_id: trade.id,
        symbol: trade.symbol,
        trade_type: trade.action === 'SELL' ? 'SELL' : 'BUY',
        quantity: trade.quantity,
        entry_price: trade.entryPrice,
        exit_price: trade.exitPrice,
        realized_pnl: trade.pnl,
        realized_pnl_pct: trade.pnlPercent,
        entry_date: trade.date,
        exit_date: trade.date,
        holding_period_days: trade.holdTime ? parseInt(trade.holdTime) : 0,
        reason_closed: trade.notes || '',
        strategy_rationale: trade.strategy,
        ai_suggested: false,
      }))
      return trades as Promise<ClosedTradeResponse[]>
    },
    enabled: !!accountId && accountId !== '',
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Query: Get performance metrics
  const performanceMetrics = useQuery({
    queryKey: ['paper-performance', accountId],
    queryFn: async () => {
      const response = await fetch(
        `/api/paper-trading/accounts/${accountId}/performance?period=all-time`,
      )
      if (!response.ok) throw new Error('Failed to fetch performance metrics')
      const data = await response.json()
      // Extract performance object and transform field names
      const perf = data.performance || {}
      return {
        total_trades: perf.totalTrades || 0,
        winning_trades: perf.winningTrades || 0,
        losing_trades: perf.losingTrades || 0,
        win_rate: perf.winRate || 0,
        avg_win: perf.avgWin || 0,
        avg_loss: perf.avgLoss || 0,
        profit_factor: perf.profitFactor || 0,
        largest_win: perf.avgWin || 0,
        largest_loss: perf.avgLoss || 0,
        sharpe_ratio: perf.sharpeRatio,
        period: 'all-time' as const,
      } as PerformanceMetricsResponse
    },
    enabled: !!accountId && accountId !== '',
    refetchInterval: 60000, // Refresh every minute
  })

  // Mutation: Execute BUY trade
  const executeBuy = useMutation({
    mutationFn: async (trade: ExecuteBuyRequest) => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/trades/buy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to execute BUY trade')
      }
      return response.json()
    },
    onSuccess: () => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['paper-account-overview', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-positions', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance', accountId] })
    },
  })

  // Mutation: Execute SELL trade
  const executeSell = useMutation({
    mutationFn: async (trade: ExecuteSellRequest) => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/trades/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to execute SELL trade')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-account-overview', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-positions', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance', accountId] })
    },
  })

  // Mutation: Close position
  const closePosition = useMutation({
    mutationFn: async ({ tradeId, ...closeData }: ClosePositionRequest & { tradeId: string }) => {
      const response = await fetch(`/api/paper-trading/trades/${tradeId}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(closeData),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to close position')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-account-overview', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-positions', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-trades', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance', accountId] })
    },
  })

  // Mutation: Reset monthly account
  const resetMonthly = useMutation({
    mutationFn: async (preserveLearnings: boolean = true) => {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/reset-monthly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmation: true,
          preserve_learnings: preserveLearnings,
        }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to reset account')
      }
      return response.json()
    },
    onSuccess: () => {
      // Refresh all data after reset
      queryClient.invalidateQueries({ queryKey: ['paper-account-overview', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-positions', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-trades', accountId] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance', accountId] })
    },
  })

  // Computed values
  const totalDeployed =
    openPositions.data?.reduce((sum, pos) => sum + pos.current_value, 0) || 0
  const totalUnrealizedPnL =
    openPositions.data?.reduce((sum, pos) => sum + pos.unrealized_pnl, 0) || 0
  const unrealizedPnLPct =
    accountOverview.data && accountOverview.data.currentBalance > 0
      ? (totalUnrealizedPnL / accountOverview.data.currentBalance) * 100
      : 0

  const isLoading =
    accountOverview.isLoading ||
    openPositions.isLoading ||
    tradeHistory.isLoading ||
    performanceMetrics.isLoading

  const isError =
    accountOverview.isError ||
    openPositions.isError ||
    tradeHistory.isError ||
    performanceMetrics.isError

  return {
    // Data
    accountOverview: accountOverview.data,
    positions: openPositions.data || [],
    trades: tradeHistory.data || [],
    metrics: performanceMetrics.data,
    totalDeployed,
    totalUnrealizedPnL,
    unrealizedPnLPct,

    // Loading states
    isLoading,
    isError,
    accountOverviewLoading: accountOverview.isLoading,
    positionsLoading: openPositions.isLoading,
    tradesLoading: tradeHistory.isLoading,
    metricsLoading: performanceMetrics.isLoading,

    // Mutations
    executeBuy: executeBuy.mutate,
    executeBuyAsync: executeBuy.mutateAsync,
    executeBuyLoading: executeBuy.isPending,
    executeBuyError: executeBuy.error?.message,

    executeSell: executeSell.mutate,
    executeSellAsync: executeSell.mutateAsync,
    executeSellLoading: executeSell.isPending,
    executeSellError: executeSell.error?.message,

    closePosition: closePosition.mutate,
    closePositionAsync: closePosition.mutateAsync,
    closePositionLoading: closePosition.isPending,
    closePositionError: closePosition.error?.message,

    resetMonthly: resetMonthly.mutate,
    resetMonthlyAsync: resetMonthly.mutateAsync,
    resetMonthlyLoading: resetMonthly.isPending,
    resetMonthlyError: resetMonthly.error?.message,

    // Refetch functions
    refetchAccountOverview: accountOverview.refetch,
    refetchPositions: openPositions.refetch,
    refetchTrades: tradeHistory.refetch,
    refetchMetrics: performanceMetrics.refetch,
  }
}

/**
 * Hook for filtering and searching trade history.
 */
export function useTradeFilter(trades: ClosedTradeResponse[]) {
  const [filters, setFilters] = React.useState({
    symbol: '',
    tradeType: '' as '' | 'BUY' | 'SELL',
    minPnL: null as number | null,
    maxPnL: null as number | null,
  })

  const filtered = React.useMemo(() => {
    return trades.filter((trade) => {
      if (filters.symbol && !trade.symbol.includes(filters.symbol.toUpperCase())) return false
      if (filters.tradeType && trade.trade_type !== filters.tradeType) return false
      if (filters.minPnL !== null && trade.realized_pnl < filters.minPnL) return false
      if (filters.maxPnL !== null && trade.realized_pnl > filters.maxPnL) return false
      return true
    })
  }, [trades, filters])

  return {
    filters,
    setFilters,
    filtered,
  }
}

// Export types for use in components
export type { UsePaperTradingReturn } from '../types/paperTrading'
