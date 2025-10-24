/**
 * useAgentConfig Hook
 * Manages agent configuration state and API calls
 */

import { useState, useEffect } from 'react'
import { apiRequest } from '@/api/client'
import type { AgentFeaturesConfig, AgentFeatureConfig } from '../types'

const FREQUENCY_OPTIONS = [
  { label: 'Daily' as const, value: 86400 },
  { label: 'Weekly' as const, value: 604800 },
  { label: 'Monthly' as const, value: 2592000 },
]

export const getFrequencyLabel = (seconds: number): string => {
  const option = FREQUENCY_OPTIONS.find(opt => opt.value === seconds)
  return option ? option.label : `${seconds}s`
}

export const getFrequencySeconds = (label: string): number => {
  const option = FREQUENCY_OPTIONS.find(opt => opt.label === label)
  return option ? option.value : 86400
}

export interface UseAgentConfigReturn {
  features: AgentFeaturesConfig | null
  loading: boolean
  error: string | null
  updateFeature: (featureName: string, updates: Partial<AgentFeatureConfig>) => Promise<void>
  refresh: () => Promise<void>
}

export const useAgentConfig = (): UseAgentConfigReturn => {
  const [features, setFeatures] = useState<AgentFeaturesConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadFeatures()
  }, [])

  const loadFeatures = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiRequest<any>('/api/agents/features')

      // Map API response to expected format
      const features: AgentFeaturesConfig = {}
      if (data.agents) {
        Object.entries(data.agents).forEach(([name, agent]: [string, any]) => {
          features[name] = {
            enabled: agent.enabled || false,
            config: agent.config || {},
            use_claude: true,
            frequency_seconds: 86400,
            priority: 'medium' as const
          }
        })
      }
      setFeatures(features)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load agent configuration'
      setError(errorMsg)
      console.error('Failed to load agent features:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateFeature = async (featureName: string, updates: Partial<AgentFeatureConfig>) => {
    try {
      // If disabling, automatically disable use_claude
      if (updates.enabled === false) {
        updates.use_claude = false
      }

      await apiRequest(`/api/agents/features/${featureName}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
        headers: { 'Content-Type': 'application/json' }
      })

      await loadFeatures()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update feature'
      setError(errorMsg)
      console.error('Failed to update feature:', err)
      throw err
    }
  }

  return {
    features,
    loading,
    error,
    updateFeature,
    refresh: loadFeatures
  }
}
