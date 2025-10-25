/**
 * Paper Trading Feature Index
 * Central export point for paper trading feature
 */

export { PaperTradingFeature } from './PaperTradingFeature'
export type { PaperTradingFeatureProps } from './PaperTradingFeature'

// Re-export types
export type {
  TradeFormData,
  TradeValidationResult,
  OpenPositionResponse,
  ClosedTradeResponse,
  PerformanceMetricsResponse,
  AccountOverviewResponse,
  ExecuteBuyRequest,
  ExecuteSellRequest,
  ClosePositionRequest,
  DailyReflection,
  StrategyInsight
} from './types'

// Re-export hooks
export { useTradeValidation } from './hooks/useTradeValidation'
