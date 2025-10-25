/**
 * Agents Feature Index
 * Central export point for agents feature
 */

export { AgentsFeature } from './AgentsFeature'
export type { AgentsFeatureProps } from './AgentsFeature'

// Re-export types
export type {
  AgentStatus,
  AgentsData,
  AgentFeatureConfig,
  AgentFeaturesConfig,
  FrequencyOption,
  AgentMetrics
} from './types'

// Re-export hooks
export { useAgentConfig, getFrequencyLabel, getFrequencySeconds } from './hooks/useAgentConfig'
