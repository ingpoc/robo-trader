import type {
  QueueType,
  QueueStatus,
  QueueTask,
  TaskExecutionHistory,
  QueuePerformanceMetrics,
  QueueStats,
  TaskFilter,
  QueueTriggerRequest,
  QueueConfigurationUpdate,
  QueueConfiguration,
} from '@/types/queue'
import { api } from './client'
import type {
  DashboardData,
  AIStatus,
  Recommendation,
  Alert,
  SymbolData,
  AIAgentConfig,
  AccountPolicy,
  ConfigurationStatus,
  GlobalConfig,
} from '@/types/api'
import type { PaperTradingOperatorSnapshot, RuntimeHealthResponse } from '@/features/paper-trading/types'

export const dashboardAPI = {
  getDashboardData: () => api.get<DashboardData>('/api/dashboard'),
}

export const runtimeAPI = {
  getHealth: () => api.get<RuntimeHealthResponse>('/api/health'),
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

export const alertsAPI = {
  getActive: () => api.get<{ alerts: Alert[] }>('/api/alerts/active'),
  handleAction: (alertId: string, action: string) =>
    api.post<{ status: string }>(`/api/alerts/${alertId}/action`, { action }),
}

export const emergencyAPI = {
  stop: () => api.post<{ status: string }>('/api/emergency/stop'),
  resume: () => api.post<{ status: string }>('/api/emergency/resume'),
}

export const configurationAPI = {
  // AI agents configuration
  getAIAgents: () =>
    api.get<{ ai_agents: Record<string, AIAgentConfig> }>('/api/configuration/ai-agents'),

  updateAIAgent: (agentName: string, config: Partial<AIAgentConfig>) =>
    api.put<{ status: string; agent: string }>(`/api/configuration/ai-agents/${agentName}`, config),

  // Global settings configuration
  getGlobalSettings: () =>
    api.get<{ global_settings: GlobalConfig }>('/api/configuration/global-settings'),

  updateGlobalSettings: (settings: Partial<GlobalConfig>) =>
    api.put<{ status: string }>('/api/configuration/global-settings', settings),

  getStatus: () =>
    api.get<{ configuration_status: ConfigurationStatus }>('/api/configuration/status'),

  getAccountPolicy: (accountId: string) =>
    api.get<{ success: boolean; account_id: string; policy: AccountPolicy }>(`/api/paper-trading/accounts/${accountId}/policy`),

  updateAccountPolicy: (accountId: string, policy: Partial<AccountPolicy>) =>
    api.put<{ success: boolean; account_id: string; policy: AccountPolicy }>(`/api/paper-trading/accounts/${accountId}/policy`, policy),
}

export const operatorAPI = {
  getOperatorSnapshot: (accountId: string) =>
    api.get<PaperTradingOperatorSnapshot>(`/api/paper-trading/accounts/${accountId}/operator-snapshot`),
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

export const symbolsAPI = {
  searchSymbols: (query: string, limit: number = 20) =>
    api.get<{ symbols: SymbolData[], total: number }>(`/api/symbols/search?q=${encodeURIComponent(query)}&limit=${limit}`),
}

export const queueAPI = {
  // Get all queue statuses
  getQueueStatuses: () =>
    api.get<{ queues: QueueStatus[], stats: QueueStats }>('/api/queues/status'),

  // Get specific queue status
  getQueueStatus: (queueType: QueueType) =>
    api.get<{ queue: QueueStatus }>(`/api/queues/status/${queueType}`),

  // Get queue tasks with filtering
  getQueueTasks: (filters?: TaskFilter) => {
    const params = new URLSearchParams();
    if (filters?.queue_type) params.append('queue_type', filters.queue_type);
    if (filters?.status?.length) params.append('status', filters.status.join(','));
    if (filters?.priority?.length) params.append('priority', filters.priority.join(','));
    if (filters?.task_type?.length) params.append('task_type', filters.task_type.join(','));
    if (filters?.date_range) {
      params.append('start_date', filters.date_range.start);
      params.append('end_date', filters.date_range.end);
    }
    return api.get<{ tasks: QueueTask[], total: number }>(`/api/queues/tasks?${params}`);
  },

  // Get task execution history
  getTaskHistory: (queueType?: QueueType, limit: number = 100) =>
    api.get<{ history: TaskExecutionHistory[] }>(`/api/queues/history?queue_type=${queueType || ''}&limit=${limit}`),

  // Get queue performance metrics
  getPerformanceMetrics: (queueType?: QueueType, hours: number = 24) =>
    api.get<{ metrics: QueuePerformanceMetrics[] }>(`/api/queues/metrics?queue_type=${queueType || ''}&hours=${hours}`),

  // Trigger manual task execution
  triggerTask: (request: QueueTriggerRequest) =>
    api.post<{ task_id: string; status: string }>('/api/queues/trigger', request),

  // Update queue configuration
  updateConfiguration: (update: QueueConfigurationUpdate) =>
    api.put<{ status: string; configuration: QueueConfiguration }>('/api/queues/config', update),

  // Get queue configuration
  getConfiguration: (queueType: QueueType) =>
    api.get<{ configuration: QueueConfiguration }>(`/api/queues/config/${queueType}`),

  // Pause/resume queue
  pauseQueue: (queueType: QueueType) =>
    api.post<{ status: string }>('/api/queues/pause', { queue_type: queueType }),

  resumeQueue: (queueType: QueueType) =>
    api.post<{ status: string }>('/api/queues/resume', { queue_type: queueType }),

  // Cancel task
  cancelTask: (taskId: string) =>
    api.post<{ status: string }>(`/api/queues/tasks/${taskId}/cancel`),

  // Retry failed task
  retryTask: (taskId: string) =>
    api.post<{ status: string }>(`/api/queues/tasks/${taskId}/retry`),

  // Clear completed tasks
  clearCompletedTasks: (queueType?: QueueType) =>
    api.post<{ status: string; cleared_count: number }>('/api/queues/clear-completed', { queue_type: queueType }),

}
