/**
 * Paper Trading Feature - TypeScript Interfaces
 * Shared types for paper trading components and hooks
 */

export interface TradeFormData {
  symbol: string
  quantity: string
  price: string
  stopLoss: string
  target: string
  rationale: string
  strategy: string
  type: 'BUY' | 'SELL'
}

export interface TradeValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  riskLevel: 'low' | 'medium' | 'high'
}

export interface PendingTradeData {
  symbol: string
  quantity: number
  entryPrice: number
  stopLoss?: number
  target?: number
  type: 'BUY' | 'SELL'
  totalValue: number
}

export interface AccountOverviewResponse {
  account_id: string
  balance: number
  deployed_capital: number
  buying_power: number
  cash_available: number
  last_updated: string
}

export interface OpenPositionResponse {
  trade_id: string
  symbol: string
  quantity: number
  entry_price: number
  current_price: number
  stop_loss?: number
  target?: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  entry_time: string
}

export interface ClosedTradeResponse {
  trade_id: string
  symbol: string
  quantity: number
  entry_price: number
  exit_price: number
  pnl: number
  pnl_pct: number
  strategy: string
  entry_time: string
  exit_time: string
  holding_days: number
}

export interface PerformanceMetricsResponse {
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  best_trade: number
  worst_trade: number
  largest_win_streak: number
  largest_loss_streak: number
  total_pnl: number
  max_drawdown: number
  max_drawdown_pct: number
  sharpe_ratio: number
  return_on_equity: number
}

export interface ExecuteBuyRequest {
  symbol: string
  quantity: number
  entry_price: number
  stop_loss?: number
  target?: number
  strategy?: string
  rationale?: string
}

export interface ExecuteSellRequest {
  symbol: string
  quantity: number
  entry_price: number
  stop_loss?: number
  target?: number
  strategy?: string
  rationale?: string
}

export interface ClosePositionRequest {
  trade_id: string
  exit_price: number
}
