/**
 * Stock Discovery Types
 * PT-002: Autonomous Stock Discovery
 */

export interface DiscoveryWatchlistItem {
  symbol: string
  company_name: string
  sector: string
  recommendation: 'BUY' | 'SELL' | 'HOLD'
  confidence_score: number
  discovery_date: string
  current_price: number | null
  status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED'
  created_at: string
  updated_at: string | null
}

export interface DiscoverySession {
  id: string
  session_date: string
  session_type: 'daily_screen' | 'sector_analysis' | 'market_scan'
  total_stocks_scanned: number
  stocks_discovered: number
  high_potential_stocks: number
  session_duration_ms: number
  session_status: 'RUNNING' | 'COMPLETED' | 'FAILED'
  created_at: string
  completed_at: string | null
}

export interface DiscoveryStatus {
  discovery_running: boolean
  current_session: DiscoverySession | null
  total_sessions: number
  completed_sessions: number
  total_stocks_scanned: number
  total_stocks_discovered: number
  recent_sessions: DiscoverySession[]
}

export interface DiscoveryWatchlistResponse {
  watchlist: DiscoveryWatchlistItem[]
  total_stocks: number
}

export interface DiscoverySessionsResponse {
  sessions: DiscoverySession[]
  total_sessions: number
}

export interface TriggerDiscoveryResponse {
  success: boolean
  message: string
  session_id: string | null
  session_type?: string
  sector?: string
}

export type DiscoveryRequestType = 'daily_screen' | 'sector_analysis'

export interface DiscoveryRequest {
  type: DiscoveryRequestType
  sector?: string
}