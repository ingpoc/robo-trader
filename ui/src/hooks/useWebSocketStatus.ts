import { useState, useEffect } from 'react'
import { wsClient } from '@/api/websocket'

export type WebSocketStatus = 'connected' | 'connecting' | 'disconnected'

export interface WebSocketStatusInfo {
  status: WebSocketStatus
  isConnected: boolean
  reconnectAttempts: number
}

/**
 * Hook to track WebSocket connection status
 * Provides real-time connection state updates
 */
export function useWebSocketStatus(): WebSocketStatusInfo {
  const [statusInfo, setStatusInfo] = useState<WebSocketStatusInfo>({
    status: 'disconnected',
    isConnected: false,
    reconnectAttempts: 0,
  })

  useEffect(() => {
    // Update status immediately
    const updateStatus = () => {
      const connectionInfo = wsClient.getConnectionInfo()
      const isConnected = wsClient.isConnected()

      setStatusInfo({
        status: isConnected ? 'connected' : connectionInfo.isReconnecting ? 'connecting' : 'disconnected',
        isConnected,
        reconnectAttempts: connectionInfo.reconnectAttempts,
      })
    }

    // Initial update
    updateStatus()

    // Subscribe to connection callbacks
    const unsubscribeConnect = wsClient.onConnect(() => {
      updateStatus()
    })

    const unsubscribeError = wsClient.onError(() => {
      updateStatus()
    })

    // Poll status every 500ms to catch state changes
    const statusInterval = setInterval(updateStatus, 500)

    return () => {
      unsubscribeConnect()
      unsubscribeError()
      clearInterval(statusInterval)
    }
  }, [])

  return statusInfo
}
