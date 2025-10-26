import { useClaudeStatus as useSystemClaudeStatus } from '@/stores/systemStatusStore'

export type ClaudeStatus = 'unavailable' | 'idle' | 'analyzing' | 'authenticated' | 'connected/idle'

export interface ClaudeStatusInfo {
  status: ClaudeStatus
  message: string
  currentTask?: string
}

/**
 * Hook to track Claude Paper Trader agent status using the centralized system status store
 * - unavailable: Claude agent is not running or disconnected
 * - idle: Claude agent is connected but not actively analyzing
 * - analyzing: Claude agent is actively running analysis
 */
export function useClaudeStatus(): ClaudeStatusInfo {
  const systemClaudeStatus = useSystemClaudeStatus()
  const { status, authMethod, sdkConnected, cliProcessRunning } = systemClaudeStatus

  // Convert system status to the expected format
  const getStatus = (): ClaudeStatus => {
    switch (status) {
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
    switch (status) {
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
    currentTask: systemClaudeStatus.data?.current_task
  }
}