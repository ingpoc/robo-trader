import { useEffect, useRef } from 'react'
import { wsClient } from '@/api/websocket'
import { useDashboardStore } from '@/store/dashboardStore'
import type { DashboardData } from '@/types/api'

export function useWebSocket() {
  const setDashboardData = useDashboardStore((state) => state.setDashboardData)
  const setConnected = useDashboardStore((state) => state.setConnected)
  const setBackendStatus = useDashboardStore((state) => state.setBackendStatus)

  useEffect(() => {
    // Only connect if not already connected
    if (wsClient.isConnected()) {
      return
    }

    // Set initial status
    setBackendStatus('connecting')

    // Register callbacks BEFORE connecting to avoid race condition
    const unsubscribe = wsClient.subscribe((data: DashboardData) => {
      setDashboardData(data)
    })

    // Set connected status when WebSocket connects
    const unsubscribeConnect = wsClient.onConnect(() => {
      setConnected(true)
      setBackendStatus('connected')
    })

    // Handle connection errors
    const unsubscribeError = wsClient.onError((error) => {
      console.error('WebSocket connection error:', error)
      setConnected(false)
      setBackendStatus('error')
    })

    wsClient.connect()

    return () => {
      unsubscribe()
      unsubscribeConnect()
      unsubscribeError()
    }
  }, [setDashboardData, setConnected, setBackendStatus])

  return {
    isConnected: wsClient.isConnected(),
  }
}
