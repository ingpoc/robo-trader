import { useEffect, useMemo, useState } from 'react'

import { wsClient } from '@/api/websocket'

export type ClaudeStatus =
  | 'checking'
  | 'unavailable'
  | 'idle'
  | 'analyzing'
  | 'authenticated'
  | 'connected/idle'
  | 'degraded'

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
  } | null
}

interface ActiveAnalysis {
  analysisId: string
  agentName: string
  symbolsCount: number
  startedAt: string
  status: string
}

interface CapabilityFallback {
  status: ClaudeStatus
  message: string
  currentTask?: string
}

function mapCapabilityStatus(payload: any): CapabilityFallback {
  const runtimeCheck = Array.isArray(payload?.checks)
    ? payload.checks.find((check: any) => check?.key === 'ai_runtime')
    : null

  if (!runtimeCheck) {
    return {
      status: 'unavailable',
      message: 'AI runtime status unavailable',
    }
  }

  if (runtimeCheck.status === 'ready') {
    return {
      status: 'connected/idle',
      message: runtimeCheck.detail || runtimeCheck.summary || 'AI runtime is ready',
      currentTask: runtimeCheck.current_task,
    }
  }

  if (runtimeCheck.status === 'degraded') {
    return {
      status: 'degraded',
      message: runtimeCheck.detail || runtimeCheck.summary || 'AI runtime is degraded',
      currentTask: runtimeCheck.current_task,
    }
  }

  return {
    status: 'unavailable',
    message: runtimeCheck.detail || runtimeCheck.summary || 'AI runtime is unavailable',
    currentTask: runtimeCheck.current_task,
  }
}

export function useClaudeStatus(): ClaudeStatusInfo {
  const [activeAnalyses, setActiveAnalyses] = useState<Map<string, ActiveAnalysis>>(new Map())
  const [latestAnalysis, setLatestAnalysis] = useState<ClaudeStatusInfo['latestAnalysis']>(null)
  const [capabilityStatus, setCapabilityStatus] = useState<CapabilityFallback>({
    status: 'checking',
    message: 'AI runtime status check is in progress',
  })

  useEffect(() => {
    let cancelled = false

    const fetchCapabilities = async () => {
      try {
        const response = await fetch('/api/paper-trading/capabilities')
        if (!response.ok) {
          throw new Error('capabilities request failed')
        }
        const payload = await response.json()
        if (cancelled) return
        setCapabilityStatus(mapCapabilityStatus(payload))
      } catch {
        if (!cancelled) {
          setCapabilityStatus({
            status: 'unavailable',
            message: 'AI runtime status unavailable',
          })
        }
      }
    }

    void fetchCapabilities()
    const intervalId = window.setInterval(() => {
      void fetchCapabilities()
    }, 60000)
    const handleFocus = () => {
      void fetchCapabilities()
    }
    window.addEventListener('focus', handleFocus)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
      window.removeEventListener('focus', handleFocus)
    }
  }, [])

  useEffect(() => {
    const handleAnalysisStarted = (event: any) => {
      const analysis: ActiveAnalysis = {
        analysisId: event.analysis_id,
        agentName: event.agent_name || 'analyzer',
        symbolsCount: event.symbols_count || 0,
        startedAt: event.started_at || new Date().toISOString(),
        status: event.status || 'running',
      }

      setActiveAnalyses(prev => new Map(prev).set(event.analysis_id, analysis))
      setLatestAnalysis({
        analysisId: event.analysis_id,
        agentName: event.agent_name,
        symbolsCount: event.symbols_count,
        status: event.status,
      })
    }

    const handleAnalysisCompleted = (event: any) => {
      setActiveAnalyses(prev => {
        const next = new Map(prev)
        next.delete(event.analysis_id)
        return next
      })

      setLatestAnalysis({
        analysisId: event.analysis_id,
        agentName: event.agent_name,
        symbolsCount: event.symbols_count,
        status: event.status,
      })
    }

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

  const resolvedStatus = useMemo<ClaudeStatus>(() => {
    if (activeAnalyses.size > 0) {
      return 'analyzing'
    }
    return capabilityStatus.status
  }, [activeAnalyses.size, capabilityStatus.status])

  const message = useMemo(() => {
    if (activeAnalyses.size > 0) {
      const analysisList = Array.from(activeAnalyses.values())
      const totalSymbols = analysisList.reduce((sum, analysis) => sum + (analysis.symbolsCount || 0), 0)
      const agents = [...new Set(analysisList.map(analysis => analysis.agentName))].join(', ')

      if (activeAnalyses.size === 1) {
        return `AI runtime is analyzing ${totalSymbols} symbols via ${agents}`
      }
      return `AI runtime is running ${activeAnalyses.size} analyses on ${totalSymbols} symbols via ${agents}`
    }

    return capabilityStatus.message
  }, [activeAnalyses, capabilityStatus.message])

  return {
    status: resolvedStatus,
    message,
    currentTask: capabilityStatus.currentTask,
    activeAnalysesCount: activeAnalyses.size,
    latestAnalysis,
  }
}

export const useAiRuntimeStatus = useClaudeStatus
