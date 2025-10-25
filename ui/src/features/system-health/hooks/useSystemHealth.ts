/**
 * System Health Hook
 * Aggregates system health data from various monitoring sources
 */

import { useState, useEffect } from 'react'

export const useSystemHealth = () => {
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null)
  const [queueHealth, setQueueHealth] = useState<any>(null)
  const [dbHealth, setDbHealth] = useState<any>(null)
  const [resources, setResources] = useState<any>(null)
  const [errors, setErrors] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchHealthData = async () => {
      try {
        setIsLoading(true)

        // Fetch real system health from backend
        const response = await fetch('/api/system/health')
        if (!response.ok) {
          throw new Error('Failed to fetch system health')
        }

        const data = await response.json()

        // Transform backend response to frontend format
        const components = data.components || {}

        setSchedulerStatus({
          healthy: components.scheduler?.status === 'healthy',
          lastRun: components.scheduler?.lastRun || new Date().toISOString()
        })

        setQueueHealth({
          healthy: true,  // TODO: Get from components
          totalTasks: 0  // TODO: Get from components
        })

        setDbHealth({
          healthy: components.database?.status === 'connected',
          activeConnections: components.database?.connections || 0
        })

        setResources({
          cpu: 0,  // TODO: Implement resource monitoring
          memory: 0,
          disk: 0
        })

        setErrors([])
      } catch (err) {
        console.error('Failed to fetch system health:', err)
        setErrors(['Failed to fetch system health data'])
      } finally {
        setIsLoading(false)
      }
    }

    fetchHealthData()

    // Refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000)
    return () => clearInterval(interval)
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
