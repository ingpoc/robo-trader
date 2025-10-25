import { API_ENDPOINTS } from './constants'

export const API_BASE_URL = 'http://localhost:8000'

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      console.error('API request failed:', error)
      return { error: error instanceof Error ? error.message : 'Unknown error' }
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()

// Portfolio API
export const portfolioApi = {
  getPortfolio: () => apiClient.get('/api/portfolio'),
  scanPortfolio: () => apiClient.post('/api/portfolio/scan'),
  getAnalytics: (period: string) => apiClient.get(`/api/analytics?period=${period}`),
}

// Agent API
export const agentApi = {
  getAgents: () => apiClient.get('/api/agents'),
  getAgent: (id: string) => apiClient.get(`/api/agents/${id}`),
  updateAgent: (id: string, data: any) => apiClient.put(`/api/agents/${id}`, data),
}

// Trading API
export const tradingApi = {
  getTrades: () => apiClient.get('/api/trades'),
  executeTrade: (trade: any) => apiClient.post('/api/trades', trade),
}

// Paper Trading API
export const paperTradingApi = {
  getAccount: () => apiClient.get('/api/paper-trading/account'),
  getPositions: () => apiClient.get('/api/paper-trading/positions'),
  executeTrade: (trade: any) => apiClient.post('/api/paper-trading/trades', trade),
}

// News & Earnings API
export const newsEarningsApi = {
  getNews: (symbol?: string) => apiClient.get(`/api/news${symbol ? `?symbol=${symbol}` : ''}`),
  getEarnings: (symbol?: string) => apiClient.get(`/api/earnings${symbol ? `?symbol=${symbol}` : ''}`),
  getUpcomingEarnings: () => apiClient.get('/api/earnings/upcoming'),
  getRecommendations: (symbol?: string) => apiClient.get(`/api/recommendations${symbol ? `?symbol=${symbol}` : ''}`),
}

// Fundamentals API
export const fundamentalsApi = {
  getFundamentals: (symbol: string) => apiClient.get(`/api/fundamentals/${symbol}`),
}

// Logs API
export const logsApi = {
  getLogs: (type?: string, limit?: number) =>
    apiClient.get(`/api/logs${type ? `?type=${type}` : ''}${limit ? `${type ? '&' : '?'}limit=${limit}` : ''}`),
}

// Config API
export const configApi = {
  getConfig: () => apiClient.get('/api/config'),
  updateConfig: (config: any) => apiClient.put('/api/config', config),
}

// Claude Transparency API
export const claudeTransparencyApi = {
  getTransparencyData: () => apiClient.get('/api/claude-transparency'),
}