/**
 * System Health Hook
 * Uses centralized system status store for consistent state management
 */

import { useState, useEffect } from 'react'
import { useSystemStatusStore } from '@/stores/systemStatusStore'
import { monitoringAPI } from '@/api/endpoints'

export const useSystemHealth = () => {
  const {
    systemStatus,
    queueStatus,
    isConnected,
    errors,
    lastUpdate,
    getOverallHealth,
    getComponentHealth
  } = useSystemStatusStore()

  // WebSocket is now initialized globally in App.tsx, so no need to initialize here
  // This hook now only reads from the store

  // Local state for scheduler data from monitoring API
  const [schedulerData, setSchedulerData] = useState<any>(null)

  // Fetch scheduler data from monitoring API
  useEffect(() => {
    const fetchSchedulerData = async () => {
      try {
        const response = await monitoringAPI.getSchedulerStatus()
        setSchedulerData(response)
      } catch (error) {
        console.error('Failed to fetch scheduler data:', error)
      }
    }

    fetchSchedulerData()
    // Set up polling to refresh scheduler data every 30 seconds
    const interval = setInterval(fetchSchedulerData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Extract component-specific data
  const dbHealth = getComponentHealth('database')
  const resources = getComponentHealth('resources')
  const websocketHealth = getComponentHealth('websocket')
  const claudeHealth = getComponentHealth('claudeAgent')

  // Queue health comes from dedicated queueStatus property, not from systemStatus.components.queue
  // The queueStatus is populated by queue_status_update WebSocket messages with proper field mapping
  const queueHealth = queueStatus ? {
    status: 'healthy', // queueStatus messages indicate health via data
    totalTasks: queueStatus.stats?.totalTasks || 0,
    runningQueues: queueStatus.stats?.runningQueues || 0,
    totalQueues: queueStatus.stats?.totalQueues || 0,
    queues: queueStatus.queues
  } : null

  // Calculate scheduler health from monitoring API data
  const calculateSchedulerHealth = () => {
    if (!schedulerData || !schedulerData.schedulers) {
      return {
        healthy: false,
        status: 'attention_required',
        healthySchedulers: 0,
        totalSchedulers: 0,
        hasActiveJobs: false,
        hasCompletedJobs: false,
        details: {
          running: 0,
          degraded: 0,
          failed: 0
        }
      }
    }

    const { schedulers } = schedulerData

    // Calculate overall scheduler health
    const healthySchedulers = schedulers.filter(s => s.status === 'running').length
    const totalSchedulers = schedulers.length
    const hasActiveJobs = schedulers.some(s => s.active_jobs > 0)
    const hasCompletedJobs = schedulers.some(s => (s.completed_jobs || 0) > 0)

    // Consider healthy if:
    // 1. All schedulers are running, OR
    // 2. At least some schedulers are running AND there's activity
    const isHealthy = healthySchedulers === totalSchedulers ||
                     (healthySchedulers > 0 && (hasActiveJobs || hasCompletedJobs))

    return {
      healthy: isHealthy,
      status: isHealthy ? 'healthy' : 'attention_required',
      healthySchedulers,
      totalSchedulers,
      hasActiveJobs,
      hasCompletedJobs,
      details: {
        running: healthySchedulers,
        degraded: healthySchedulers > 0 && healthySchedulers < totalSchedulers,
        failed: schedulers.filter(s => s.status === 'error').length
      }
    }
  }

  const schedulerHealth = calculateSchedulerHealth()

  // Format data for compatibility with enhanced components
  const formattedData = {
    scheduler: schedulerData ? {
      healthy: schedulerHealth.healthy,
      lastRun: schedulerData?.lastRun,
      activeJobs: schedulerData?.schedulers?.reduce((sum: number, s: any) => sum + (s.active_jobs || 0), 0) || 0,
      completedJobs: schedulerData?.schedulers?.reduce((sum: number, s: any) => sum + (s.completed_jobs || 0), 0) || 0,
      schedulers: schedulerData?.schedulers || [],
      totalSchedulers: schedulerHealth.totalSchedulers,
      runningSchedulers: schedulerHealth.details.running,
      healthySchedulers: schedulerHealth.healthySchedulers,
      failedSchedulers: schedulerHealth.details.failed
    } : null,

    queue: queueHealth ? {
      healthy: ['healthy', 'idle'].includes(queueHealth.status),
      totalTasks: queueHealth.totalTasks,
      runningQueues: queueHealth.runningQueues,
      totalQueues: queueHealth.totalQueues,
      queues: queueHealth.queues
    } : null,

    database: dbHealth ? {
      healthy: dbHealth.status === 'connected',
      activeConnections: dbHealth.connections,
      portfolioLoaded: dbHealth.portfolioLoaded
    } : null,

    resources: resources ? {
      cpu: resources.cpu,
      memory: resources.memory,
      disk: resources.disk
    } : null,

    websocket: websocketHealth ? {
      healthy: websocketHealth.status === 'connected',
      clients: websocketHealth.clients
    } : null,

    claudeAgent: claudeHealth ? {
      healthy: ['active', 'authenticated'].includes(claudeHealth.status),
      status: claudeHealth.status,
      authMethod: claudeHealth.authMethod,
      tasksCompleted: claudeHealth.tasksCompleted
    } : null
  }

  return {
    // System-wide data
    overallHealth: getOverallHealth(),
    isConnected,
    lastUpdate,
    errors,
    isLoading: systemStatus === null,

    // Component-specific data (formatted for existing UI)
    schedulerStatus: formattedData.scheduler,
    queueHealth: formattedData.queue,
    dbHealth: formattedData.database,
    resources: formattedData.resources,
    websocketHealth: formattedData.websocket,
    claudeHealth: formattedData.claudeAgent,

    // Raw data access
    rawSystemStatus: systemStatus,
    getComponentHealth
  }
}
