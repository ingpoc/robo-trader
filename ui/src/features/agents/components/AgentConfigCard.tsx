/**
 * Agent Config Card Component
 * Form for configuring individual agent features
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { AlertCircle } from 'lucide-react'
import { getFrequencyLabel, getFrequencySeconds } from '../hooks/useAgentConfig'
import type { AgentFeatureConfig } from '../types'

const FREQUENCY_OPTIONS = [
  { label: 'Daily', value: 86400 },
  { label: 'Weekly', value: 604800 },
  { label: 'Monthly', value: 2592000 },
]

const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'] as const

const PRESET_FEATURES = [
  'portfolio_scan',
  'market_screening',
  'earnings_check',
  'news_monitoring',
  'ai_daily_planning'
]

export interface AgentConfigCardProps {
  featureName: string
  config: AgentFeatureConfig
  onUpdate: (updates: Partial<AgentFeatureConfig>) => Promise<void>
  isUpdating?: boolean
  error?: string | null
}

export const AgentConfigCard: React.FC<AgentConfigCardProps> = ({
  featureName,
  config,
  onUpdate,
  isUpdating = false,
  error = null
}) => {
  const [localError, setLocalError] = useState<string | null>(null)

  const isPresetFeature = PRESET_FEATURES.includes(featureName)

  const handleUpdate = async (updates: Partial<AgentFeatureConfig>) => {
    try {
      setLocalError(null)
      await onUpdate(updates)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update configuration'
      setLocalError(message)
    }
  }

  return (
    <Card className="p-4 space-y-4 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100">
          {featureName.replace(/_/g, ' ')}
        </h3>
        <label className="flex items-center gap-2 cursor-pointer">
          <span className="text-warmgray-700 dark:text-warmgray-300 text-sm">Enabled</span>
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) => {
              const updates: Partial<AgentFeatureConfig> = { enabled: e.target.checked }
              if (!e.target.checked) {
                updates.use_claude = false
              }
              handleUpdate(updates)
            }}
            disabled={isUpdating}
            className="w-4 h-4 accent-copper-500"
            aria-label={`Enable ${featureName}`}
          />
        </label>
      </div>

      {/* Configuration Grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Use Claude Toggle */}
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-warmgray-700 dark:text-warmgray-300 text-sm">Use Claude</span>
            <input
              type="checkbox"
              checked={config.use_claude}
              onChange={(e) => handleUpdate({ use_claude: e.target.checked })}
              disabled={!config.enabled || isUpdating}
              className="w-4 h-4 accent-copper-500"
              aria-label={`Use Claude for ${featureName}`}
            />
          </label>
        </div>

        {/* Frequency Selector */}
        <div>
          <label className="block text-sm font-medium text-warmgray-700 dark:text-warmgray-300 mb-1">
            Frequency {!isPresetFeature && '(seconds)'}
          </label>
          {isPresetFeature ? (
            <select
              value={getFrequencyLabel(config.frequency_seconds)}
              onChange={(e) => handleUpdate({ frequency_seconds: getFrequencySeconds(e.target.value) })}
              disabled={!config.enabled || isUpdating}
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm"
              aria-label={`Frequency for ${featureName}`}
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
              onChange={(e) => handleUpdate({ frequency_seconds: parseInt(e.target.value) || 0 })}
              disabled={!config.enabled || isUpdating}
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm"
              placeholder="seconds"
              aria-label={`Frequency in seconds for ${featureName}`}
            />
          )}
        </div>

        {/* Priority Selector */}
        <div>
          <label className="block text-sm font-medium text-warmgray-700 dark:text-warmgray-300 mb-1">
            Priority
          </label>
          <select
            value={config.priority}
            onChange={(e) => handleUpdate({ priority: e.target.value as any })}
            disabled={!config.enabled || isUpdating}
            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm"
            aria-label={`Priority for ${featureName}`}
          >
            {PRIORITY_OPTIONS.map(priority => (
              <option key={priority} value={priority}>
                {priority.charAt(0).toUpperCase() + priority.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error Message */}
      {(error || localError) && (
        <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-950 rounded-md">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-600">{error || localError}</p>
        </div>
      )}

      {/* Status */}
      {isUpdating && (
        <div className="text-sm text-warmgray-500 italic">
          Updating...
        </div>
      )}
    </Card>
  )
}

export default AgentConfigCard
