import { useEffect, useState, useCallback } from 'react'
import { wsClient } from '@/api/websocket'

export interface ClaudeAnalysis {
  analysisId: string
  agentName: string
  symbolsCount: number
  startedAt: string
  status: 'running' | 'completed' | 'failed'
  completedAt?: string
  failedAt?: string
  recommendationsCount?: number
  promptUpdatesCount?: number
  error?: string
  errorType?: string
}

export interface ClaudeAnalysisState {
  activeAnalyses: ClaudeAnalysis[]
  completedAnalyses: ClaudeAnalysis[]
  failedAnalyses: ClaudeAnalysis[]
  totalAnalysesCount: number
  isAnyAnalysisRunning: boolean
}

/**
 * Hook to track Claude analysis activities with API call integration
 *
 * This hook provides:
 * - Real-time tracking of active analyses via WebSocket events
 * - History of completed and failed analyses
 * - API integration for fetching analysis history
 * - Event-driven updates without polling
 */
export function useClaudeAnalysis(): ClaudeAnalysisState & {
  refetchHistory: () => Promise<void>
  getAnalysisById: (id: string) => ClaudeAnalysis | undefined
} {
  const [analyses, setAnalyses] = useState<Map<string, ClaudeAnalysis>>(new Map())
  const [isInitialized, setIsInitialized] = useState(false)

  // Fetch analysis history from API on mount
  const refetchHistory = useCallback(async () => {
    try {
      // Fetch analysis transparency data from API
      const response = await fetch('/api/claude/transparency/analysis')
      if (!response.ok) {
        console.warn('Failed to fetch analysis history:', response.statusText)
        return
      }

      const data = await response.json()
      const analysisHistory = data.analysis || {}

      // Convert API data to ClaudeAnalysis format
      const apiAnalyses: ClaudeAnalysis[] = []

      Object.entries(analysisHistory).forEach(([symbol, analysisData]: [string, any]) => {
        if (analysisData && typeof analysisData === 'object') {
          apiAnalyses.push({
            analysisId: analysisData.analysis_id || `api-${symbol}-${Date.now()}`,
            agentName: analysisData.agent_name || 'unknown',
            symbolsCount: 1, // API returns per-symbol data
            startedAt: analysisData.timestamp || new Date().toISOString(),
            status: analysisData.status === 'completed' ? 'completed' :
                   analysisData.status === 'failed' ? 'failed' : 'running',
            completedAt: analysisData.completed_at,
            failedAt: analysisData.failed_at,
            recommendationsCount: analysisData.recommendations?.length || 0,
            error: analysisData.error,
            errorType: analysisData.error_type
          })
        }
      })

      // Merge with existing analyses (prefer existing data for active analyses)
      setAnalyses(prev => {
        const newMap = new Map(prev)

        apiAnalyses.forEach(apiAnalysis => {
          const existing = newMap.get(apiAnalysis.analysisId)
          // Only update if existing is not active or doesn't exist
          if (!existing || existing.status !== 'running') {
            newMap.set(apiAnalysis.analysisId, apiAnalysis)
          }
        })

        return newMap
      })

    } catch (error) {
      console.error('Error fetching analysis history:', error)
    } finally {
      setIsInitialized(true)
    }
  }, [])

  // Initialize with API data
  useEffect(() => {
    refetchHistory()
  }, [refetchHistory])

  // Handle WebSocket events for real-time updates
  useEffect(() => {
    const handleAnalysisStarted = (event: any) => {
      const analysis: ClaudeAnalysis = {
        analysisId: event.analysis_id,
        agentName: event.agent_name,
        symbolsCount: event.symbols_count || 0,
        startedAt: event.started_at || new Date().toISOString(),
        status: 'running'
      }

      setAnalyses(prev => new Map(prev).set(event.analysis_id, analysis))
    }

    const handleAnalysisCompleted = (event: any) => {
      setAnalyses(prev => {
        const existing = prev.get(event.analysis_id)
        const updated: ClaudeAnalysis = {
          ...(existing || {
            analysisId: event.analysis_id,
            agentName: event.agent_name,
            symbolsCount: event.symbols_count || 0,
            startedAt: event.started_at || new Date().toISOString()
          }),
          status: 'completed',
          completedAt: event.completed_at || new Date().toISOString(),
          recommendationsCount: event.recommendations_count,
          promptUpdatesCount: event.prompt_updates_count
        }

        return new Map(prev).set(event.analysis_id, updated)
      })
    }

    // Subscribe to WebSocket events
    const unsubscribeStarted = wsClient.subscribe('CLAUDE_ANALYSIS_STARTED', handleAnalysisStarted)
    const unsubscribeCompleted = wsClient.subscribe('CLAUDE_ANALYSIS_COMPLETED', handleAnalysisCompleted)

    return () => {
      unsubscribeStarted()
      unsubscribeCompleted()
    }
  }, [])

  // Categorize analyses
  const activeAnalyses = Array.from(analyses.values()).filter(a => a.status === 'running')
  const completedAnalyses = Array.from(analyses.values()).filter(a => a.status === 'completed')
  const failedAnalyses = Array.from(analyses.values()).filter(a => a.status === 'failed')

  // Helper function to get analysis by ID
  const getAnalysisById = useCallback((id: string): ClaudeAnalysis | undefined => {
    return analyses.get(id)
  }, [analyses])

  return {
    activeAnalyses,
    completedAnalyses,
    failedAnalyses,
    totalAnalysesCount: analyses.size,
    isAnyAnalysisRunning: activeAnalyses.length > 0,
    refetchHistory,
    getAnalysisById
  }
}