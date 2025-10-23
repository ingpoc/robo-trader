import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { useQueueManagement } from '@/hooks/useQueue'
import {
  Settings,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react'
import type { QueueType, QueueConfiguration } from '@/types/queue'

interface QueueConfigurationPanelProps {
  selectedQueue?: QueueType
  onQueueSelect: (queueType: QueueType) => void
}

const ConfigSection: React.FC<{
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}> = ({ title, icon, children }) => (
  <div className="space-y-4">
    <div className="flex items-center gap-2">
      {icon}
      <h3 className="text-lg font-semibold text-warmgray-900">{title}</h3>
    </div>
    <div className="space-y-4 pl-6">
      {children}
    </div>
  </div>
)

const ConfigField: React.FC<{
  label: string
  description?: string
  children: React.ReactNode
}> = ({ label, description, children }) => (
  <div className="space-y-2">
    <Label className="text-sm font-medium text-warmgray-700">{label}</Label>
    {description && (
      <p className="text-xs text-warmgray-500">{description}</p>
    )}
    {children}
  </div>
)

export const QueueConfigurationPanel: React.FC<QueueConfigurationPanelProps> = ({
  selectedQueue,
  onQueueSelect,
}) => {
  const { updateConfig } = useQueueManagement()
  const [config, setConfig] = useState<Partial<QueueConfiguration>>({})
  const [hasChanges, setHasChanges] = useState(false)

  const handleConfigChange = (key: keyof QueueConfiguration, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const handleSave = () => {
    if (!selectedQueue) return

    updateConfig.mutate({
      queue_type: selectedQueue,
      configuration: config,
    }, {
      onSuccess: () => {
        setHasChanges(false)
        setConfig({})
      }
    })
  }

  const handleReset = () => {
    setConfig({})
    setHasChanges(false)
  }

  if (!selectedQueue) {
    return (
      <Card className="card-base">
        <div className="p-12 text-center">
          <Settings className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-warmgray-900 mb-2">Select a Queue</h3>
          <p className="text-warmgray-600">Choose a queue from the overview to configure its settings.</p>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-warmgray-900">Queue Configuration</h2>
          <p className="text-sm text-warmgray-600 mt-1">
            Configure settings for {selectedQueue.replace('_', ' ')}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {hasChanges && (
            <Badge variant="warning" className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Unsaved Changes
            </Badge>
          )}

          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>

          <Button
            onClick={handleSave}
            disabled={!hasChanges || updateConfig.isPending}
            className="btn-primary"
          >
            <Save className="w-4 h-4 mr-2" />
            {updateConfig.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Basic Settings */}
        <Card className="card-base p-6">
          <ConfigSection title="Basic Settings" icon={<Settings className="w-5 h-5 text-warmgray-600" />}>
            <ConfigField
              label="Queue Enabled"
              description="Enable or disable this queue"
            >
              <Switch
                checked={config.enabled ?? true}
                onCheckedChange={(checked) => handleConfigChange('enabled', checked)}
              />
            </ConfigField>

            <ConfigField
              label="Max Concurrent Tasks"
              description="Maximum number of tasks that can run simultaneously"
            >
              <Input
                type="number"
                min="1"
                max="50"
                value={config.max_concurrent_tasks ?? 5}
                onChange={(e) => handleConfigChange('max_concurrent_tasks', parseInt(e.target.value))}
              />
            </ConfigField>

            <ConfigField
              label="Max Retries"
              description="Maximum number of retry attempts for failed tasks"
            >
              <Input
                type="number"
                min="0"
                max="10"
                value={config.max_retries ?? 3}
                onChange={(e) => handleConfigChange('max_retries', parseInt(e.target.value))}
              />
            </ConfigField>

            <ConfigField
              label="Timeout (seconds)"
              description="Maximum time allowed for task execution"
            >
              <Input
                type="number"
                min="30"
                max="3600"
                value={config.timeout_seconds ?? 300}
                onChange={(e) => handleConfigChange('timeout_seconds', parseInt(e.target.value))}
              />
            </ConfigField>
          </ConfigSection>
        </Card>

        {/* Scheduling Settings */}
        <Card className="card-base p-6">
          <ConfigSection title="Scheduling" icon={<Clock className="w-5 h-5 text-warmgray-600" />}>
            <ConfigField
              label="Scheduling Frequency"
              description="How often to check for new tasks (in seconds)"
            >
              <Input
                type="number"
                min="30"
                max="3600"
                value={config.scheduling_frequency_seconds ?? 300}
                onChange={(e) => handleConfigChange('scheduling_frequency_seconds', parseInt(e.target.value))}
              />
            </ConfigField>

            <ConfigField
              label="Batch Size"
              description="Number of tasks to process in each batch"
            >
              <Input
                type="number"
                min="1"
                max="100"
                value={config.batch_size ?? 10}
                onChange={(e) => handleConfigChange('batch_size', parseInt(e.target.value))}
              />
            </ConfigField>

            <ConfigField
              label="Priority Weights"
              description="Priority multipliers for task scheduling"
            >
              <div className="space-y-2">
                {(['low', 'medium', 'high', 'critical'] as const).map((priority) => (
                  <div key={priority} className="flex items-center gap-2">
                    <Label className="text-sm w-16 capitalize">{priority}:</Label>
                    <Input
                      type="number"
                      min="0.1"
                      max="5"
                      step="0.1"
                      value={config.priority_weights?.[priority] ?? 1}
                      onChange={(e) => handleConfigChange('priority_weights', {
                        ...config.priority_weights,
                        [priority]: parseFloat(e.target.value)
                      })}
                      className="w-20"
                    />
                  </div>
                ))}
              </div>
            </ConfigField>
          </ConfigSection>
        </Card>

        {/* Circuit Breaker Settings */}
        <Card className="card-base p-6">
          <ConfigSection title="Circuit Breaker" icon={<Zap className="w-5 h-5 text-warmgray-600" />}>
            <ConfigField
              label="Circuit Breaker Enabled"
              description="Enable automatic failure protection"
            >
              <Switch
                checked={config.circuit_breaker_enabled ?? true}
                onCheckedChange={(checked) => handleConfigChange('circuit_breaker_enabled', checked)}
              />
            </ConfigField>

            <ConfigField
              label="Failure Threshold"
              description="Number of failures before circuit breaker activates"
            >
              <Input
                type="number"
                min="3"
                max="20"
                value={config.circuit_breaker_threshold ?? 5}
                onChange={(e) => handleConfigChange('circuit_breaker_threshold', parseInt(e.target.value))}
                disabled={!config.circuit_breaker_enabled}
              />
            </ConfigField>

            <ConfigField
              label="Recovery Timeout"
              description="Time to wait before attempting recovery (seconds)"
            >
              <Input
                type="number"
                min="30"
                max="3600"
                value={config.circuit_breaker_timeout_seconds ?? 300}
                onChange={(e) => handleConfigChange('circuit_breaker_timeout_seconds', parseInt(e.target.value))}
                disabled={!config.circuit_breaker_enabled}
              />
            </ConfigField>
          </ConfigSection>
        </Card>

        {/* Queue Selection */}
        <Card className="card-base p-6">
          <ConfigSection title="Queue Selection" icon={<CheckCircle className="w-5 h-5 text-warmgray-600" />}>
            <ConfigField
              label="Select Queue to Configure"
              description="Choose which queue configuration to modify"
            >
              <Select
                value={selectedQueue}
                onValueChange={(value) => onQueueSelect(value as QueueType)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select queue" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PORTFOLIO_SCHEDULER">Portfolio Scheduler</SelectItem>
                  <SelectItem value="DATA_FETCHER_SCHEDULER">Data Fetcher Scheduler</SelectItem>
                  <SelectItem value="AI_ANALYSIS_QUEUE">AI Analysis Queue</SelectItem>
                </SelectContent>
              </Select>
            </ConfigField>

            <div className="mt-4 p-4 bg-warmgray-50 rounded-lg">
              <h4 className="text-sm font-medium text-warmgray-900 mb-2">Configuration Status</h4>
              <div className="flex items-center gap-2">
                {updateConfig.isSuccess && !hasChanges && (
                  <Badge variant="success" className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    Saved
                  </Badge>
                )}
                {updateConfig.isError && (
                  <Badge variant="error" className="flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Save Failed
                  </Badge>
                )}
                {updateConfig.isPending && (
                  <Badge variant="secondary">Saving...</Badge>
                )}
              </div>
              {updateConfig.error && (
                <p className="text-xs text-red-600 mt-2">
                  {updateConfig.error.message}
                </p>
              )}
            </div>
          </ConfigSection>
        </Card>
      </div>
    </div>
  )
}