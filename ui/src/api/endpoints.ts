import { api } from './client'
import type {
  DashboardData,
  TradeRequest,
  AIStatus,
  Recommendation,
  Alert,
  AgentStatus,
  AgentConfig,
  PerformanceData,
} from '@/types/api'

export const dashboardAPI = {
  getDashboardData: () => api.get<DashboardData>('/api/dashboard'),
  portfolioScan: () => api.post<{ status: string }>('/api/portfolio-scan'),
  marketScreening: () => api.post<{ status: string }>('/api/market-screening'),
}

export const tradingAPI = {
  executeTrade: (trade: TradeRequest) =>
    api.post<{ status: string; intent_id?: string; reasons?: string[] }>(
      '/api/manual-trade',
      trade
    ),
}

export const aiAPI = {
  getStatus: () => api.get<AIStatus>('/api/ai/status'),
  planDaily: () => api.post<{ status: string }>('/api/ai/plan-daily'),
  planWeekly: () => api.post<{ status: string }>('/api/ai/plan-weekly'),
  getRecommendations: () =>
    api.get<{ recommendations: Recommendation[] }>('/api/ai/recommendations'),
}

export const recommendationsAPI = {
  approve: (id: string) =>
    api.post<{ status: string; recommendation_id: string }>(
      `/api/recommendations/approve/${id}`
    ),
  reject: (id: string) =>
    api.post<{ status: string; recommendation_id: string }>(
      `/api/recommendations/reject/${id}`
    ),
  discuss: (id: string) =>
    api.post<{ status: string; recommendation_id: string }>(
      `/api/recommendations/discuss/${id}`
    ),
}

export const monitoringAPI = {
  getSystemStatus: () =>
    api.get<{
      status: string
      agents: Record<string, unknown>
      scheduler: Record<string, unknown>
    }>('/api/monitoring/status'),
  getSchedulerStatus: () =>
    api.get<{
      running: boolean
      jobs: Array<{ id: string; next_run: string; enabled: boolean }>
    }>('/api/monitoring/scheduler'),
}

export const alertsAPI = {
  getActive: () => api.get<{ alerts: Alert[] }>('/api/alerts/active'),
  handleAction: (alertId: string, action: string) =>
    api.post<{ status: string }>(`/api/alerts/${alertId}/action`, { action }),
}

export const agentsAPI = {
  getStatus: () =>
    api.get<{ agents: Record<string, AgentStatus> }>('/api/agents/status'),
  getTools: (agentName: string) =>
    api.get<{ tools: string[] }>(`/api/agents/${agentName}/tools`),
  getConfig: (agentName: string) =>
    api.get<{ config: AgentConfig }>(`/api/agents/${agentName}/config`),
  updateConfig: (agentName: string, config: AgentConfig) =>
    api.post<{ status: string; agent: string; config: AgentConfig }>(
      `/api/agents/${agentName}/config`,
      config
    ),
}

export const emergencyAPI = {
  stop: () => api.post<{ status: string }>('/api/emergency/stop'),
  resume: () => api.post<{ status: string }>('/api/emergency/resume'),
}

export const configAPI = {
  get: () => api.get<Record<string, unknown>>('/api/config'),
  update: (config: Record<string, unknown>) =>
    api.post<{ status: string }>('/api/config', config),
}

export const analyticsAPI = {
  getPortfolioDeep: () =>
    api.get<PerformanceData>('/api/analytics/portfolio-deep'),
  getPerformance: (period: string) =>
    api.get<PerformanceData>(`/api/analytics/performance/${period}`),
  optimizeStrategy: (strategyName: string) =>
    api.post<{ status: string; optimization: Record<string, unknown> }>(
      '/api/analytics/optimize-strategy',
      { strategy_name: strategyName }
    ),
}

export const chatAPI = {
  query: (query: string, sessionId?: string) =>
    api.post<{
      response: string
      session_id: string
      intents: string[]
      actions: string[]
      timestamp: string
    }>('/api/chat/query', { query, session_id: sessionId }),
}

export const logsAPI = {
  getLogs: (limit: number = 100) => api.get<{ logs: Array<{
    timestamp: string
    level: string
    message: string
    source?: string
  }> }>(`/api/logs?limit=${limit}`),
  logError: (error: {
    level: string
    message: string
    context?: Record<string, unknown>
    stack_trace?: string
  }) => api.post<{ status: string; timestamp: string }>('/api/logs/errors', error),
}

export const newsEarningsAPI = {
  getNews: (symbol: string, limit: number = 20) =>
    api.get<{ news: Array<{
      symbol: string
      title: string
      summary: string
      content?: string
      source?: string
      sentiment: string
      relevance_score: number
      published_at: string
      fetched_at: string
      citations?: string[]
      created_at: string
    }> }>(`/api/news/${symbol}?limit=${limit}`),

  getEarnings: (symbol: string, limit: number = 10) =>
    api.get<{ earnings: Array<{
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
    }> }>(`/api/earnings/${symbol}?limit=${limit}`),

  getNewsAndEarnings: (symbol: string, newsLimit: number = 10, earningsLimit: number = 5) =>
    api.get<{
      symbol: string
      news: Array<{
        symbol: string
        title: string
        summary: string
        content?: string
        source?: string
        sentiment: string
        relevance_score: number
        published_at: string
        fetched_at: string
        citations?: string[]
        created_at: string
      }>
      earnings: Array<{
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
      }>
      last_updated: string
    }>(`/api/news-earnings/${symbol}?news_limit=${newsLimit}&earnings_limit=${earningsLimit}`),

  getUpcomingEarnings: (daysAhead: number = 30) =>
    api.get<{ upcoming_earnings: Array<{
      symbol: string
      fiscal_period: string
      next_earnings_date: string
      guidance?: string
    }> }>(`/api/earnings/upcoming?days_ahead=${daysAhead}`),
}
