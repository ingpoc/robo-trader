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

      // Retry logic for feature registration scenarios
      let lastError: Error | null = null
      let retryCount = 0
      const maxRetries = 3
      const baseDelay = 1000 // 1 second

      while (retryCount < maxRetries) {
        try {
          await apiRequest(`/api/agents/features/${featureName}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
            headers: { 'Content-Type': 'application/json' }
          })

          // Success - break out of retry loop
          break
        } catch (err) {
          lastError = err instanceof Error ? err : new Error('Failed to update feature')

          // Check if this is a "feature not found" error that might resolve with retry
          const errorMessage = lastError.message.toLowerCase()
          const isRegistrationError = errorMessage.includes('not found') &&
                                     errorMessage.includes('feature') &&
                                     retryCount < maxRetries - 1

          if (isRegistrationError) {
            retryCount++
            const delay = baseDelay * Math.pow(2, retryCount - 1) // Exponential backoff
            console.warn(`Feature registration retry ${retryCount}/${maxRetries} for ${featureName} after ${delay}ms: ${lastError.message}`)

            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, delay))
            continue
          } else {
            // Not a registration error or out of retries - throw immediately
            throw lastError
          }
        }
      }

      // Refresh features after successful update
      await loadFeatures()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update feature'

      // Provide user-friendly error messages
      let userFriendlyError = errorMsg
      if (errorMsg.includes('not found') && errorMsg.includes('feature')) {
        userFriendlyError = `Feature '${featureName}' is being registered. Please try again in a moment.`
      } else if (errorMsg.includes('400')) {
        userFriendlyError = `Invalid configuration for '${featureName}'. Please check your settings.`
      } else if (errorMsg.includes('500')) {
        userFriendlyError = `Server error while updating '${featureName}'. Please try again.`
      }

      setError(userFriendlyError)
      console.error('Failed to update feature:', err)
      throw new Error(userFriendlyError)
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
