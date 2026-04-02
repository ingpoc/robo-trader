/**
 * Paper Trading Feature - TypeScript Interfaces
 * Shared types for paper trading components and hooks
 */

import type { AccountPolicy, ConfigurationStatus } from '@/types/api'

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
export type ArtifactFreshnessState = 'fresh' | 'stale' | 'unknown'
export type ArtifactEmptyReason =
  | 'never_run'
  | 'stale'
  | 'blocked_by_runtime'
  | 'blocked_by_quota'
  | 'no_candidates'
  | 'requires_selection'

export interface RuntimeIdentity {
  runtime: 'frontend' | 'backend'
  git_sha: string | null
  git_short_sha: string | null
  build_id: string
  started_at: string
  workspace_path: string | null
}

export interface RuntimeHealthResponse {
  status: 'healthy' | 'unhealthy'
  message?: string
  error?: string
  timestamp: string
  runtime_identity?: RuntimeIdentity | null
  readiness?: Record<string, unknown>
  components?: Record<string, unknown>
  active_lane?: {
    base_url: string
    host?: string | null
    port?: number | null
  } | null
  callback_listener?: {
    port: number
    active: boolean
  } | null
  ai_runtime_quota?: {
    usage_limited: boolean
    retry_at?: string | null
    last_error?: string | null
  } | null
}

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

export interface WebMCPReadiness {
  status: CapabilityStatus
  summary: string
  detail?: string | null
  tool_count: number
  registered: boolean
  testing_available: boolean
  direct_execution_ready: boolean
  probe_tool?: string | null
}

export interface OverviewSummary {
  generated_at: string
  account_id: string
  execution_mode: string
  selected_account: {
    account_id: string
    buying_power?: number | null
    cash_available?: number | null
    deployed_capital?: number | null
    balance?: number | null
    position_count: number
    valuation_status?: string | null
    valuation_detail?: string | null
    mark_freshness?: string | null
  }
  readiness: {
    overall_status?: string | null
    blocker_count: number
    first_blocker?: string | null
  }
  next_action: {
    summary?: string | null
    detail?: string | null
    route: string
  }
  act_now?: Array<{
    label: string
    detail: string
    priority: 'high' | 'medium' | 'low'
  }>
  staleness?: Record<string, unknown> | null
  queue: {
    unevaluated_closed_trades: number
    queued_promotable_improvements: number
    decision_pending_improvements: number
    recent_runs: number
    ready_now_promotions: number
  }
  performance: {
    portfolio_value?: number | null
    unrealized_pnl?: number | null
    win_rate?: number | null
    closed_trades: number
  }
  recent_stage_outputs: Array<{
    label: string
    status: string
    generated_at?: string | null
    last_generated_at?: string | null
    status_reason?: string | null
    freshness_state?: ArtifactFreshnessState | null
    empty_reason?: ArtifactEmptyReason | null
    considered_count: number
  }>
  guardrails: {
    execution_mode?: string | null
    per_trade_exposure_pct?: number | null
    max_portfolio_risk_pct?: number | null
    max_open_positions?: number | null
    max_new_entries_per_day?: number | null
    max_deployed_capital_pct?: number | null
  }
  incidents: Array<Record<string, unknown>>
}

export interface PaperTradingOperatorSnapshot {
  generated_at: string
  selected_account_id: string | null
  execution_mode?: 'observe' | 'propose' | 'operator_confirmed_execution' | 'manual_only'
  accounts: Array<{
    account_id: string
    account_name: string
    strategy_type: string
  }>
  health: Record<string, unknown> | null
  configuration_status: ConfigurationStatus | null
  account_policy?: AccountPolicy | null
  overview_summary?: OverviewSummary | null
  queue_status: Record<string, unknown> | null
  capability_snapshot: TradingCapabilitySnapshot | Record<string, unknown> | null
  overview: AccountOverviewResponse | null
  positions: OpenPositionResponse[]
  trades: ClosedTradeResponse[]
  performance: PerformanceMetricsResponse | null
  discovery: DiscoveryEnvelope | Record<string, unknown> | null
  research?: ResearchEnvelope | Record<string, unknown> | null
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
  last_researched_at?: string | null
  last_actionability?: 'actionable' | 'watch_only' | 'blocked' | null
  last_thesis_confidence?: number | null
  last_analysis_mode?: 'fresh_evidence' | 'stale_evidence' | 'insufficient_evidence' | null
  research_freshness?: ArtifactFreshnessState
  fresh_primary_source_count?: number
  fresh_external_source_count?: number
  market_data_freshness?: string
  technical_context_available?: boolean
  evidence_mode?: string
  lifecycle_state?: 'fresh_queue' | 'actionable' | 'keep_watch' | 'rejected'
  reentry_reason?: string | null
  last_trigger_type?: string | null
  dark_horse_score?: number
  evidence_quality_score?: number
}

export interface SessionLoopSummary {
  target_actionable_count: number
  actionable_found_count: number
  research_attempt_count: number
  attempted_candidates: string[]
  attempted_candidate_ids: string[]
  queue_exhausted: boolean
  termination_reason: string
  current_candidate_symbol?: string | null
  current_candidate_id?: string | null
  latest_transition_reason?: string | null
  model_usage_by_phase?: Record<string, Record<string, unknown>>
  token_usage_by_phase?: Record<string, Record<string, unknown>>
  total_candidates_scanned: number
  promoted_actionable_symbols: string[]
}

export interface DiscoveryEnvelope {
  status: ArtifactStatus
  generated_at: string
  last_generated_at?: string | null
  blockers: string[]
  context_mode: string
  artifact_count: number
  criteria: string[]
  considered: string[]
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  freshness_state?: ArtifactFreshnessState
  empty_reason?: ArtifactEmptyReason | null
  candidates: AgentCandidate[]
  loop_summary?: SessionLoopSummary | null
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
  fresh_primary_source_count?: number
  fresh_external_source_count?: number
  technical_context_available?: boolean
  evidence_mode?: string
  classification?: 'actionable_buy_candidate' | 'keep_watch' | 'rejected'
  what_changed_since_last_research?: string
  next_step: string
  provider_metadata?: Record<string, unknown>
  generated_at: string
}

export interface ResearchEnvelope {
  status: ArtifactStatus
  generated_at: string
  last_generated_at?: string | null
  blockers: string[]
  context_mode: string
  artifact_count: number
  criteria: string[]
  considered: string[]
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  freshness_state?: ArtifactFreshnessState
  empty_reason?: ArtifactEmptyReason | null
  research: ResearchPacket | null
  loop_summary?: SessionLoopSummary | null
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
  last_generated_at?: string | null
  blockers: string[]
  context_mode: string
  artifact_count: number
  criteria: string[]
  considered: string[]
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  freshness_state?: ArtifactFreshnessState
  empty_reason?: ArtifactEmptyReason | null
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
  last_generated_at?: string | null
  blockers: string[]
  context_mode: string
  artifact_count: number
  criteria: string[]
  considered: string[]
  provider_metadata?: Record<string, unknown>
  run_id?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
  status_reason?: string | null
  freshness_state?: ArtifactFreshnessState
  empty_reason?: ArtifactEmptyReason | null
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
