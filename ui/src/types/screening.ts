export interface ScreeningResults {
  momentum: Array<{
    symbol: string
    score: number
    indicators: Record<string, number>
    last_price?: number
    change_pct?: number
  }>
  value: Array<{
    symbol: string
    pe_ratio: number
    roe: number
    debt_equity: number
    market_cap?: number
  }>
  quality: Array<{
    symbol: string
    quality_score: number
    fundamentals: Record<string, number>
  }>
  timestamp?: string
}

export interface StrategyResults {
  actions: Array<{
    type: 'BUY' | 'SELL' | 'HOLD' | 'REDUCE' | 'REBALANCE'
    symbol: string
    reasoning: string
    confidence: number
    priority?: 'high' | 'medium' | 'low'
    quantity?: number
    target_price?: number
    stop_loss?: number
  }>
  current_allocation: Record<string, number>
  target_allocation: Record<string, number>
  rebalance_needed: boolean
  total_deviation?: number
  timestamp?: string
}
