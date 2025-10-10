export interface Portfolio {
  cash: {
    free: number
    total: number
  }
  exposure_total: number
  holdings: Holding[]
  risk_aggregates: {
    portfolio: {
      concentration_risk: number
      dominant_sector: string
    }
  }
}

export interface Holding {
  symbol: string
  qty: number
  avg_price: number
  last_price: number
  pnl_abs: number
  pnl_pct: number
  exposure: number
  risk_tags: string[]
}

export interface Signal {
  symbol: string
  timeframe: string
  entry: {
    type: string
    price?: number
  }
  confidence: number
  rationale: string
}

export interface RiskDecision {
  decision: 'approve' | 'reject' | 'modify'
  reasons: string[]
  modified_params?: Record<string, unknown>
}

export interface Intent {
  id: string
  symbol: string
  status: 'pending' | 'approved' | 'executed' | 'rejected'
  signal?: Signal
  risk_decision?: RiskDecision
  created_at: string
}

export interface Recommendation {
  id: string
  recommendation: {
    action: string
    symbol: string
    confidence: number
    reasoning: string
  }
  status: 'pending' | 'approved' | 'rejected' | 'discussing'
  created_at?: string
}

export interface AIStatus {
  current_task?: string
  next_planned_task?: string
  portfolio_health?: string
  api_budget_used: number
  daily_api_limit: number
}

export interface AgentStatus {
  active: boolean
  status: 'running' | 'idle' | 'standby' | 'error'
  last_activity: string
  tasks_completed: number
  uptime: string
  message: string
}

export interface Alert {
  id: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  timestamp: string
  symbol: string
  actionable: boolean
  persistent: boolean
}

import type { ScreeningResults, StrategyResults } from './screening'

export interface DashboardData {
  portfolio: Portfolio | null
  analytics: Portfolio['risk_aggregates'] | null
  screening: ScreeningResults | null
  strategy: StrategyResults | null
  intents: Intent[]
  config: {
    environment: string
    max_turns: number
  }
  timestamp: string
  ai_status?: AIStatus
  recommendations?: Recommendation[]
}

export interface TradeRequest {
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  order_type: 'MARKET' | 'LIMIT'
  price?: number
}

export interface ChartDataPoint {
  timestamp: string
  value: number
  label?: string
}

export interface PerformanceData {
  period: string
  total_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  chart_data: ChartDataPoint[]
}

export interface AgentConfig {
  enabled: boolean
  frequency: string
  [key: string]: unknown
}

export interface AgentFeatureConfig {
  enabled: boolean
  use_claude: boolean
  frequency_seconds: number
  priority: 'critical' | 'high' | 'medium' | 'low'
}

export interface AgentFeaturesConfig {
  chat_interface: AgentFeatureConfig
  portfolio_scan: AgentFeatureConfig
  market_screening: AgentFeatureConfig
  market_monitoring: AgentFeatureConfig
  stop_loss_monitor: AgentFeatureConfig
  earnings_check: AgentFeatureConfig
  news_monitoring: AgentFeatureConfig
  ai_daily_planning: AgentFeatureConfig
  health_check: AgentFeatureConfig
  trade_execution: AgentFeatureConfig
}

export interface WebSocketMessage {
  type: 'dashboard_update' | 'recommendation' | 'alert' | 'status_change'
  data: DashboardData | Recommendation | Alert | unknown
}
