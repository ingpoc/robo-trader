/**
 * AI Automation Control Panel
 * Toggle AI trading, emergency stop, and risk limits configuration
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/Input'
import {
  Bot, AlertOctagon, Shield, Settings, Activity,
  TrendingUp, Clock, CheckCircle, XCircle, RefreshCw
} from 'lucide-react'
import { useAIAutomation, type AIAutomationConfig } from '../hooks/useAIAutomation'

export const AIAutomationControlPanel: React.FC = () => {
  const {
    config,
    isLoading,
    error,
    refetch,
    toggleAITrading,
    triggerEmergencyStop,
    resetEmergencyStop,
    updateRiskLimits
  } = useAIAutomation()

  const [showRiskSettings, setShowRiskSettings] = useState(false)
  const [isToggling, setIsToggling] = useState(false)

  const handleToggle = async (enabled: boolean) => {
    setIsToggling(true)
    await toggleAITrading(enabled)
    setIsToggling(false)
  }

  const handleEmergencyStop = async () => {
    if (confirm('Are you sure you want to activate emergency stop? This will halt all AI trading.')) {
      await triggerEmergencyStop()
    }
  }

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Loading AI automation status...
        </div>
      </Card>
    )
  }

  if (error || !config) {
    return (
      <Card className="p-6 border-destructive">
        <div className="flex items-center gap-2 text-destructive">
          <XCircle className="w-5 h-5" />
          <span>Failed to load AI automation: {error}</span>
          <Button variant="outline" size="sm" onClick={refetch}>Retry</Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${config.ai_trading_enabled ? 'bg-green-500/10' : 'bg-muted'}`}>
              <Bot className={`w-5 h-5 ${config.ai_trading_enabled ? 'text-green-500' : 'text-muted-foreground'}`} />
            </div>
            <div>
              <h3 className="font-semibold">AI Paper Trading Control</h3>
              <p className="text-sm text-muted-foreground">
                {config.ai_trading_enabled ? 'AI is actively trading' : 'AI trading is paused'}
              </p>
            </div>
          </div>

          {/* Main Toggle */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Label htmlFor="ai-toggle" className="text-sm">
                {config.ai_trading_enabled ? 'Enabled' : 'Disabled'}
              </Label>
              <Switch
                id="ai-toggle"
                checked={config.ai_trading_enabled}
                onCheckedChange={handleToggle}
                disabled={isToggling || config.emergency_stop}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Emergency Stop Banner */}
      {config.emergency_stop && (
        <div className="px-4 py-3 bg-destructive/10 border-b border-destructive/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-destructive">
              <AlertOctagon className="w-5 h-5" />
              <span className="font-medium">Emergency Stop Active</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={resetEmergencyStop}
              className="border-destructive text-destructive hover:bg-destructive/10"
            >
              Reset Emergency Stop
            </Button>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Activity className="w-4 h-4" />}
          label="Total Trades"
          value={config.total_automated_trades}
        />
        <StatCard
          icon={<CheckCircle className="w-4 h-4 text-green-500" />}
          label="Success Rate"
          value={`${config.success_rate.toFixed(1)}%`}
        />
        <StatCard
          icon={<TrendingUp className="w-4 h-4" />}
          label="Total P&L"
          value={`₹${config.total_automated_pnl.toLocaleString()}`}
          valueColor={config.total_automated_pnl >= 0 ? 'text-green-500' : 'text-red-500'}
        />
        <StatCard
          icon={<Clock className="w-4 h-4" />}
          label="Last Trade"
          value={config.last_trade_execution
            ? new Date(config.last_trade_execution).toLocaleTimeString()
            : 'Never'}
        />
      </div>

      {/* Controls */}
      <div className="p-4 border-t flex flex-wrap gap-2">
        <Button
          variant="destructive"
          size="sm"
          onClick={handleEmergencyStop}
          disabled={config.emergency_stop}
          className="flex items-center gap-2"
        >
          <AlertOctagon className="w-4 h-4" />
          Emergency Stop
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowRiskSettings(!showRiskSettings)}
          className="flex items-center gap-2"
        >
          <Settings className="w-4 h-4" />
          Risk Settings
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={refetch}
          className="flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      {/* Risk Settings Panel */}
      {showRiskSettings && (
        <RiskSettingsPanel
          config={config}
          onUpdate={updateRiskLimits}
          onClose={() => setShowRiskSettings(false)}
        />
      )}
    </Card>
  )
}

// Stat Card Component
interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
  valueColor?: string
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, valueColor }) => (
  <div className="p-3 rounded-lg bg-muted/50">
    <div className="flex items-center gap-2 text-muted-foreground mb-1">
      {icon}
      <span className="text-xs">{label}</span>
    </div>
    <div className={`font-semibold ${valueColor || ''}`}>{value}</div>
  </div>
)

// Risk Settings Panel
interface RiskSettingsPanelProps {
  config: AIAutomationConfig
  onUpdate: (limits: Record<string, number>) => Promise<boolean>
  onClose: () => void
}

const RiskSettingsPanel: React.FC<RiskSettingsPanelProps> = ({ config, onUpdate, onClose }) => {
  const [limits, setLimits] = useState({
    max_daily_loss_percent: config.risk_limits.max_daily_loss_percent,
    max_position_size_percent: config.risk_limits.max_position_size_percent,
    max_portfolio_risk_percent: config.risk_limits.max_portfolio_risk_percent,
    max_concurrent_positions: config.risk_limits.max_concurrent_positions,
    min_confidence_score: config.risk_limits.min_confidence_score
  })
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    const success = await onUpdate(limits)
    setIsSaving(false)
    if (success) onClose()
  }

  return (
    <div className="p-4 border-t bg-muted/30">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-primary" />
        <h4 className="font-medium">Risk Limits Configuration</h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <RiskInput
          label="Max Daily Loss %"
          value={limits.max_daily_loss_percent}
          onChange={v => setLimits(l => ({ ...l, max_daily_loss_percent: v }))}
        />
        <RiskInput
          label="Max Position Size %"
          value={limits.max_position_size_percent}
          onChange={v => setLimits(l => ({ ...l, max_position_size_percent: v }))}
        />
        <RiskInput
          label="Max Portfolio Risk %"
          value={limits.max_portfolio_risk_percent}
          onChange={v => setLimits(l => ({ ...l, max_portfolio_risk_percent: v }))}
        />
        <RiskInput
          label="Max Concurrent Positions"
          value={limits.max_concurrent_positions}
          onChange={v => setLimits(l => ({ ...l, max_concurrent_positions: v }))}
          step={1}
        />
        <RiskInput
          label="Min Confidence Score"
          value={limits.min_confidence_score}
          onChange={v => setLimits(l => ({ ...l, min_confidence_score: v }))}
          step={0.1}
          max={1}
        />
      </div>

      <div className="flex justify-end gap-2 mt-4">
        <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
        <Button size="sm" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  )
}

// Risk Input Component
interface RiskInputProps {
  label: string
  value: number
  onChange: (value: number) => void
  step?: number
  max?: number
}

const RiskInput: React.FC<RiskInputProps> = ({ label, value, onChange, step = 0.5, max = 100 }) => (
  <div>
    <Label className="text-xs text-muted-foreground">{label}</Label>
    <Input
      type="number"
      value={value}
      onChange={e => onChange(parseFloat(e.target.value) || 0)}
      step={step}
      min={0}
      max={max}
      className="mt-1"
    />
  </div>
)

export default AIAutomationControlPanel
