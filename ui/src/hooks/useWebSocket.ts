import { useEffect, useRef, useCallback } from 'react'
import { wsClient } from '@/api/websocket'
import { useDashboardStore } from '@/store/dashboardStore'
import type { DashboardData } from '@/types/api'

export function useWebSocket() {
  const setDashboardData = useDashboardStore((state) => state.setDashboardData)
  const setConnected = useDashboardStore((state) => state.setConnected)
  const setBackendStatus = useDashboardStore((state) => state.setBackendStatus)
  const addToast = useDashboardStore((state) => state.addToast)

  // Use refs to avoid stale closures in callbacks
  const setDashboardDataRef = useRef(setDashboardData)
  const setConnectedRef = useRef(setConnected)
  const setBackendStatusRef = useRef(setBackendStatus)
  const addToastRef = useRef(addToast)

  useEffect(() => {
    setDashboardDataRef.current = setDashboardData
    setConnectedRef.current = setConnected
    setBackendStatusRef.current = setBackendStatus
    addToastRef.current = addToast
  })

  const handleDataUpdate = useCallback((data: DashboardData) => {
    setDashboardDataRef.current(data)
    // Update data freshness timestamps
    const now = Date.now()
    addToastRef.current({
      title: 'Data Updated',
      description: 'Real-time data received from server',
      variant: 'default'
    })
  }, [])

  const handleConnect = useCallback(() => {
    setConnectedRef.current(true)
    setBackendStatusRef.current('connected')
    addToastRef.current({
      title: 'Connected',
      description: 'Real-time data connection established',
      variant: 'success'
    })
  }, [])

  const handleError = useCallback((error: Event) => {
    console.error('WebSocket connection error:', error)
    setConnectedRef.current(false)
    setBackendStatusRef.current('error')
    addToastRef.current({
      title: 'Connection Error',
      description: 'Lost connection to real-time data. Attempting to reconnect...',
      variant: 'error'
    })
  }, [])

  useEffect(() => {
    // Only connect if not already connected
    if (wsClient.isConnected()) {
      return
    }

    // Set initial status
    setBackendStatusRef.current('connecting')

    // Register callbacks BEFORE connecting to avoid race condition
    const unsubscribe = wsClient.subscribe(handleDataUpdate)
    const unsubscribeConnect = wsClient.onConnect(handleConnect)
    const unsubscribeError = wsClient.onError(handleError)

    wsClient.connect()

    return () => {
      unsubscribe()
      unsubscribeConnect()
      unsubscribeError()
    }
  }, [handleDataUpdate, handleConnect, handleError])

  return {
    isConnected: wsClient.isConnected(),
    connectionInfo: wsClient.getConnectionInfo(),
  }
}
