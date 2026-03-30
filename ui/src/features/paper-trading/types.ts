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
  valuation_status?: 'live' | 'quote_unavailable' | 'market_closed'
  valuation_detail?: string | null
}

export interface OpenPositionResponse {
  trade_id: string
  symbol: string
  quantity: number
  entry_price: number
  current_price: number | null
  stop_loss?: number
  target?: number
  unrealized_pnl: number | null
  unrealized_pnl_pct: number | null
  entry_time: string
  strategy?: string
  tradeType?: string
  currentValue?: number | null
  daysHeld?: number
  markStatus?: 'live' | 'stale_entry' | 'quote_unavailable' | 'market_closed'
  markDetail?: string | null
  markTimestamp?: string | null
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

export type CapabilityStatus = 'ready' | 'degraded' | 'blocked'

export type ArtifactStatus = 'ready' | 'blocked' | 'empty'

export interface TradingCapabilityCheck {
  key: string
  label: string
  status: CapabilityStatus
  blocking?: boolean
  summary: string
  detail?: string | null
  metadata?: Record<string, unknown>
}

export interface TradingCapabilitySnapshot {
  mode: string
  overall_status: CapabilityStatus
  automation_allowed: boolean
  generated_at: string
  account_id?: string | null
  blockers: string[]
  checks: TradingCapabilityCheck[]
}

export interface PaperTradingOperatorSnapshot {
  generated_at: string
  selected_account_id: string | null
  execution_mode?: 'observe' | 'propose' | 'operator_confirmed_execution'
  accounts: Array<{
    account_id: string
    account_name: string
    strategy_type: string
  }>
  health: Record<string, unknown> | null
  configuration_status: Record<string, unknown> | null
  queue_status: Record<string, unknown> | null
  capability_snapshot: TradingCapabilitySnapshot | Record<string, unknown> | null
  overview: AccountOverviewResponse | null
  positions: OpenPositionResponse[]
  trades: ClosedTradeResponse[]
  performance: PerformanceMetricsResponse | null
  discovery: DiscoveryEnvelope | Record<string, unknown> | null
  decisions?: DecisionEnvelope | Record<string, unknown> | null
  review?: ReviewEnvelope | Record<string, unknown> | null
  learning_summary: Record<string, unknown> | null
  improvement_report: Record<string, unknown> | null
  run_history?: Record<string, unknown> | null
  latest_retrospective?: Record<string, unknown> | null
  learning_readiness?: Record<string, unknown> | null
  latest_improvement_decisions?: Array<Record<string, unknown>>
  promotion_report?: Record<string, unknown> | null
  staleness?: Record<string, unknown> | null
  operator_recommendation?: Record<string, unknown> | null
  positions_health?: Record<string, unknown> | null
  recent_trade_outcomes?: Array<Record<string, unknown>>
  promotable_improvements?: Array<Record<string, unknown>>
  incidents?: Array<Record<string, unknown>>
}

export interface AgentCandidate {
  candidate_id: string
  symbol: string
  company_name?: string | null
  sector?: string | null
  source: string
  priority: 'high' | 'medium' | 'low'
  confidence: number
  rationale: string
  next_step: string
  generated_at: string
}

export interface DiscoveryEnvelope {
  status: ArtifactStatus
  generated_at: string
  blockers: string[]
  context_mode: string
  artifact_count: number
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  candidates: AgentCandidate[]
}

export interface ResearchPacket {
  research_id: string
  candidate_id: string
  account_id: string
  symbol: string
  thesis: string
  evidence: string[]
  risks: string[]
  invalidation: string
  confidence: number
  screening_confidence: number
  thesis_confidence: number
  analysis_mode: 'fresh_evidence' | 'stale_evidence' | 'insufficient_evidence'
  actionability: 'actionable' | 'watch_only' | 'blocked'
  external_evidence_status: 'fresh' | 'partial' | 'missing'
  why_now: string
  source_summary: Array<{
    source_type: string
    label: string
    tier: 'primary' | 'secondary' | 'derived'
    timestamp: string
    freshness: string
    detail: string
  }>
  evidence_citations: Array<{
    source_type: string
    label: string
    reference: string
    tier: 'primary' | 'secondary' | 'derived'
    freshness: string
    timestamp: string
  }>
  market_data_freshness: {
    status: string
    summary: string
    timestamp: string
    age_seconds?: number | null
    provider: string
    has_intraday_quote: boolean
    has_historical_data: boolean
  }
  next_step: string
  provider_metadata?: Record<string, unknown>
  generated_at: string
}

export interface ResearchEnvelope {
  status: ArtifactStatus
  generated_at: string
  blockers: string[]
  context_mode: string
  artifact_count: number
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  research: ResearchPacket | null
}

export interface DecisionPacket {
  decision_id: string
  symbol: string
  action: 'hold' | 'review_exit' | 'tighten_stop' | 'take_profit'
  confidence: number
  thesis: string
  invalidation: string
  next_step: string
  risk_note: string
  generated_at: string
}

export interface DecisionEnvelope {
  status: ArtifactStatus
  generated_at: string
  blockers: string[]
  context_mode: string
  artifact_count: number
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  decisions: DecisionPacket[]
}

export interface StrategyProposal {
  proposal_id: string
  title: string
  recommendation: string
  rationale: string
  guardrail: string
}

export interface ReviewReport {
  review_id: string
  summary: string
  strengths: string[]
  weaknesses: string[]
  risk_flags: string[]
  top_lessons: string[]
  strategy_proposals: StrategyProposal[]
  generated_at: string
}

export interface ReviewEnvelope {
  status: ArtifactStatus
  generated_at: string
  blockers: string[]
  context_mode: string
  artifact_count: number
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  review: ReviewReport | null
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
