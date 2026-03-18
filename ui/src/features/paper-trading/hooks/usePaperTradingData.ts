/**
 * Paper Trading Data Hook
 * Fetches real data from backend API for read-only display
 */

import { useState, useEffect, useCallback } from 'react'
import type {
  AccountOverviewResponse,
  OpenPositionResponse,
  ClosedTradeResponse,
  PerformanceMetricsResponse
} from '../types'

interface UsePaperTradingDataOptions {
  accountId?: string
  autoRefresh?: boolean
  refreshInterval?: number
}

interface PaperTradingDataState {
  accountOverview: AccountOverviewResponse | null
  openPositions: OpenPositionResponse[]
  closedTrades: ClosedTradeResponse[]
  performanceMetrics: PerformanceMetricsResponse | null
  isLoading: boolean
  error: string | null
}

export const usePaperTradingData = (options: UsePaperTradingDataOptions = {}) => {
  const {
    accountId,
    autoRefresh = true,
    refreshInterval = 30000
  } = options

  const [state, setState] = useState<PaperTradingDataState>({
    accountOverview: null,
    openPositions: [],
    closedTrades: [],
    performanceMetrics: null,
    isLoading: true,
    error: null
  })

  const fetchAccountOverview = useCallback(async () => {
    if (!accountId) {
      return null
    }
    try {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/overview`)
      if (!response.ok) throw new Error('Failed to fetch account overview')
      const data = await response.json()
      return data.success ? data.data : null
    } catch (error) {
      console.error('Error fetching account overview:', error)
      return null
    }
  }, [accountId])

  const fetchOpenPositions = useCallback(async () => {
    if (!accountId) {
      return []
    }
    try {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/positions`)
      if (!response.ok) throw new Error('Failed to fetch positions')
      const data = await response.json()
      return data.success ? data.positions : []
    } catch (error) {
      console.error('Error fetching positions:', error)
      return []
    }
  }, [accountId])

  const fetchClosedTrades = useCallback(async () => {
    if (!accountId) {
      return []
    }
    try {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/trades`)
      if (!response.ok) throw new Error('Failed to fetch trades')
      const data = await response.json()
      return data.success ? data.trades : []
    } catch (error) {
      console.error('Error fetching trades:', error)
      return []
    }
  }, [accountId])

  const fetchPerformanceMetrics = useCallback(async () => {
    if (!accountId) {
      return null
    }
    try {
      const response = await fetch(`/api/paper-trading/accounts/${accountId}/performance`)
      if (!response.ok) return null
      const data = await response.json()
      return data.success ? data.performance : data.metrics
    } catch {
      return null
    }
  }, [accountId])

  const refresh = useCallback(async () => {
    if (!accountId) {
      setState({
        accountOverview: null,
        openPositions: [],
        closedTrades: [],
        performanceMetrics: null,
        isLoading: false,
        error: null
      })
      return
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      const [overview, positions, trades, metrics] = await Promise.all([
        fetchAccountOverview(),
        fetchOpenPositions(),
        fetchClosedTrades(),
        fetchPerformanceMetrics()
      ])

      setState({
        accountOverview: overview,
        openPositions: positions,
        closedTrades: trades,
        performanceMetrics: metrics,
        isLoading: false,
        error: null
      })
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch data'
      }))
    }
  }, [accountId, fetchAccountOverview, fetchOpenPositions, fetchClosedTrades, fetchPerformanceMetrics])

  // Initial fetch
  useEffect(() => {
    refresh()
  }, [refresh])

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(refresh, refreshInterval)
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, refresh])

  return {
    ...state,
    refresh
  }
}

export type UsePaperTradingDataReturn = ReturnType<typeof usePaperTradingData>
