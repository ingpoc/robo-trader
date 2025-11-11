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
  TradeRequest,
  AIStatus,
  Recommendation,
  Alert,
  AgentStatus,
  AgentConfig,
  PerformanceData,
  SymbolData,
  BackgroundTaskConfig,
  AIAgentConfig,
  GlobalConfig,
  PromptConfig,
} from '@/types/api'

export const dashboardAPI = {
  getDashboardData: () => api.get<DashboardData>('/api/dashboard'),
  portfolioScan: () => api.post<{ 
    status: string
    message?: string
    auth_url?: string
    state?: string
    redirect_url?: string
    instructions?: string
    source?: string
    holdings_count?: number
    portfolio?: unknown
  }>('/api/portfolio-scan'),
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
      status: string
      schedulers: Array<{
        scheduler_id: string
        name: string
        status: string
        event_driven: boolean
        uptime_seconds: number
        jobs_processed: number
        jobs_failed: number
        active_jobs: number
        completed_jobs: number
        last_run_time: string
        execution_history?: Array<any>
        total_executions?: number
        jobs?: Array<any>
      }>
      total_schedulers: number
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

export const configurationAPI = {
  // Background tasks configuration
  getBackgroundTasks: () =>
    api.get<{ background_tasks: Record<string, BackgroundTaskConfig> }>('/api/configuration/background-tasks'),

  updateBackgroundTask: (taskName: string, config: Partial<BackgroundTaskConfig>) =>
    api.put<{ status: string; task: string }>(`/api/configuration/background-tasks/${taskName}`, config),

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

  // Configuration management
  backupConfiguration: () =>
    api.post<{ status: string; timestamp: string }>('/api/configuration/backup'),

  restoreConfiguration: (timestamp: string) =>
    api.post<{ status: string; timestamp: string }>('/api/configuration/restore', { timestamp }),

  getStatus: () =>
    api.get<{ configuration_status: Record<string, unknown> }>('/api/configuration/status'),

  // AI prompts configuration (individual)
  getPrompt: (promptName: string) =>
    api.get<PromptConfig>(`/api/configuration/prompts/${promptName}`),
  updatePrompt: (promptName: string, prompt: Partial<PromptConfig>) =>
    api.put<{ status: string; prompt: string }>(`/api/configuration/prompts/${promptName}`, prompt),

  // Manual scheduler execution
  executeScheduler: (taskName: string) =>
    api.post<{
      status: string;
      task_id: string;
      task_name: string;
      task_type: string;
      message: string;
      timestamp: string;
    }>(`/api/configuration/schedulers/${taskName}/execute`),

  // Manual AI agent execution
  executeAgent: (agentName: string) =>
    api.post<{
      status: string;
      agent_name: string;
      analysis_id: string;
      symbols_analyzed: number;
      recommendations_count: number;
      prompt_updates: number;
      message: string;
      timestamp: string;
    }>(`/api/configuration/ai-agents/${agentName}/execute`),
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

  // Get queue health status
  getHealthStatus: () =>
    api.get<{
      overall_health: 'healthy' | 'warning' | 'critical';
      queue_health: Record<QueueType, 'healthy' | 'warning' | 'critical'>;
      issues: string[];
    }>('/api/queues/health'),
}
