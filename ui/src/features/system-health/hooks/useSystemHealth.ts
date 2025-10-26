/**
 * System Health Hook
 * Aggregates system health data from WebSocket broadcasts
 */

import { useState, useEffect } from 'react'
import { wsClient } from '@/api/websocket'

export const useSystemHealth = () => {
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null)
  const [queueHealth, setQueueHealth] = useState<any>(null)
  const [dbHealth, setDbHealth] = useState<any>(null)
  const [resources, setResources] = useState<any>(null)
  const [errors, setErrors] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Subscribe to WebSocket for real-time system health updates
    const unsubscribe = wsClient.subscribe((message: any) => {
      // Check for system health updates from backend
      if (message.type === 'system_health_update') {
        const components = message.components || {}

        setSchedulerStatus({
          healthy: components.scheduler?.status === 'healthy',
          lastRun: components.scheduler?.lastRun || new Date().toISOString()
        })

        setQueueHealth({
          healthy: components.queue?.status === 'healthy',
          totalTasks: components.queue?.totalTasks || 0
        })

        setDbHealth({
          healthy: components.database?.status === 'connected',
          activeConnections: components.database?.connections || 0
        })

        setResources({
          cpu: components.resources?.cpu || 0,
          memory: components.resources?.memory || 0,
          disk: components.resources?.disk || 0
        })

        setErrors([])
        setIsLoading(false)
      }

      // Handle queue status updates from queue_status_update messages
      // This provides more detailed queue information
      if (message.type === 'queue_status_update') {
        const stats = message.stats || {}
        setQueueHealth({
          healthy: true, // Assume healthy if we get status updates
          totalTasks: stats.totalTasks || stats.total_queues || 0,
          runningQueues: stats.running_queues || 0,
          totalQueues: stats.total_queues || 0
        })
        setIsLoading(false)
      }

      // Check for system health errors
      if (message.type === 'system_health_error') {
        console.error('System health error:', message.error)
        setErrors([message.error || 'System health monitoring error'])
        setIsLoading(false)
      }
    })

    // Set initial loading state
    setIsLoading(true)

    return () => {
      unsubscribe()
    }
  }, [])

  return {
    schedulerStatus,
    queueHealth,
    dbHealth,
    resources,
    errors,
    isLoading,
  }
}
