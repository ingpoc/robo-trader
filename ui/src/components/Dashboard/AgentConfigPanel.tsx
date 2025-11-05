import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsAPI } from '@/api/endpoints'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/hooks/use-toast'
import type { AgentConfig } from '@/types/api'

interface AgentConfigPanelProps {
  agentName: string
  onClose?: () => void
}

export function AgentConfigPanel({ agentName, onClose }: AgentConfigPanelProps) {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: configData, isLoading } = useQuery({
    queryKey: ['agent-config', agentName],
    queryFn: () => agentsAPI.getConfig(agentName),
  })

  const [config, setConfig] = useState<Partial<AgentConfig>>({
    enabled: true,
    frequency: 'realtime',
  })

  useEffect(() => {
    if (configData?.config) {
      setConfig(configData.config)
    }
  }, [configData])

  const updateConfig = useMutation({
    mutationFn: (newConfig: AgentConfig) => agentsAPI.updateConfig(agentName, newConfig),
    onSuccess: () => {
      toast({
        title: 'Configuration Updated',
        description: `${agentName} settings saved successfully`,
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['agent-config', agentName] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      onClose?.()
    },
    onError: (error) => {
      toast({
        title: 'Update Failed',
        description: error instanceof Error ? error.message : 'Failed to update configuration',
        variant: 'destructive',
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateConfig.mutate(config as AgentConfig)
  }

  const handleChange = (field: keyof AgentConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-sm text-warmgray-600">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4 bg-white border border-warmgray-200 rounded">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-warmgray-900 capitalize">
          {agentName.replace('_', ' ')} Configuration
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-warmgray-400 hover:text-warmgray-600"
          >
            ✕
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="enabled"
            checked={config.enabled || false}
            onChange={(e) => handleChange('enabled', e.target.checked)}
            className="rounded border-warmgray-300"
          />
          <label htmlFor="enabled" className="text-sm font-medium text-warmgray-700">
            Enable Agent
          </label>
        </div>

        <div>
          <label htmlFor="frequency" className="block text-sm font-medium text-warmgray-700 mb-1">
            Update Frequency
          </label>
          <Select
            id="frequency"
            value={config.frequency || 'realtime'}
            onChange={(e) => handleChange('frequency', e.target.value)}
          >
            <option value="realtime">Real-time</option>
            <option value="1min">Every 1 minute</option>
            <option value="5min">Every 5 minutes</option>
            <option value="15min">Every 15 minutes</option>
            <option value="1hour">Every hour</option>
            <option value="daily">Daily</option>
          </Select>
        </div>

        {/* Agent-specific configuration fields */}
        {agentName === 'risk_manager' && (
          <>
            <div>
              <label htmlFor="max_position_size" className="block text-sm font-medium text-warmgray-700 mb-1">
                Max Position Size (%)
              </label>
              <Input
                id="max_position_size"
                type="number"
                value={(config as any).max_position_size || 10}
                onChange={(e) => handleChange('max_position_size' as any, parseFloat(e.target.value))}
              />
            </div>
            <div>
              <label htmlFor="risk_per_trade" className="block text-sm font-medium text-warmgray-700 mb-1">
                Risk per Trade (%)
              </label>
              <Input
                id="risk_per_trade"
                type="number"
                step="0.1"
                value={(config as any).risk_per_trade || 1}
                onChange={(e) => handleChange('risk_per_trade' as any, parseFloat(e.target.value))}
              />
            </div>
          </>
        )}

        {agentName === 'technical_analyst' && (
          <div>
            <label htmlFor="indicators" className="block text-sm font-medium text-warmgray-700 mb-1">
              Technical Indicators
            </label>
            <div className="flex flex-wrap gap-2">
              {['RSI', 'MACD', 'Bollinger_Bands', 'Moving_Averages'].map(indicator => (
                <label key={indicator} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
                    checked={((config as any).indicators || []).includes(indicator)}
                    onChange={(e) => {
                      const current = (config as any).indicators || []
                      const updated = e.target.checked
                        ? [...current, indicator]
                        : current.filter((i: string) => i !== indicator)
                      handleChange('indicators' as any, updated)
                    }}
                    className="rounded border-warmgray-300"
                  />
                  {indicator.replace('_', ' ')}
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-4">
          <Button type="submit" disabled={updateConfig.isPending}>
            {updateConfig.isPending ? 'Saving...' : 'Save Configuration'}
          </Button>
          {onClose && (
            <Button type="button" variant="tertiary" onClick={onClose}>
              Cancel
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}