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
      const data = response.data as any
      // API returns {"research": {...}} structure
      if (data && data.research) {
        setResearchActivity(data.research)
      } else {
        setResearchActivity(null)
      }
    } catch (err) {
      console.error('Failed to fetch research activity:', err)
      setResearchActivity(null)
    }
  }

  const fetchAnalysisActivity = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/analysis')
      const data = response.data as any
      // API returns {"analysis": {...}} structure
      const analysisData = data.analysis || data
      setAnalysisActivity(analysisData)
    } catch (err) {
      console.error('Failed to fetch analysis activity:', err)
      setAnalysisActivity(null)
    }
  }

  const fetchTradeDecisions = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/trade-decisions')
      const data = response.data as any
      // API returns {"decisions": [...], "stats": {...}, "last_updated": "..."} structure
      if (data && data.decisions) {
        setTradeLogs(data.decisions)
      } else {
        setTradeLogs([])
      }
    } catch (err) {
      console.error('Failed to fetch trade decisions:', err)
      setTradeLogs([])
    }
  }

  const fetchExecutionActivity = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/execution')
      const data = response.data as any
      // API returns {"execution": {...}} structure
      const executionData = data.execution || data
      setExecutionActivity(executionData)
      // Map execution data to session format expected by SessionTranscripts component
      if (executionData && executionData.recent_executions) {
        const mappedSessions = executionData.recent_executions.map((session: any) => ({
          type: session.session_type || 'unknown',
          timestamp: session.timestamp,
          duration: 0, // Not available in current API
          tokenInput: session.token_usage ? Math.floor(session.token_usage * 0.6) : 0,
          tokenOutput: session.token_usage ? Math.floor(session.token_usage * 0.4) : 0,
          decisionsCount: session.trades_executed || 0,
          tradesExecuted: session.trades_executed || 0,
          summary: `${session.account_type} trading session - ${session.success ? 'Successful' : 'Failed'}`
        }))
        setSessionData(mappedSessions)
      } else {
        setSessionData([])
      }
    } catch (err) {
      console.error('Failed to fetch execution activity:', err)
      setExecutionActivity(null)
      setSessionData([])
    }
  }

  const fetchDailyEvaluation = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/daily-evaluation')
      const data = response.data as any
      // API returns {"daily_evaluation": {...}} structure
      const evaluationData = data.daily_evaluation || data
      setDailyEvaluation(evaluationData)

      // Transform evaluation data to reflections format
      if (evaluationData && evaluationData.evaluations && evaluationData.evaluations.length > 0) {
        const reflections = evaluationData.evaluations.map((evaluation: any) => ({
          date: evaluation.date,
          account_type: evaluation.account_type,
          what_worked: evaluation.best_performing ? `${evaluation.best_performing} strategy performed well` : '',
          what_didnt_work: evaluation.worst_performing ? `${evaluation.worst_performing} strategy underperformed` : '',
          tomorrow_focus: evaluation.recommendations && evaluation.recommendations.length > 0 ? evaluation.recommendations.join('. ') : '',
          win_rate: 0, // Not available in current data
          trades_executed: 0, // Not available in current data
          confidence_score: evaluation.confidence_score
        }))
        setStrategyReflections(reflections)
      } else {
        setStrategyReflections([])
      }
    } catch (err) {
      console.error('Failed to fetch daily evaluation:', err)
      setDailyEvaluation(null)
      setStrategyReflections([])
    }
  }

  const fetchDailySummary = async () => {
    try {
      const response = await apiClient.get('/api/claude/transparency/daily-summary')
      const data = response.data as any
      // API returns {"daily_summary": {...}} structure
      const summaryData = data.daily_summary || data.dailySummary || data
      setDailySummary(summaryData)
    } catch (err) {
      console.error('Failed to fetch daily summary:', err)
      setDailySummary(null)
    }
  }

  const fetchStrategyEvolution = async (strategyName: string) => {
    try {
      const response = await apiClient.get(`/api/claude/transparency/strategy-evolution/${strategyName}`)
      const data = response.data as any
      setStrategyEvolution(data.strategy_evolution)
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
        fetchDailySummary(),
        fetchTradeDecisions()
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