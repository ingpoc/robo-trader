/**
 * System Health Hook
 * Uses centralized system status store for consistent state management
 */

import { useSystemStatusStore } from '@/stores/systemStatusStore'

export const useSystemHealth = () => {
  const {
    systemStatus,
    isConnected,
    errors,
    lastUpdate,
    getOverallHealth,
    getComponentHealth
  } = useSystemStatusStore()

  // WebSocket is now initialized globally in App.tsx, so no need to initialize here
  // This hook now only reads from the store

  // Extract component-specific data
  const schedulerStatus = getComponentHealth('scheduler')
  const queueHealth = getComponentHealth('queue')
  const dbHealth = getComponentHealth('database')
  const resources = getComponentHealth('resources')
  const websocketHealth = getComponentHealth('websocket')
  const claudeHealth = getComponentHealth('claudeAgent')

  
  // Format data for compatibility with existing components
  const formattedData = {
    scheduler: schedulerStatus ? {
      healthy: schedulerStatus.status === 'healthy',
      lastRun: schedulerStatus.lastRun,
      activeJobs: schedulerStatus.activeJobs,
      completedJobs: schedulerStatus.completedJobs
    } : null,

    queue: queueHealth ? {
      healthy: ['healthy', 'idle'].includes(queueHealth.status),
      totalTasks: queueHealth.totalTasks,
      runningQueues: queueHealth.runningQueues,
      totalQueues: queueHealth.totalQueues
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
