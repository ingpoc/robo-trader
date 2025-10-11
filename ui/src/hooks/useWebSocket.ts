import { useEffect } from 'react'
import { wsClient } from '@/api/websocket'
import { useDashboardStore } from '@/store/dashboardStore'
import type { DashboardData } from '@/types/api'

export function useWebSocket() {
  const setDashboardData = useDashboardStore((state) => state.setDashboardData)
  const setConnected = useDashboardStore((state) => state.setConnected)
  const setBackendStatus = useDashboardStore((state) => state.setBackendStatus)
  const addToast = useDashboardStore((state) => state.addToast)

  useEffect(() => {
    setBackendStatus('connecting')
    wsClient.connect()

    const unsubscribe = wsClient.subscribe((data: DashboardData) => {
      setDashboardData(data)
      setConnected(true)
      setBackendStatus('connected')
    })

    const unsubscribeError = wsClient.onError(() => {
      setConnected(false)
      setBackendStatus('disconnected')
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
      setBackendStatus('disconnected')
    }
  }, [setDashboardData, setConnected, setBackendStatus, addToast])

  return {
    isConnected: wsClient.isConnected(),
  }
}
