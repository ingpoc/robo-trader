import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Switch } from '@/components/ui/Switch'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Separator } from '@/components/ui/Separator'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Brain, Globe, Settings, RefreshCw } from 'lucide-react'
import type { GlobalConfig } from '@/types/api'

interface GlobalSettingsPanelProps {
  globalSettings: GlobalConfig | null
  isLoading: boolean
  onUpdateSetting: (section: keyof GlobalConfig, field: string, value: any) => void
  onSetGlobalSettings: React.Dispatch<React.SetStateAction<GlobalConfig | null>>
}

export const GlobalSettingsPanel: React.FC<GlobalSettingsPanelProps> = ({
  globalSettings,
  isLoading,
  onUpdateSetting,
  onSetGlobalSettings,
}) => {
  if (isLoading) {
    return (
      <div className="text-center py-8">
        <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
        <p className="text-gray-600">Loading global settings...</p>
      </div>
    )
  }

  if (!globalSettings) {
    return (
      <div className="text-center py-8">
        <Globe className="w-8 h-8 mx-auto mb-3 text-gray-400" />
        <p className="text-gray-600">Global settings not loaded</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          System-wide configuration that affects all components.
          Set global limits, defaults, and system behavior.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6">
        {/* Claude AI Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              Claude AI Settings
            </CardTitle>
            <CardDescription>
              Global Claude AI configuration and limits
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="claude-enabled">Enable Claude AI</Label>
                <p className="text-sm text-gray-600">
                  Master switch for all Claude AI usage
                </p>
              </div>
              <Switch
                id="claude-enabled"
                checked={globalSettings?.claudeUsage?.enabled ?? true}
                onCheckedChange={(checked) => onUpdateSetting('claudeUsage', 'enabled', checked)}
              />
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="token-limit">Daily Token Limit</Label>
                <Input
                  id="token-limit"
                  type="number"
                  value={globalSettings?.claudeUsage?.dailyTokenLimit ?? 50000}
                  onChange={(e) => onUpdateSetting('claudeUsage', 'dailyTokenLimit', parseInt(e.target.value))}
                  disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="cost-threshold">Cost Alert Threshold ($)</Label>
                <Input
                  id="cost-threshold"
                  type="number"
                  step="0.01"
                  value={globalSettings?.claudeUsage?.costThreshold ?? 10.00}
                  onChange={(e) => onUpdateSetting('claudeUsage', 'costThreshold', parseFloat(e.target.value))}
                  disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="cost-alerts"
                checked={globalSettings?.claudeUsage?.costAlerts ?? true}
                onCheckedChange={(checked) => onUpdateSetting('claudeUsage', 'costAlerts', checked)}
                disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
              />
              <Label htmlFor="cost-alerts">Enable cost alerts</Label>
            </div>
          </CardContent>
        </Card>

        {/* Scheduler Defaults */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Scheduler Defaults
            </CardTitle>
            <CardDescription>
              Default settings for background schedulers
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Switch
                id="market-hours"
                checked={globalSettings?.schedulerDefaults?.marketHoursOnly ?? true}
                onCheckedChange={(checked) => onUpdateSetting('schedulerDefaults', 'marketHoursOnly', checked)}
              />
              <Label htmlFor="market-hours">Run during market hours only</Label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="default-frequency">Default Frequency</Label>
                <div className="flex gap-2">
                  <Input
                    id="default-frequency"
                    type="number"
                    min="1"
                    value={globalSettings?.schedulerDefaults?.defaultFrequency ?? 30}
                    onChange={(e) => onUpdateSetting('schedulerDefaults', 'defaultFrequency', parseInt(e.target.value))}
                    className="w-20"
                  />
                  <Select
                    value={globalSettings?.schedulerDefaults?.defaultFrequencyUnit ?? 'minutes'}
                    onValueChange={(value) => onUpdateSetting('schedulerDefaults', 'defaultFrequencyUnit', value)}
                  >
                    <SelectTrigger className="w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="minutes">Minutes</SelectItem>
                      <SelectItem value="hours">Hours</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="retry-attempts">Retry Attempts</Label>
                <Input
                  id="retry-attempts"
                  type="number"
                  min="1"
                  max="10"
                  value={globalSettings?.schedulerDefaults?.retryAttempts ?? 3}
                  onChange={(e) => onUpdateSetting('schedulerDefaults', 'retryAttempts', parseInt(e.target.value))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="retry-delay">Retry Delay (minutes)</Label>
                <Input
                  id="retry-delay"
                  type="number"
                  min="1"
                  max="60"
                  value={globalSettings?.schedulerDefaults?.retryDelayMinutes ?? 5}
                  onChange={(e) => onUpdateSetting('schedulerDefaults', 'retryDelayMinutes', parseInt(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* System Limits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              System Limits
            </CardTitle>
            <CardDescription>
              Configure core system parameters and limits
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <Label htmlFor="max-turns">Max Conversation Turns</Label>
                <Input
                  id="max-turns"
                  type="number"
                  min="1"
                  max="50"
                  value={globalSettings.maxTurns ?? 5}
                  onChange={e => onSetGlobalSettings(prev => ({...prev!, maxTurns: parseInt(e.target.value)}))}
                />
                <p className="text-xs text-gray-500">Maximum number of conversation turns allowed per session</p>
              </div>
              <div>
                <Label htmlFor="risk-tolerance">Risk Tolerance (1-10)</Label>
                <Input
                  id="risk-tolerance"
                  type="number"
                  min="1"
                  max="10"
                  value={globalSettings.riskTolerance ?? 5}
                  onChange={e => onSetGlobalSettings(prev => ({...prev!, riskTolerance: parseInt(e.target.value)}))}
                />
                <p className="text-xs text-gray-500">Higher = more aggressive trading strategies</p>
              </div>
              <div>
                <Label htmlFor="daily-api-limit">Daily API Call Limit</Label>
                <Input
                  id="daily-api-limit"
                  type="number"
                  min="1"
                  value={globalSettings.dailyApiLimit ?? 25}
                  onChange={e => onSetGlobalSettings(prev => ({...prev!, dailyApiLimit: parseInt(e.target.value)}))}
                />
                <p className="text-xs text-gray-500">Maximum number of API calls allowed daily</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
