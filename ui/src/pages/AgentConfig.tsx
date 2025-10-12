import { useState, useEffect } from 'react'
import { apiRequest } from '@/api/client'
import type { AgentFeaturesConfig, AgentFeatureConfig } from '@/types/api'

// Frequency mapping utilities
const FREQUENCY_OPTIONS = [
  { label: 'Daily', value: 86400 },
  { label: 'Weekly', value: 604800 },
  { label: 'Monthly', value: 2592000 },
] as const

const getFrequencyLabel = (seconds: number): string => {
  const option = FREQUENCY_OPTIONS.find(opt => opt.value === seconds)
  return option ? option.label : `${seconds}s`
}

const getFrequencySeconds = (label: string): number => {
  const option = FREQUENCY_OPTIONS.find(opt => opt.label === label)
  return option ? option.value : 86400 // default to daily
}

export function AgentConfig() {
  const [features, setFeatures] = useState<AgentFeaturesConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadFeatures()
  }, [])

  const loadFeatures = async () => {
    try {
      const data = await apiRequest<{ features: AgentFeaturesConfig }>('/api/agents/features')
      setFeatures(data.features)
    } catch (error) {
      console.error('Failed to load agent features:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateFeature = async (featureName: string, updates: Partial<AgentFeatureConfig>) => {
    try {
      await apiRequest(`/api/agents/features/${featureName}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
        headers: { 'Content-Type': 'application/json' }
      })
      await loadFeatures()
    } catch (error) {
      console.error('Failed to update feature:', error)
    }
  }

  if (loading || !features) {
    return <div>Loading...</div>
  }

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agent Configuration</h1>
        </div>
      </div>

      {Object.entries(features).map(([featureName, config]) => (
        <FeatureCard
          key={featureName}
          featureName={featureName}
          config={config}
          onUpdate={(updates) => updateFeature(featureName, updates)}
        />
      ))}
    </div>
  )
}

function FeatureCard({ featureName, config, onUpdate }: {
  featureName: string
  config: AgentFeatureConfig
  onUpdate: (updates: Partial<AgentFeatureConfig>) => void
}) {
  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">{featureName.replace(/_/g, ' ')}</h3>
        <label className="flex items-center gap-2">
          <span>Enabled</span>
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) => onUpdate({ enabled: e.target.checked })}
          />
        </label>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="flex items-center gap-2">
            <span>Use Claude</span>
            <input
              type="checkbox"
              checked={config.use_claude}
              onChange={(e) => onUpdate({ use_claude: e.target.checked })}
              disabled={!config.enabled}
            />
          </label>
        </div>

        <div>
          <label>
            <span className="block mb-1">
              Frequency {['portfolio_scan', 'market_screening', 'earnings_check', 'news_monitoring', 'ai_daily_planning'].includes(featureName) ? '' : '(seconds)'}
            </span>
            {['portfolio_scan', 'market_screening', 'earnings_check', 'news_monitoring', 'ai_daily_planning'].includes(featureName) ? (
              <select
                value={getFrequencyLabel(config.frequency_seconds)}
                onChange={(e) => onUpdate({ frequency_seconds: getFrequencySeconds(e.target.value) })}
                disabled={!config.enabled}
                className="w-full border rounded px-2 py-1"
              >
                {FREQUENCY_OPTIONS.map(option => (
                  <option key={option.value} value={option.label}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="number"
                value={config.frequency_seconds}
                onChange={(e) => onUpdate({ frequency_seconds: parseInt(e.target.value) })}
                disabled={!config.enabled}
                className="w-full border rounded px-2 py-1"
                placeholder="seconds"
              />
            )}
          </label>
        </div>

        <div>
          <label>
            <span className="block mb-1">Priority</span>
            <select
              value={config.priority}
              onChange={(e) => onUpdate({ priority: e.target.value as any })}
              disabled={!config.enabled}
              className="w-full border rounded px-2 py-1"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  )
}
