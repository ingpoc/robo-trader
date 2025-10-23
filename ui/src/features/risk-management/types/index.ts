// Risk Management TypeScript Interfaces
// Based on API Specification v1

export interface RiskAssessment {
  assessment_id: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  decision: 'APPROVED' | 'REJECTED' | 'CONDITIONAL';
  risk_score: number;
  risk_factors: {
    concentration_risk: number;
    liquidity_risk: number;
    market_risk: number;
    volatility_risk: number;
    sector_risk: number;
  };
  portfolio_impact: {
    new_position_percent: number;
    sector_exposure: number;
    overall_risk_change: number;
  };
  recommendations: string[];
  warnings: string[];
  expires_at: string;
  assessed_at: string;
}

export interface RiskLimit {
  id: string;
  user_id: string;
  limit_type: 'POSITION_SIZE' | 'SECTOR_CONCENTRATION' | 'STOP_LOSS_PERCENTAGE' | 'DAILY_LOSS_LIMIT' | 'PORTFOLIO_BETA';
  limit_value: number;
  current_utilization: number;
  utilization_percent: number;
  warning_threshold: number;
  status: 'NORMAL' | 'WARNING' | 'CRITICAL';
  description: string;
  updated_at: string;
  is_active: boolean;
}

export interface StopLossOrder {
  id: string;
  user_id: string;
  symbol: string;
  position_id: string;
  trigger_type: 'FIXED' | 'TRAILING' | 'VOLATILITY_ADJUSTED';
  trigger_price: number;
  current_price: number;
  activation_price: number;
  trail_percent?: number;
  is_triggered: boolean;
  created_at: string;
  last_updated: string;
}

export interface RiskAlert {
  id: string;
  user_id: string;
  type: 'LIMIT_BREACH_WARNING' | 'STOP_LOSS_TRIGGERED' | 'HIGH_VOLATILITY' | 'SECTOR_RISK_SPIKE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  title: string;
  message: string;
  details: Record<string, any>;
  is_acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  created_at: string;
  expires_at: string;
}

export interface PortfolioRiskMetrics {
  portfolio_id: string;
  timestamp: string;
  period: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y';
  basic_metrics: {
    total_value: number;
    total_risk_score: number;
    risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
    max_drawdown: number;
    current_drawdown: number;
  };
  value_at_risk: {
    var_1day_95: number;
    var_1day_99: number;
    var_10day_95: number;
    cvar_1day_95: number;
  };
  risk_adjusted_returns: {
    sharpe_ratio: number;
    sortino_ratio: number;
    information_ratio: number;
    treynor_ratio: number;
  };
  portfolio_characteristics: {
    beta: number;
    volatility: number;
    correlation_to_market: number;
    diversification_ratio: number;
  };
  concentration_analysis: {
    top_10_holdings_percent: number;
    largest_position_percent: number;
    sector_concentration: Record<string, number>;
  };
}

export interface RiskMonitoringStatus {
  monitoring_status: 'ACTIVE' | 'INACTIVE' | 'ERROR';
  last_update: string;
  positions_monitored: number;
  active_stop_losses: number;
  risk_summary: {
    overall_risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
    risk_limit_breaches: number;
    warnings_active: number;
    critical_alerts: number;
  };
  current_alerts: RiskAlert[];
  recent_triggers: Array<{
    id: string;
    type: string;
    symbol: string;
    message: string;
    previous_price?: number;
    new_price?: number;
    triggered_at: string;
  }>;
}

// Stop-Loss Template Types
export interface StopLossTemplate {
  id: string;
  name: string;
  description: string;
  trigger_type: 'FIXED' | 'TRAILING' | 'VOLATILITY_ADJUSTED';
  default_trigger_percent: number;
  activation_conditions: {
    min_position_size?: number;
    max_volatility?: number;
    sector_restrictions?: string[];
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Portfolio Rebalancing Types
export interface RebalancingRule {
  id: string;
  name: string;
  description: string;
  trigger_type: 'PERIODIC' | 'THRESHOLD' | 'EVENT_BASED';
  trigger_config: {
    frequency?: 'DAILY' | 'WEEKLY' | 'MONTHLY';
    threshold_percent?: number;
    event_type?: string;
  };
  rebalancing_strategy: 'EQUAL_WEIGHT' | 'TARGET_WEIGHTS' | 'RISK_PARITY';
  target_allocations?: Record<string, number>;
  excluded_assets?: string[];
  is_active: boolean;
  last_executed?: string;
  created_at: string;
  updated_at: string;
}

// Emergency Override Types
export interface EmergencyOverride {
  id: string;
  user_id: string;
  override_type: 'DISABLE_ALL_LIMITS' | 'INCREASE_POSITION_LIMITS' | 'DISABLE_STOP_LOSSES' | 'ALLOW_HIGH_RISK_TRADES';
  reason: string;
  justification: string;
  duration_minutes: number;
  is_active: boolean;
  activated_at?: string;
  expires_at?: string;
  created_at: string;
  approved_by?: string;
}

// WebSocket Event Types
export interface RiskWebSocketEvent {
  type: 'risk_alert' | 'stop_loss_triggered' | 'risk_metrics_update' | 'limit_breach';
  timestamp: string;
  data: any;
}

// Form Types
export interface RiskLimitFormData {
  limit_type: RiskLimit['limit_type'];
  limit_value: number;
  warning_threshold: number;
  description: string;
  is_active: boolean;
}

export interface StopLossTemplateFormData {
  name: string;
  description: string;
  trigger_type: StopLossTemplate['trigger_type'];
  default_trigger_percent: number;
  activation_conditions: StopLossTemplate['activation_conditions'];
}

export interface RebalancingRuleFormData {
  name: string;
  description: string;
  trigger_type: RebalancingRule['trigger_type'];
  trigger_config: RebalancingRule['trigger_config'];
  rebalancing_strategy: RebalancingRule['rebalancing_strategy'];
  target_allocations?: Record<string, number>;
  excluded_assets?: string[];
}

export interface EmergencyOverrideFormData {
  override_type: EmergencyOverride['override_type'];
  reason: string;
  justification: string;
  duration_minutes: number;
}

// API Response Types
export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

// Error Types
export interface RiskApiError {
  code: 'RISK_LIMIT_EXCEEDED' | 'INSUFFICIENT_DATA' | 'INVALID_TRADE_PARAMETERS' | 'RISK_ASSESSMENT_FAILED' | 'STOP_LOSS_NOT_FOUND' | 'LIMIT_NOT_FOUND' | 'ALERT_NOT_FOUND' | 'UNAUTHORIZED_ACCESS' | 'INTERNAL_ERROR';
  message: string;
  details?: any;
}