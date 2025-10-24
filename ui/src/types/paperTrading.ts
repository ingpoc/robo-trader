/**
 * Paper Trading Types
 * Type definitions for paper trading functionality
 */

export interface AccountOverviewResponse {
  accountId: string
  accountType: 'swing' | 'options'
  currency: string
  createdDate: string
  initialCapital: number
  currentBalance: number
  totalInvested: number
  marginAvailable: number
  todayPnL: number
  monthlyROI: number
  winRate: number
  activeStrategy: string
  cashAvailable: number
  deployedCapital: number
  openPositions: number
  closedTodayCount: number
}

export interface OpenPositionResponse {
  trade_id: string
  symbol: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  entry_price: number
  current_price: number
  current_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  stop_loss?: number
  target_price?: number
  entry_date: string
  days_held: number
  strategy_rationale: string
  ai_suggested: boolean
}

export interface ClosedTradeResponse {
  trade_id: string
  symbol: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  entry_price: number
  exit_price: number
  realized_pnl: number
  realized_pnl_pct: number
  entry_date: string
  exit_date: string
  holding_period_days: number
  reason_closed: string
  strategy_rationale: string
  ai_suggested: boolean
}

export interface ExecuteBuyRequest {
  symbol: string
  quantity: number
  entry_price: number
  strategy_rationale: string
  stop_loss?: number
  target_price?: number
  ai_suggested?: boolean
}

export interface ExecuteSellRequest {
  symbol: string
  quantity: number
  exit_price: number
  strategy_rationale: string
  stop_loss?: number
  target_price?: number
  ai_suggested?: boolean
}

export interface ClosePositionRequest {
  exit_price: number
  reason?: string
}

export interface PerformanceMetricsResponse {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  largest_win: number
  largest_loss: number
  sharpe_ratio?: number
  period: 'today' | 'week' | 'month' | 'all-time'
}

export interface UsePaperTradingReturn {
  // Data
  accountOverview?: AccountOverviewResponse
  positions: OpenPositionResponse[]
  trades: ClosedTradeResponse[]
  metrics?: PerformanceMetricsResponse
  totalDeployed: number
  totalUnrealizedPnL: number
  unrealizedPnLPct: number

  // Loading states
  isLoading: boolean
  isError: boolean
  accountOverviewLoading: boolean
  positionsLoading: boolean
  tradesLoading: boolean
  metricsLoading: boolean

  // Mutations
  executeBuy: (trade: ExecuteBuyRequest) => void
  executeBuyAsync: (trade: ExecuteBuyRequest) => Promise<any>
  executeBuyLoading: boolean
  executeBuyError?: string

  executeSell: (trade: ExecuteSellRequest) => void
  executeSellAsync: (trade: ExecuteSellRequest) => Promise<any>
  executeSellLoading: boolean
  executeSellError?: string

  closePosition: (data: ClosePositionRequest & { tradeId: string }) => void
  closePositionAsync: (data: ClosePositionRequest & { tradeId: string }) => Promise<any>
  closePositionLoading: boolean
  closePositionError?: string

  resetMonthly: (preserveLearnings?: boolean) => void
  resetMonthlyAsync: (preserveLearnings?: boolean) => Promise<any>
  resetMonthlyLoading: boolean
  resetMonthlyError?: string

  // Refetch functions
  refetchAccountOverview: () => void
  refetchPositions: () => void
  refetchTrades: () => void
  refetchMetrics: () => void
}
