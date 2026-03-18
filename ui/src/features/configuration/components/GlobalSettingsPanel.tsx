import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/Label'
import { Input } from '@/components/ui/Input'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Brain, Globe, Radio, Settings, RefreshCw } from 'lucide-react'
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
          System-wide limits and agent defaults for the paper-trading operator.
          Background scheduler controls are intentionally excluded from the active product.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Radio className="w-5 h-5" />
              Quote Stream Defaults
            </CardTitle>
            <CardDescription>
              Paper-mode live P&amp;L uses the quote stream provider, independent of the future broker adapter.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="quote-stream-provider">Provider</Label>
                <Select
                  value={globalSettings.quoteStreamProvider ?? 'upstox'}
                  onValueChange={(value) => onSetGlobalSettings(prev => ({ ...prev!, quoteStreamProvider: value as GlobalConfig['quoteStreamProvider'] }))}
                >
                  <SelectTrigger id="quote-stream-provider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="upstox">Upstox</SelectItem>
                    <SelectItem value="zerodha_kite">Zerodha Kite</SelectItem>
                    <SelectItem value="none">Disabled</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500">
                  Upstox is the default zero-cost quote stream for paper mode.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quote-stream-mode">Mode</Label>
                <Select
                  value={globalSettings.quoteStreamMode ?? 'ltpc'}
                  onValueChange={(value) => onSetGlobalSettings(prev => ({ ...prev!, quoteStreamMode: value as GlobalConfig['quoteStreamMode'] }))}
                >
                  <SelectTrigger id="quote-stream-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ltpc">LTPC</SelectItem>
                    <SelectItem value="full">Full</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500">
                  LTPC is the efficient default for live paper marks.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quote-stream-limit">Watched Symbols Limit</Label>
                <Input
                  id="quote-stream-limit"
                  type="number"
                  min="1"
                  max="5000"
                  value={globalSettings.quoteStreamSymbolLimit ?? 50}
                  onChange={e => onSetGlobalSettings(prev => ({ ...prev!, quoteStreamSymbolLimit: parseInt(e.target.value, 10) || 50 }))}
                />
                <p className="text-xs text-gray-500">
                  Controls how many symbols the operator console should actively stream.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

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
