import { useState, useEffect, useRef } from 'react'
import { wsClient } from '@/api/websocket'
import { useAgents } from './useAgents'

export type ClaudeStatus = 'unavailable' | 'idle' | 'analyzing'

export interface ClaudeStatusInfo {
  status: ClaudeStatus
  message: string
  currentTask?: string
}

/**
 * Hook to track Claude Paper Trader agent status
 * - unavailable: Claude agent is not running or disconnected
 * - idle: Claude agent is connected but not actively analyzing
 * - analyzing: Claude agent is actively running analysis
 */
export function useClaudeStatus(): ClaudeStatusInfo {
  const { agents, isLoading } = useAgents()
  const [statusInfo, setStatusInfo] = useState<ClaudeStatusInfo>({
    status: 'unavailable',
    message: 'Initializing...',
  })

  // Track last activity timestamp
  const lastActivityRef = useRef<number>(Date.now())

  useEffect(() => {
    // Subscribe to WebSocket for real-time agent status updates
    const unsubscribe = wsClient.subscribe((message: any) => {
      // Check for agent-specific status updates
      if (message.type === 'agent_status_update' && message.agent_name === 'claude_paper_trader') {
        lastActivityRef.current = Date.now()

        const agentStatus = message.status
        if (agentStatus === 'running') {
          setStatusInfo({
            status: 'analyzing',
            message: message.message || 'Analyzing market data...',
            currentTask: message.current_task,
          })
        } else if (agentStatus === 'idle') {
          setStatusInfo({
            status: 'idle',
            message: 'Ready',
          })
        } else if (agentStatus === 'error') {
          setStatusInfo({
            status: 'unavailable',
            message: 'Error',
          })
        }
      }

      // Check for AI task updates from dashboard data
      if (message.type === 'dashboard_update' && message.data?.ai_status) {
        const aiStatus = message.data.ai_status
        if (aiStatus.current_task && aiStatus.current_task !== 'Idle') {
          lastActivityRef.current = Date.now()
          setStatusInfo({
            status: 'analyzing',
            message: aiStatus.current_task,
            currentTask: aiStatus.current_task,
          })
        } else {
          // Check if recently active (within last 5 seconds)
          const timeSinceActivity = Date.now() - lastActivityRef.current
          if (timeSinceActivity > 5000) {
            setStatusInfo({
              status: 'idle',
              message: 'Ready',
            })
          }
        }
      }
    })

    return () => {
      unsubscribe()
    }
  }, [])

  useEffect(() => {
    // Update status based on agent data from polling
    if (isLoading) {
      setStatusInfo({
        status: 'unavailable',
        message: 'Loading...',
      })
      return
    }

    const claudeAgent = agents?.['claude_paper_trader']
    if (!claudeAgent) {
      setStatusInfo({
        status: 'unavailable',
        message: 'Not configured',
      })
      return
    }

    // Map agent status to Claude status
    switch (claudeAgent.status) {
      case 'running':
        setStatusInfo({
          status: 'analyzing',
          message: claudeAgent.message || 'Analyzing...',
          currentTask: claudeAgent.message,
        })
        break
      case 'idle':
        setStatusInfo({
          status: 'idle',
          message: 'Ready',
        })
        break
      case 'error':
      case 'pending':
      default:
        setStatusInfo({
          status: 'unavailable',
          message: claudeAgent.message || 'Unavailable',
        })
        break
    }
  }, [agents, isLoading])

  return statusInfo
}
