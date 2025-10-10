import { useEffect } from 'react'
import { wsClient } from '@/api/websocket'
import { useDashboardStore } from '@/store/dashboardStore'
import type { DashboardData } from '@/types/api'

export function useWebSocket() {
  const setDashboardData = useDashboardStore((state) => state.setDashboardData)
  const setConnected = useDashboardStore((state) => state.setConnected)
  const addToast = useDashboardStore((state) => state.addToast)

  useEffect(() => {
    wsClient.connect()

    const unsubscribe = wsClient.subscribe((data: DashboardData) => {
      setDashboardData(data)
      setConnected(true)
    })

    const unsubscribeError = wsClient.onError(() => {
      setConnected(false)
      addToast({
        title: 'Connection Lost',
        description: 'Attempting to reconnect...',
        variant: 'error',
      })
    })

    return () => {
      unsubscribe()
      unsubscribeError()
      wsClient.disconnect()
    }
  }, [setDashboardData, setConnected, addToast])

  return {
    isConnected: wsClient.isConnected(),
  }
}
