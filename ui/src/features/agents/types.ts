/**
 * Agents Feature Types
 * Data structures for agent management and configuration
 */

export interface AgentStatus {
  status: 'running' | 'idle' | 'error' | 'pending'
  message: string
  tasks_completed: number
  uptime?: string
  // Claude Paper Trader specific
  win_rate?: number
  pnl?: number
  tokens_used?: number
}

export interface AgentsData {
  [agentName: string]: AgentStatus
}

export interface AgentFeatureConfig {
  enabled: boolean
  config: Record<string, any>
  use_claude: boolean
  frequency_seconds: number
  priority: 'low' | 'medium' | 'high' | 'critical'
}

export interface AgentFeaturesConfig {
  [featureName: string]: AgentFeatureConfig
}

export interface FrequencyOption {
  label: 'Daily' | 'Weekly' | 'Monthly'
  value: number
}

export interface AgentMetrics {
  win_rate: number
  pnl: number
  tokens_used: number
  max_tokens: number
}
