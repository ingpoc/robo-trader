export interface SymbolData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume?: number
  marketCap?: number
}

export interface SymbolSearchResult {
  symbols: SymbolData[]
  total: number
}

// Dashboard and Portfolio Types
export interface Holding {
  symbol: string
  qty: number
  last_price: number
  exposure: number
  pnl_abs: number
  pnl_pct: number
  risk_tags: string[]
}

export interface Cash {
  free: number
  used: number
  total: number
}

export interface Portfolio {
  holdings: Holding[]
  cash: Cash
  exposure_total: number
}

export interface Analytics {
  portfolio: {
    concentration_risk: number
    dominant_sector: string
  }
}

export interface Recommendation {
  id: string
  symbol: string
  action: 'buy' | 'sell' | 'hold'
  confidence: number
  reasoning: string
  status: 'pending' | 'approved' | 'rejected' | 'discussing'
  created_at: string
  updated_at?: string
}

export interface Alert {
  id: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  symbol?: string
  timestamp: string
  acknowledged: boolean
}

export interface AIStatus {
  portfolio_health: string
  current_task: string
  api_budget_used: number
  daily_api_limit: number
  next_planned_task?: string
}

export interface DashboardData {
  portfolio: Portfolio
  analytics: Analytics
  recommendations: Recommendation[]
  alerts: Alert[]
  ai_status: AIStatus
  timestamp: string
  intents?: Intent[]
}

// Trading Types
export interface Intent {
  id: string
  symbol: string
  action: 'buy' | 'sell' | 'hold'
  quantity?: number
  confidence?: number
  reasoning?: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  created_at: string
}

export interface TradeRequest {
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  order_type: 'MARKET' | 'LIMIT'
  price?: number
}

export interface TradeResponse {
  status: string
  intent_id?: string
  reasons?: string[]
}

// Agent Types
export interface AgentStatus {
  id: string
  name: string
  status: 'running' | 'stopped' | 'error' | 'idle'
  last_active: string
  uptime?: number
  memory_usage?: number
  cpu_usage?: number
  active?: boolean
  message?: string
  tasks_completed?: number
}

export interface AgentConfigSettings {
  [key: string]: string | number | boolean | undefined
}

export interface AgentConfig {
  id: string
  name: string
  enabled: boolean
  config: AgentConfigSettings
  last_updated: string
}

export interface AgentFeaturesConfig {
  [key: string]: AgentFeatureConfig
}

export interface AgentFeatureConfig {
  enabled: boolean
  config: AgentConfigSettings
  use_claude?: boolean
  frequency_seconds?: number
  priority?: number
}

// Performance Types
export interface ChartDataPoint {
  timestamp: string
  value: number
  label?: string
}

export interface PerformanceData {
  timestamp: string
  portfolio_value: number
  pnl_absolute: number
  pnl_percentage: number
  sharpe_ratio?: number
  max_drawdown?: number
  win_rate?: number
  chart_data?: ChartDataPoint[]
}

// Additional types for better type safety
export interface UpcomingEarnings {
  symbol: string
  fiscal_period: string
  next_earnings_date: string
  guidance?: string
  days_until?: number
}

export interface ErrorDetails {
  code?: string
  field?: string
  [key: string]: string | number | boolean | undefined
}

export interface ErrorResponse {
  message: string
  status?: number
  details?: ErrorDetails
}

// Configuration Types
export interface BackgroundTaskConfig {
  enabled: boolean
  frequency: number
  frequencyUnit: 'seconds' | 'minutes' | 'hours' | 'days'
  useClaude: boolean
  priority: 'low' | 'medium' | 'high'
}

export interface AIAgentConfig {
  enabled: boolean
  useClaude: boolean
  tools: string[]
  responseFrequency: number
  responseFrequencyUnit: 'minutes' | 'hours'
  scope: 'portfolio' | 'market' | 'watchlist'
  maxTokensPerRequest: number
}

export interface GlobalConfig {
  claudeUsage: {
    enabled: boolean
    dailyTokenLimit: number
    costAlerts: boolean
    costThreshold: number
  }
  schedulerDefaults: {
    defaultFrequency: number
    defaultFrequencyUnit: 'minutes' | 'hours'
    marketHoursOnly: boolean
    retryAttempts: number
    retryDelayMinutes: number
  }
  maxTurns: number
  riskTolerance: number
  dailyApiLimit: number
}

export interface PromptConfig {
  prompt_name: string
  content: string
  description: string
  created_at: string
  updated_at: string
}