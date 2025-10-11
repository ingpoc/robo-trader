import { useEffect, useRef } from 'react'
import { wsClient } from '@/api/websocket'
import { useDashboardStore } from '@/store/dashboardStore'
import type { DashboardData } from '@/types/api'

export function useWebSocket() {
  const setDashboardData = useDashboardStore((state) => state.setDashboardData)
  const setConnected = useDashboardStore((state) => state.setConnected)

  useEffect(() => {
    // Only connect if not already connected
    if (wsClient.isConnected()) {
      return
    }

    // Register callbacks BEFORE connecting to avoid race condition
    const unsubscribe = wsClient.subscribe((data: DashboardData) => {
      setDashboardData(data)
    })

    // Set connected status when WebSocket connects
    const unsubscribeConnect = wsClient.onConnect(() => {
      setConnected(true)
    })

    wsClient.connect()

    return () => {
      unsubscribe()
      unsubscribeConnect()
    }
  }, [setDashboardData, setConnected])

  return {
    isConnected: wsClient.isConnected(),
  }
}
