/**
 * System Health Hook
 * Uses the monitoring summary API as the authoritative source for health state.
 */

import { useEffect, useMemo, useState } from 'react'
import { monitoringAPI } from '@/api/endpoints'
import { useSystemStatusStore } from '@/stores/systemStatusStore'

type MonitoringComponent = {
  status?: string
  summary?: string
  error?: string
  [key: string]: any
}

type MonitoringSummary = {
  status: string
  timestamp: string
  blockers: string[]
  initialization: {
    orchestrator_initialized: boolean
    bootstrap_completed: boolean
    initialization_errors: string[]
    last_error: string | null
  }
  components: {
    orchestrator?: MonitoringComponent
    database?: MonitoringComponent
    event_bus?: MonitoringComponent
    background_scheduler?: MonitoringComponent
    websocket?: MonitoringComponent
  }
}

const dedupeErrors = (errors: string[]) => Array.from(new Set(errors.filter(Boolean)))

export const useSystemHealth = () => {
  const { isConnected, errors: websocketErrors, lastUpdate } = useSystemStatusStore()

  const [systemSummary, setSystemSummary] = useState<MonitoringSummary | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const fetchHealthData = async () => {
      try {
        const summary = await monitoringAPI.getSystemStatus()

        if (cancelled) {
          return
        }

        setSystemSummary(summary)
        setFetchError(null)
      } catch (error) {
        if (cancelled) {
          return
        }

        const message =
          error instanceof Error ? error.message : 'Failed to fetch system health status'
        setFetchError(message)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    fetchHealthData()
    const interval = setInterval(fetchHealthData, 15000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const components = systemSummary?.components ?? {}

  const databaseComponent = components.database
  const dbHealth = databaseComponent
    ? {
        healthy: databaseComponent.status === 'healthy',
        activeConnections: databaseComponent.connections || 0,
        portfolioLoaded: Boolean(databaseComponent.portfolioLoaded),
        status: databaseComponent.status,
        summary: databaseComponent.summary,
        error: databaseComponent.error,
      }
    : null

  const websocketComponent = components.websocket
  const websocketHealth = useMemo(() => {
    if (!websocketComponent && !isConnected) {
      return null
    }

    const reportedClients = Number(websocketComponent?.clients || 0)
    const effectiveClients = isConnected ? Math.max(1, reportedClients) : reportedClients
    const localConnectionOverridesSummary = isConnected && reportedClients === 0
    const status =
      localConnectionOverridesSummary
        ? 'healthy'
        : websocketComponent?.status || (isConnected ? 'healthy' : 'idle')

    const summary =
      localConnectionOverridesSummary
        ? 'This operator session is connected to the live WebSocket.'
        : websocketComponent?.summary ||
          (isConnected
            ? 'This operator session is connected to the live WebSocket.'
            : 'No WebSocket clients are currently connected.')

    return {
      healthy: status === 'healthy',
      status,
      clients: effectiveClients,
      summary,
    }
  }, [isConnected, websocketComponent])

  const eventBusHealth = components.event_bus
    ? {
        status: components.event_bus.status,
        summary: components.event_bus.summary || 'Event bus status unavailable.',
      }
    : null

  const mergedErrors = dedupeErrors([
    ...(systemSummary?.blockers || []),
    ...(websocketErrors || []),
    ...(fetchError ? [fetchError] : []),
    ...(systemSummary?.initialization?.initialization_errors || []),
  ])

  return {
    overallHealth: systemSummary?.status || 'unknown',
    isConnected,
    lastUpdate: systemSummary?.timestamp || lastUpdate,
    errors: mergedErrors,
    isLoading,
    dbHealth,
    resources: null,
    websocketHealth,
    eventBusHealth,
    claudeHealth: null,
    rawSystemStatus: systemSummary,
    getComponentHealth: (component: keyof MonitoringSummary['components']) => components[component] || null,
  }
}
