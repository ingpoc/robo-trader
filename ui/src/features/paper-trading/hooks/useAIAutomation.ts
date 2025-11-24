/**
 * Hook for AI Automation Control
 * Manages AI paper trading toggle, emergency stop, and risk limits
 */

import { useState, useEffect, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'

export interface RiskLimits {
  max_daily_loss_percent: number
  max_position_size_percent: number
  max_portfolio_risk_percent: number
  max_concurrent_positions: number
  min_confidence_score: number
}

export interface TradingHours {
  market_hours_only: boolean
  trading_days: string[]
  start_time: string
  end_time: string
}

export interface AIAutomationConfig {
  ai_trading_enabled: boolean
  risk_limits: RiskLimits
  trading_hours: TradingHours
  daily_loss_limit: number
  max_position_size_percent: number
  max_portfolio_risk_percent: number
  emergency_stop: boolean
  last_strategy_generation: string | null
  last_trade_execution: string | null
  automation_start_time: string | null
  total_automated_trades: number
  successful_automated_trades: number
  failed_automated_trades: number
  total_automated_pnl: number
  success_rate: number
  created_at: string
  updated_at: string
}

export interface AIAutomationState {
  config: AIAutomationConfig | null
  isLoading: boolean
  error: string | null
}

const API_BASE = '/api/paper-trading/automation'

export function useAIAutomation() {
  const [state, setState] = useState<AIAutomationState>({
    config: null,
    isLoading: true,
    error: null
  })
  const { toast } = useToast()

  // Fetch automation status
  const fetchStatus = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      const response = await fetch(`${API_BASE}/status`)
      const data = await response.json()

      if (data.success) {
        setState({ config: data.automation, isLoading: false, error: null })
      } else {
        setState(prev => ({ ...prev, isLoading: false, error: data.error || 'Failed to fetch status' }))
      }
    } catch (err) {
      setState(prev => ({ ...prev, isLoading: false, error: 'Network error' }))
    }
  }, [])

  // Toggle AI trading
  const toggleAITrading = useCallback(async (enabled: boolean) => {
    try {
      const response = await fetch(`${API_BASE}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      })
      const data = await response.json()

      if (data.success) {
        setState(prev => prev.config ? {
          ...prev,
          config: { ...prev.config, ai_trading_enabled: enabled }
        } : prev)
        toast({
          title: enabled ? 'AI Trading Enabled' : 'AI Trading Disabled',
          description: enabled ? 'AI will now execute paper trades automatically' : 'AI paper trading has been paused'
        })
        return true
      } else {
        toast({ title: 'Error', description: data.error, variant: 'destructive' })
        return false
      }
    } catch {
      toast({ title: 'Error', description: 'Failed to toggle AI trading', variant: 'destructive' })
      return false
    }
  }, [toast])

  // Emergency stop
  const triggerEmergencyStop = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/emergency-stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()

      if (data.success) {
        setState(prev => prev.config ? {
          ...prev,
          config: { ...prev.config, emergency_stop: true, ai_trading_enabled: false }
        } : prev)
        toast({
          title: '🛑 Emergency Stop Activated',
          description: 'All AI trading has been halted immediately',
          variant: 'destructive'
        })
        return true
      }
      return false
    } catch {
      toast({ title: 'Error', description: 'Failed to activate emergency stop', variant: 'destructive' })
      return false
    }
  }, [toast])

  // Reset emergency stop
  const resetEmergencyStop = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/reset-emergency-stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()

      if (data.success) {
        setState(prev => prev.config ? {
          ...prev,
          config: { ...prev.config, emergency_stop: false }
        } : prev)
        toast({ title: 'Emergency Stop Reset', description: 'You can now re-enable AI trading' })
        return true
      }
      return false
    } catch {
      toast({ title: 'Error', description: 'Failed to reset emergency stop', variant: 'destructive' })
      return false
    }
  }, [toast])

  // Update risk limits
  const updateRiskLimits = useCallback(async (limits: Partial<RiskLimits>) => {
    try {
      const response = await fetch(`${API_BASE}/risk-limits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(limits)
      })
      const data = await response.json()

      if (data.success) {
        await fetchStatus()
        toast({ title: 'Risk Limits Updated', description: 'New risk parameters are now active' })
        return true
      }
      return false
    } catch {
      toast({ title: 'Error', description: 'Failed to update risk limits', variant: 'destructive' })
      return false
    }
  }, [fetchStatus, toast])

  // Initial fetch
  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return {
    ...state,
    refetch: fetchStatus,
    toggleAITrading,
    triggerEmergencyStop,
    resetEmergencyStop,
    updateRiskLimits
  }
}
