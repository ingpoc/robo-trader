import { useClaudeStatus as useSystemClaudeStatus } from '@/stores/systemStatusStore'
import { useEffect, useState, useCallback } from 'react'
import { wsClient } from '@/api/websocket'

export type ClaudeStatus = 'unavailable' | 'idle' | 'analyzing' | 'authenticated' | 'connected/idle'

export interface ClaudeStatusInfo {
  status: ClaudeStatus
  message: string
  currentTask?: string
  activeAnalysesCount?: number
  latestAnalysis?: {
    analysisId?: string
    agentName?: string
    symbolsCount?: number
    status?: string
  }
}

// Store active analysis from WebSocket events
interface ActiveAnalysis {
  analysisId: string
  agentName: string
  symbolsCount: number
  startedAt: string
  status: string
}

/**
 * Hook to track Claude Paper Trader agent status using event-driven WebSocket updates
 * - unavailable: Claude agent is not running or disconnected
 * - idle: Claude agent is connected but not actively analyzing
 * - analyzing: Claude agent is actively running analysis
 * - connected/idle: Claude agent is connected and ready
 */
export function useClaudeStatus(): ClaudeStatusInfo {
  const systemClaudeStatus = useSystemClaudeStatus()
  const { status, authMethod, sdkConnected, cliProcessRunning } = systemClaudeStatus

  // Track active analyses from WebSocket events
  const [activeAnalyses, setActiveAnalyses] = useState<Map<string, ActiveAnalysis>>(new Map())
  const [latestAnalysis, setLatestAnalysis] = useState<ClaudeStatusInfo['latestAnalysis']>(null)

  // Handle WebSocket events for real-time analysis tracking
  useEffect(() => {
    const handleAnalysisStarted = (event: any) => {
      const analysis: ActiveAnalysis = {
        analysisId: event.analysis_id,
        agentName: event.agent_name,
        symbolsCount: event.symbols_count || 0,
        startedAt: event.started_at || new Date().toISOString(),
        status: event.status || 'running'
      }

      setActiveAnalyses(prev => new Map(prev).set(event.analysis_id, analysis))
      setLatestAnalysis({
        analysisId: event.analysis_id,
        agentName: event.agent_name,
        symbolsCount: event.symbols_count,
        status: event.status
      })
    }

    const handleAnalysisCompleted = (event: any) => {
      setActiveAnalyses(prev => {
        const newMap = new Map(prev)
        newMap.delete(event.analysis_id)
        return newMap
      })

      // Update latest analysis with completion info
      setLatestAnalysis(prev => prev ? {
        ...prev,
        status: event.status || 'completed',
        analysisId: event.analysis_id
      } : null)
    }

    // Subscribe to WebSocket events - filter by message type inside callback
    const handleWebSocketMessage = (message: any) => {
      if (message.type === 'CLAUDE_ANALYSIS_STARTED' || message.type === 'claude_analysis_started') {
        handleAnalysisStarted(message)
      } else if (message.type === 'CLAUDE_ANALYSIS_COMPLETED' || message.type === 'claude_analysis_completed') {
        handleAnalysisCompleted(message)
      }
    }

    const unsubscribe = wsClient.subscribe(handleWebSocketMessage)

    return () => {
      unsubscribe()
    }
  }, [])

  // Convert system status to the expected format with event-driven enhancements
  const getStatus = (): ClaudeStatus => {
    // If we have active analyses from events, prioritize that status
    if (activeAnalyses.size > 0) {
      return 'analyzing'
    }

    switch (status) {
      case 'analyzing':
        return 'analyzing'
      case 'connected/idle':
        return 'connected/idle'
      case 'active':
        return sdkConnected && cliProcessRunning ? 'connected/idle' : 'authenticated'
      case 'authenticated':
        return 'authenticated'
      case 'disconnected':
        return 'unavailable'
      default:
        return 'unavailable'
    }
  }

  const getStatusMessage = (): string => {
    // If we have active analyses, show enhanced message
    if (activeAnalyses.size > 0) {
      const analysisList = Array.from(activeAnalyses.values())
      const totalSymbols = analysisList.reduce((sum, analysis) => sum + (analysis.symbolsCount || 0), 0)
      const agents = [...new Set(analysisList.map(a => a.agentName))].join(', ')

      if (activeAnalyses.size === 1) {
        return `Claude is analyzing ${totalSymbols} symbols via ${agents}`
      } else {
        return `Claude is running ${activeAnalyses.size} analyses on ${totalSymbols} symbols via ${agents}`
      }
    }

    switch (status) {
      case 'analyzing':
        return 'Claude is analyzing market data and executing strategies'
      case 'connected/idle':
        return 'Claude SDK is actively connected to CLI process'
      case 'active':
        return sdkConnected && cliProcessRunning
          ? 'Claude agent is connected and ready'
          : `Authenticated via ${authMethod || 'unknown method'}`
      case 'authenticated':
        return `Authenticated via ${authMethod || 'unknown method'}`
      case 'disconnected':
        return 'Claude agent is not connected'
      default:
        return 'Claude agent status unknown'
    }
  }

  return {
    status: getStatus(),
    message: getStatusMessage(),
    currentTask: systemClaudeStatus.data?.current_task,
    activeAnalysesCount: activeAnalyses.size,
    latestAnalysis
  }
}