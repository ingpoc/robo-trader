/**
 * Hook for Claude AI Transparency Data
 *
 * Fetches and manages all AI transparency data from the backend APIs
 */

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'

interface ResearchActivity {
  total_sessions: number
  symbols_analyzed: number
  data_sources_used: number
  key_findings: string[]
  recent_sessions: any[]
}

interface AnalysisActivity {
  total_decisions: number
  avg_confidence: number
  strategies_evaluated: number
  refinements_made: number
  recent_decisions: any[]
}

interface ExecutionActivity {
  total_executions: number
  success_rate: number
  avg_slippage: number
  avg_cost: number
  risk_compliance: number
  recent_executions: any[]
}

interface DailyEvaluation {
  evaluation_date: string
  strategies_evaluated: number
  refinements_recommended: number
  confidence_score: number
  key_insights: string[]
  performance_summary: Record<string, any>
}

interface DailySummary {
  date: string
  day_rating: string
  trades_executed: number
  total_pnl: number
  research_sessions: number
  strategies_evaluated: number
  key_achievements: string[]
  areas_for_improvement: string[]
  planned_activities: string[]
}

interface StrategyEvolution {
  strategy_name: string
  timeline: any[]
  total_evaluations: number
  avg_win_rate: number
  avg_profit_factor: number
  total_refinements: number
}

export function useClaudeTransparency() {
  const [researchActivity, setResearchActivity] = useState<ResearchActivity | null>(null)
  const [analysisActivity, setAnalysisActivity] = useState<AnalysisActivity | null>(null)
  const [executionActivity, setExecutionActivity] = useState<ExecutionActivity | null>(null)
  const [dailyEvaluation, setDailyEvaluation] = useState<DailyEvaluation | null>(null)
  const [dailySummary, setDailySummary] = useState<DailySummary | null>(null)
  const [strategyEvolution, setStrategyEvolution] = useState<StrategyEvolution | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Add fields for feature hook compatibility
  const [tradeLogs, setTradeLogs] = useState<any[]>([])
  const [strategyReflections, setStrategyReflections] = useState<any[]>([])
  const [sessionData, setSessionData] = useState<any[]>([])

  const fetchResearchActivity = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/research')
      setResearchActivity(response.data)
    } catch (err) {
      console.error('Failed to fetch research activity:', err)
      setResearchActivity(null)
    }
  }

  const fetchAnalysisActivity = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/analysis')
      setAnalysisActivity(response.data)  // FIX: API returns data directly, not nested
      // Also populate tradeLogs from analysis data for Recommendations tab
      if (response.data && response.data.recent_decisions) {
        setTradeLogs(response.data.recent_decisions)  // FIX: Correct path to recent_decisions
      }
    } catch (err) {
      console.error('Failed to fetch analysis activity:', err)
      setAnalysisActivity(null)
      setTradeLogs([])
    }
  }

  const fetchExecutionActivity = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/execution')
      setExecutionActivity(response.data)
    } catch (err) {
      console.error('Failed to fetch execution activity:', err)
      setExecutionActivity(null)
    }
  }

  const fetchDailyEvaluation = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/daily-evaluation')
      setDailyEvaluation(response.data)
    } catch (err) {
      console.error('Failed to fetch daily evaluation:', err)
      setDailyEvaluation(null)
    }
  }

  const fetchDailySummary = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/daily-summary')
      setDailySummary(response.data)
    } catch (err) {
      console.error('Failed to fetch daily summary:', err)
      setDailySummary(null)
    }
  }

  const fetchStrategyEvolution = async (strategyName: string) => {
    try {
      const response = await apiClient.get(`/api/claude/transparency/strategy-evolution/${strategyName}`)
      setStrategyEvolution(response.data)
    } catch (err) {
      console.error('Failed to fetch strategy evolution:', err)
      setStrategyEvolution(null)
    }
  }

  const refetchAll = async () => {
    setIsLoading(true)
    setError(null)

    try {
      await Promise.all([
        fetchResearchActivity(),
        fetchAnalysisActivity(),
        fetchExecutionActivity(),
        fetchDailyEvaluation(),
        fetchDailySummary()
      ])
    } catch (err) {
      setError('Failed to refresh transparency data')
      console.error('Error refreshing transparency data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refetchAll()
  }, [])

  return {
    researchActivity,
    analysisActivity,
    executionActivity,
    dailyEvaluation,
    dailySummary,
    strategyEvolution,
    // Feature hook compatibility fields
    tradeLogs,
    strategyReflections,
    sessionData,
    isLoading,
    error,
    refetchAll,
    fetchStrategyEvolution
  }
}