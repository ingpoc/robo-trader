import React from 'react'
import { Brain, Radio, RefreshCw } from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Switch } from '@/components/ui/switch'
import type { GlobalConfig } from '@/types/api'

interface GlobalSettingsPanelProps {
  globalSettings: GlobalConfig | null
  isLoading: boolean
  onUpdateSetting: (field: keyof GlobalConfig, value: unknown) => void
}

export const GlobalSettingsPanel: React.FC<GlobalSettingsPanelProps> = ({
  globalSettings,
  isLoading,
  onUpdateSetting,
}) => {
  if (isLoading) {
    return (
      <div className="py-8 text-center">
        <RefreshCw className="mx-auto mb-3 h-8 w-8 animate-spin text-gray-400" />
        <p className="text-gray-600">Loading global settings...</p>
      </div>
    )
  }

  if (!globalSettings) {
    return (
      <div className="py-8 text-center">
        <p className="text-gray-600">Global settings not loaded</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Global policy owns runtime defaults that apply across paper-trading accounts. Live runtime truth is shown separately and is never edited from this section.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="h-5 w-5" />
            Quote Stream Policy
          </CardTitle>
          <CardDescription>Operator-wide defaults for live quote delivery and subscription breadth.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="quote-stream-provider">Provider</Label>
            <Select
              value={globalSettings.quoteStreamProvider ?? 'upstox'}
              onValueChange={(value) => onUpdateSetting('quoteStreamProvider', value)}
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
          </div>

          <div className="space-y-2">
            <Label htmlFor="quote-stream-mode">Mode</Label>
            <Select
              value={globalSettings.quoteStreamMode ?? 'ltpc'}
              onValueChange={(value) => onUpdateSetting('quoteStreamMode', value)}
            >
              <SelectTrigger id="quote-stream-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ltpc">LTPC</SelectItem>
                <SelectItem value="full">Full</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="quote-stream-limit">Symbol limit</Label>
            <Input
              id="quote-stream-limit"
              type="number"
              min="1"
              max="5000"
              value={globalSettings.quoteStreamSymbolLimit ?? 50}
              onChange={e => onUpdateSetting('quoteStreamSymbolLimit', parseInt(e.target.value, 10) || 50)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Claude Usage Policy
          </CardTitle>
          <CardDescription>Budget and alert defaults for research and review runs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-3">
            <Switch
              id="claude-enabled"
              checked={globalSettings.claudeEnabled ?? true}
              onCheckedChange={(checked) => onUpdateSetting('claudeEnabled', checked)}
            />
            <Label htmlFor="claude-enabled">Enable Claude-powered operator runs</Label>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="claude-daily-token-limit">Daily token budget</Label>
              <Input
                id="claude-daily-token-limit"
                type="number"
                min="1000"
                step="1000"
                value={globalSettings.claudeDailyTokenLimit ?? 120000}
                onChange={e => onUpdateSetting('claudeDailyTokenLimit', parseInt(e.target.value, 10) || 120000)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="claude-cost-threshold">Cost alert threshold (USD)</Label>
              <Input
                id="claude-cost-threshold"
                type="number"
                min="1"
                step="1"
                value={globalSettings.claudeCostThreshold ?? 10}
                onChange={e => onUpdateSetting('claudeCostThreshold', parseFloat(e.target.value) || 10)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daily-api-limit">Daily API limit</Label>
              <Input
                id="daily-api-limit"
                type="number"
                min="1"
                value={globalSettings.dailyApiLimit ?? 25}
                onChange={e => onUpdateSetting('dailyApiLimit', parseInt(e.target.value, 10) || 25)}
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Switch
              id="claude-cost-alerts"
              checked={globalSettings.claudeCostAlerts ?? true}
              onCheckedChange={(checked) => onUpdateSetting('claudeCostAlerts', checked)}
            />
            <Label htmlFor="claude-cost-alerts">Raise cost alerts</Label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
