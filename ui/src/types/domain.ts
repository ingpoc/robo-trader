// Domain models for News & Earnings feature

export type SentimentType = 'positive' | 'negative' | 'neutral'

export type TabType = 'news' | 'earnings' | 'recommendations'

export type RecommendationAction = 'buy' | 'sell' | 'hold'

export type RecommendationStatus = 'pending' | 'approved' | 'rejected' | 'discussing'

export type AgentStatus = 'active' | 'inactive' | 'error'

export type RiskLevel = 'low' | 'medium' | 'high'

export interface NewsItem {
  id: string
  symbol: string
  title: string
  summary: string
  content?: string
  source?: string
  sentiment: SentimentType
  relevance_score: number
  published_at: string
  fetched_at: string
  citations?: string[]
  created_at: string
  url?: string
}

export interface EarningsReport {
  id: string
  symbol: string
  fiscal_period: string
  fiscal_year?: number
  fiscal_quarter?: number
  report_date: string
  eps_actual?: number
  eps_estimated?: number
  revenue_actual?: number
  revenue_estimated?: number
  surprise_pct?: number
  guidance?: string
  next_earnings_date?: string
  fetched_at: string
  created_at: string
}

export interface UpcomingEarnings {
  symbol: string
  fiscal_period: string
  next_earnings_date: string
  guidance?: string
  days_until: number
}

export interface Recommendation {
  id: string
  symbol: string
  action: RecommendationAction
  confidence: number
  reasoning: string
  status: RecommendationStatus
  created_at: string
  updated_at?: string
}

export interface NewsEarningsData {
  news: NewsItem[]
  earnings: EarningsReport[]
  upcoming_earnings: UpcomingEarnings[]
  last_updated: string
  symbol: string
}

export interface NewsEarningsFilters {
  symbol: string
  sentiment?: SentimentType[]
  dateRange?: {
    start: string
    end: string
  }
  minRelevance?: number
}

export interface NewsEarningsState {
  selectedSymbol: string
  portfolioSymbols: string[]
  activeTab: TabType
  expandedNews: Set<string>
  filters: NewsEarningsFilters
  isLoading: boolean
  error: string | null
}

// API Response types
export interface NewsEarningsApiResponse {
  news: NewsItem[]
  earnings: EarningsReport[]
  last_updated: string
}

export interface UpcomingEarningsApiResponse {
  upcoming_earnings: UpcomingEarnings[]
}

// Utility types
export type SortDirection = 'asc' | 'desc'

export interface SortConfig {
  field: keyof NewsItem | keyof EarningsReport
  direction: SortDirection
}

export interface PaginationConfig {
  page: number
  pageSize: number
  total: number
}

// Event types for WebSocket updates
export interface NewsEarningsUpdateEvent {
  type: 'news_update' | 'earnings_update' | 'recommendation_update'
  symbol: string
  data: NewsItem | EarningsReport | Recommendation
}

// Error types
export interface NewsEarningsError {
  type: 'api_error' | 'network_error' | 'validation_error'
  message: string
  symbol?: string
  retryable: boolean
}