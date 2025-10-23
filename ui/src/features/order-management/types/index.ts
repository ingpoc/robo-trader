// Order Management TypeScript Interfaces
// Based on trading platform specifications

// Core Order Types
export interface Order {
  id: string;
  user_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  order_type: OrderType;
  status: OrderStatus;
  price?: number;
  stop_price?: number;
  limit_price?: number;
  trail_percent?: number;
  time_in_force: TimeInForce;
  created_at: string;
  updated_at: string;
  executed_at?: string;
  filled_quantity: number;
  remaining_quantity: number;
  average_fill_price?: number;
  commission?: number;
  fees?: number;
  notes?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export type OrderType =
  | 'MARKET'
  | 'LIMIT'
  | 'STOP'
  | 'STOP_LIMIT'
  | 'TRAILING_STOP'
  | 'BRACKET'
  | 'OCO' // One Cancels Other
  | 'CONDITIONAL'
  | 'ICEBERG'
  | 'TWAP'
  | 'VWAP';

export type OrderStatus =
  | 'PENDING'
  | 'SUBMITTED'
  | 'PARTIAL_FILL'
  | 'FILLED'
  | 'CANCELLED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'SUSPENDED';

export type TimeInForce =
  | 'DAY'
  | 'GTC' // Good Till Cancelled
  | 'GTD' // Good Till Date
  | 'IOC' // Immediate or Cancel
  | 'FOK' // Fill or Kill
  | 'GTX'; // Good Till Crossing

// Order Templates
export interface OrderTemplate {
  id: string;
  user_id: string;
  name: string;
  description: string;
  strategy_type: string;
  order_config: OrderTemplateConfig;
  risk_parameters: RiskParameters;
  is_active: boolean;
  is_default: boolean;
  usage_count: number;
  last_used?: string;
  created_at: string;
  updated_at: string;
  tags?: string[];
}

export interface OrderTemplateConfig {
  order_type: OrderType;
  side: 'BUY' | 'SELL';
  quantity_type: 'FIXED' | 'PERCENTAGE' | 'DOLLAR_AMOUNT';
  quantity_value: number;
  price_type: 'MARKET' | 'LIMIT' | 'STOP' | 'TRAILING';
  price_offset?: number; // percentage or dollar offset
  time_in_force: TimeInForce;
  expiration_date?: string;
  constraints?: OrderConstraints;
}

export interface RiskParameters {
  max_position_size?: number;
  max_loss_percentage?: number;
  stop_loss_type?: 'FIXED' | 'TRAILING' | 'VOLATILITY_BASED';
  stop_loss_value?: number;
  take_profit_levels?: TakeProfitLevel[];
  risk_reward_ratio?: number;
  max_daily_trades?: number;
  max_daily_loss?: number;
}

export interface TakeProfitLevel {
  id: string;
  percentage: number;
  quantity_percentage: number;
  price_offset?: number;
}

// Order Groups and Baskets
export interface OrderGroup {
  id: string;
  user_id: string;
  name: string;
  description: string;
  group_type: 'BASKET' | 'BRACKET' | 'OCO' | 'CONDITIONAL_CHAIN';
  orders: Order[];
  status: 'ACTIVE' | 'PARTIAL' | 'COMPLETED' | 'CANCELLED';
  execution_strategy: 'SEQUENTIAL' | 'PARALLEL' | 'CONDITIONAL';
  constraints?: GroupConstraints;
  created_at: string;
  updated_at: string;
}

export interface GroupConstraints {
  max_total_value?: number;
  max_individual_order_value?: number;
  min_execution_percentage?: number;
  timeout_seconds?: number;
  cancel_on_failure?: boolean;
}

// Bracket Orders
export interface BracketOrder {
  id: string;
  parent_order_id: string;
  entry_order: Order;
  stop_loss_order?: Order;
  take_profit_orders: Order[];
  status: 'PENDING' | 'PARTIAL' | 'COMPLETED' | 'CANCELLED';
  risk_reward_ratio?: number;
  created_at: string;
}

// Order Constraints
export interface OrderConstraints {
  min_quantity?: number;
  max_quantity?: number;
  price_increment?: number;
  min_price?: number;
  max_price?: number;
  allowed_symbols?: string[];
  restricted_symbols?: string[];
  max_daily_volume?: number;
  max_order_value?: number;
  market_hours_only?: boolean;
  pre_market_allowed?: boolean;
  after_hours_allowed?: boolean;
}

// Order History and Execution
export interface OrderExecution {
  id: string;
  order_id: string;
  execution_id: string;
  quantity: number;
  price: number;
  timestamp: string;
  commission?: number;
  fees?: number;
  venue?: string;
  metadata?: Record<string, any>;
}

export interface OrderHistory {
  order: Order;
  executions: OrderExecution[];
  status_changes: OrderStatusChange[];
  total_filled: number;
  total_value: number;
  total_commission: number;
  total_fees: number;
  pnl_realized?: number;
  pnl_unrealized?: number;
}

export interface OrderStatusChange {
  id: string;
  order_id: string;
  old_status: OrderStatus;
  new_status: OrderStatus;
  timestamp: string;
  reason?: string;
  metadata?: Record<string, any>;
}

// WebSocket Events
export interface OrderWebSocketEvent {
  type: 'order_created' | 'order_updated' | 'order_executed' | 'order_cancelled' | 'order_rejected';
  timestamp: string;
  data: Order | OrderExecution | OrderStatusChange;
}

// Form Data Types
export interface OrderFormData {
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  order_type: OrderType;
  price?: number;
  stop_price?: number;
  limit_price?: number;
  trail_percent?: number;
  time_in_force: TimeInForce;
  expiration_date?: string;
  notes?: string;
  tags?: string[];
}

export interface OrderTemplateFormData {
  name: string;
  description: string;
  strategy_type: string;
  order_config: OrderTemplateConfig;
  risk_parameters: RiskParameters;
  tags?: string[];
}

export interface BracketOrderFormData {
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  entry_price?: number;
  stop_loss_price?: number;
  stop_loss_percentage?: number;
  take_profit_levels: {
    percentage: number;
    quantity_percentage: number;
  }[];
  time_in_force: TimeInForce;
}

export interface OrderGroupFormData {
  name: string;
  description: string;
  group_type: OrderGroup['group_type'];
  orders: OrderFormData[];
  execution_strategy: OrderGroup['execution_strategy'];
  constraints?: GroupConstraints;
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
export interface OrderApiError {
  code:
    | 'ORDER_NOT_FOUND'
    | 'INVALID_ORDER_PARAMETERS'
    | 'INSUFFICIENT_FUNDS'
    | 'MARKET_CLOSED'
    | 'QUANTITY_TOO_SMALL'
    | 'PRICE_OUT_OF_RANGE'
    | 'ORDER_CANCELLED'
    | 'EXECUTION_FAILED'
    | 'RISK_LIMIT_EXCEEDED'
    | 'UNAUTHORIZED_ACCESS'
    | 'INTERNAL_ERROR';
  message: string;
  details?: any;
}

// Filter and Search Types
export interface OrderFilters {
  symbol?: string;
  side?: 'BUY' | 'SELL';
  order_type?: OrderType;
  status?: OrderStatus;
  time_in_force?: TimeInForce;
  date_from?: string;
  date_to?: string;
  min_value?: number;
  max_value?: number;
  tags?: string[];
}

export interface OrderSortOptions {
  field: 'created_at' | 'updated_at' | 'symbol' | 'quantity' | 'price' | 'status';
  direction: 'asc' | 'desc';
}

// Statistics and Analytics
export interface OrderStatistics {
  total_orders: number;
  total_value: number;
  total_commission: number;
  total_fees: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  sharpe_ratio?: number;
  max_drawdown: number;
  best_trade: number;
  worst_trade: number;
  orders_by_type: Record<OrderType, number>;
  orders_by_status: Record<OrderStatus, number>;
  orders_by_symbol: Record<string, number>;
}

// Real-time Monitoring
export interface OrderMonitoringStatus {
  active_orders: number;
  pending_orders: number;
  executing_orders: number;
  total_positions: number;
  total_value: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  risk_exposure: number;
  margin_used: number;
  buying_power: number;
  last_update: string;
}

// Conditional Orders
export interface ConditionalOrder {
  id: string;
  user_id: string;
  condition: OrderCondition;
  trigger_order: OrderFormData;
  is_active: boolean;
  triggered_at?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface OrderCondition {
  type: 'PRICE' | 'VOLUME' | 'TIME' | 'TECHNICAL_INDICATOR' | 'NEWS_SENTIMENT';
  operator: 'GT' | 'LT' | 'GTE' | 'LTE' | 'EQ' | 'NEQ';
  value: any;
  symbol?: string;
  timeframe?: string;
  additional_conditions?: OrderCondition[];
  logical_operator?: 'AND' | 'OR';
}

// Advanced Order Types
export interface IcebergOrder extends Order {
  display_quantity: number;
  total_quantity: number;
  peak_quantity: number;
  randomize_peaks?: boolean;
}

export interface TwapOrder extends Order {
  duration_minutes: number;
  interval_minutes: number;
  total_slices: number;
  executed_slices: number;
}

export interface VwapOrder extends Order {
  start_time: string;
  end_time: string;
  benchmark_volume?: number;
  participation_rate?: number;
}

// Export all types
export type {
  Order,
  OrderType,
  OrderStatus,
  TimeInForce,
  OrderTemplate,
  OrderTemplateConfig,
  RiskParameters,
  TakeProfitLevel,
  OrderGroup,
  GroupConstraints,
  BracketOrder,
  OrderConstraints,
  OrderExecution,
  OrderHistory,
  OrderStatusChange,
  OrderWebSocketEvent,
  OrderFormData,
  OrderTemplateFormData,
  BracketOrderFormData,
  OrderGroupFormData,
  ApiResponse,
  PaginatedResponse,
  OrderApiError,
  OrderFilters,
  OrderSortOptions,
  OrderStatistics,
  OrderMonitoringStatus,
  ConditionalOrder,
  OrderCondition,
  IcebergOrder,
  TwapOrder,
  VwapOrder,
};