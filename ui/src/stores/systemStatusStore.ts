/**
 * Centralized System Status Store
 *
 * Provides a single source of truth for all system status updates
 * with proper state management, deduplication, and error handling.
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { wsClient } from '@/api/websocket'
import { QueueStatusDTO } from '@/types/queue'

// Types for system status
interface ComponentStatus {
  status: 'healthy' | 'degraded' | 'error' | 'stopped' | 'inactive' | 'idle' | 'connected' | 'disconnected'
  lastCheck?: string
  [key: string]: any
}

interface SystemComponents {
  scheduler: ComponentStatus
  database: ComponentStatus
  websocket: ComponentStatus
  claudeAgent: ComponentStatus
  queue: ComponentStatus
  resources: ComponentStatus
  ai_analysis: ComponentStatus
}

interface SystemStatus {
  status: 'healthy' | 'degraded' | 'error' | 'idle'
  components: SystemComponents
  timestamp: string
  metrics?: {
    total_broadcasts?: number
    successful_broadcasts?: number
    failed_broadcasts?: number
    state_changes?: number
    success_rate?: number
  }
}

interface ClaudeStatus {
  status: string
  auth_method?: string
  sdk_connected?: boolean
  cli_process_running?: boolean
  timestamp: string
  data?: any
}

// Phase 3: Updated to match backend WebSocket message schema
interface QueueStatus {
  queues: QueueStatusDTO[]  // Array of DTOs matching backend
  stats: {
    total_queues: number
    total_pending_tasks: number
    total_active_tasks: number
    total_completed_tasks: number
    total_failed_tasks: number
    last_updated: string
  }
  timestamp: string
}

interface SystemStatusState {
  // State
  systemStatus: SystemStatus | null
  claudeStatus: ClaudeStatus | null
  queueStatus: QueueStatus | null
  isConnected: boolean
  connectionInfo: any
  errors: string[]
  lastUpdate: string | null
  _webSocketInitialized: boolean
  _webSocketCleanup: (() => void) | null

  // Computed getters
  getOverallHealth: () => 'healthy' | 'degraded' | 'error' | 'unknown'
  getComponentHealth: (component: keyof SystemComponents) => ComponentStatus | null
  hasActiveConnections: () => boolean

  // Actions
  setSystemStatus: (status: SystemStatus) => void
  setClaudeStatus: (status: ClaudeStatus) => void
  setQueueStatus: (status: QueueStatus) => void
  setConnected: (connected: boolean) => void
  setConnectionInfo: (info: any) => void
  addError: (error: string) => void
  clearErrors: () => void

  // WebSocket handling
  initializeWebSocket: () => () => void
}

export const useSystemStatusStore = create<SystemStatusState>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    systemStatus: null,
    claudeStatus: null,
    queueStatus: null,
    isConnected: false,
    connectionInfo: null,
    errors: [],
    lastUpdate: null,
    _webSocketInitialized: false,
    _webSocketCleanup: null,

    // Computed getters
    getOverallHealth: () => {
      const { systemStatus } = get()
      return systemStatus?.status || 'unknown'
    },

    getComponentHealth: (component) => {
      const { systemStatus } = get()
      return systemStatus?.components[component] || null
    },

    hasActiveConnections: () => {
      const { systemStatus } = get()
      return (systemStatus?.components.websocket?.clients || 0) > 0
    },

    // Actions
    setSystemStatus: (status) => {
      set((state) => {
        // Only update if status actually changed
        if (JSON.stringify(state.systemStatus) === JSON.stringify(status)) {
          return state
        }

        return {
          systemStatus: status,
          lastUpdate: new Date().toISOString(),
          errors: status.status === 'error' ?
            [`System status error: ${status.status}`] :
            state.errors
        }
      })
    },

    setClaudeStatus: (status) => {
      set((state) => {
        if (JSON.stringify(state.claudeStatus) === JSON.stringify(status)) {
          return state
        }

        return {
          claudeStatus: status,
          lastUpdate: new Date().toISOString()
        }
      })
    },

    setQueueStatus: (status) => {
      set((state) => {
        if (JSON.stringify(state.queueStatus) === JSON.stringify(status)) {
          return state
        }

        // Check for failed tasks in queue status
        const newErrors: string[] = [...state.errors]

        // Handle both array format (from REST API) and object format (from WebSocket)
        let queuesData = status.queues

        // If queues is an array (REST API format), convert to object for processing
        if (Array.isArray(queuesData)) {
          queuesData = queuesData.reduce((acc: any, queue: any) => {
            acc[queue.name] = queue
            return acc
          }, {})
        }

        // Detect failed tasks per queue
        if (queuesData && typeof queuesData === 'object') {
          Object.entries(queuesData).forEach(([queueName, queue]: [string, any]) => {
            if (queue && queue.failed_tasks && queue.failed_tasks > 0) {
              const errorMsg = `Queue "${queueName}" has ${queue.failed_tasks} failed task(s)`
              // Avoid duplicate errors
              if (!newErrors.includes(errorMsg)) {
                newErrors.push(errorMsg)
              }
            }
          })
        }

        // Calculate total failed tasks from queue data
        let totalFailedTasks = status.stats?.total_failed_tasks || 0
        if (totalFailedTasks === 0 && queuesData && typeof queuesData === 'object') {
          // Sum up failed tasks from individual queues
          totalFailedTasks = Object.values(queuesData).reduce((sum: number, queue: any) => {
            return sum + (queue.failed_tasks || 0)
          }, 0)
        }

        // Add total failed tasks error if there are any
        if (totalFailedTasks > 0) {
          const errorMsg = `System has ${totalFailedTasks} total failed task(s)`
          if (!newErrors.some(e => e.includes('total failed'))) {
            newErrors.push(errorMsg)
          }
        }

        return {
          queueStatus: status,
          lastUpdate: new Date().toISOString(),
          errors: newErrors.length > 5 ? newErrors.slice(-5) : newErrors // Keep last 5 errors
        }
      })
    },

    setConnected: (connected) => {
      set({ isConnected: connected })
    },

    setConnectionInfo: (info) => {
      set({ connectionInfo: info })
    },

    addError: (error) => {
      set((state) => ({
        errors: [...state.errors.slice(-4), error], // Keep last 5 errors
        lastUpdate: new Date().toISOString()
      }))
    },

    clearErrors: () => {
      set({ errors: [] })
    },

    // WebSocket handling
    initializeWebSocket: () => {
      const store = get()

      // Prevent duplicate initialization
      if (store._webSocketInitialized) {
        if (process.env.NODE_ENV === 'development') {
          console.log('WebSocket already initialized in system status store')
        }
        return store._webSocketCleanup || (() => {})
      }

      // Force cleanup any existing connection before initializing
      if (store._webSocketCleanup) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Cleaning up existing WebSocket before re-initialization')
        }
        store._webSocketCleanup()
        set({
          _webSocketInitialized: false,
          _webSocketCleanup: null,
          isConnected: false
        })
      }

      // Message handler
      const handleMessage = (message: any) => {
        try {
          // Only log in development or for important messages
          if (process.env.NODE_ENV === 'development' ||
              ['connection_established', 'shutdown'].includes(message.type)) {
            console.log('System status store received message:', message.type)
          }

          switch (message.type) {
            case 'system_health_update':
              store.setSystemStatus({
                status: message.status,
                components: message.components,
                timestamp: message.timestamp,
                metrics: message.metrics
              })

              // Extract queue status from system health components
              if (message.components && message.components.queue) {
                const queueComponent = message.components.queue
                store.setQueueStatus({
                  queues: {
                    main_queue: {
                      status: queueComponent.status,
                      totalTasks: queueComponent.totalTasks || 0,
                      runningQueues: queueComponent.runningQueues || 0,
                      totalQueues: queueComponent.totalQueues || 0
                    }
                  },
                  stats: {
                    totalTasks: queueComponent.totalTasks || 0,
                    runningQueues: queueComponent.runningQueues || 0,
                    totalQueues: queueComponent.totalQueues || 0
                  },
                  timestamp: message.timestamp,
                  data: queueComponent
                })
              }
              break

            case 'claude_status_update':
              store.setClaudeStatus({
                status: message.status,
                auth_method: message.auth_method,
                sdk_connected: message.sdk_connected,
                cli_process_running: message.cli_process_running,
                timestamp: message.timestamp,
                data: message.data
              })
              break

            case 'queue_status_update':
              store.setQueueStatus({
                queues: message.queues,
                stats: message.stats,
                timestamp: message.timestamp,
                data: message.data
              })
              break

            case 'portfolio_analysis_update':
              // Handle portfolio analysis status updates
              if (process.env.NODE_ENV === 'development') {
                console.log('Portfolio analysis update received:', message)
              }

              // Update system status to reflect AI analysis activity
              const currentSystemStatus = store.systemStatus
              if (currentSystemStatus) {
                store.setSystemStatus({
                  ...currentSystemStatus,
                  components: {
                    ...currentSystemStatus.components,
                    ai_analysis: {
                      status: message.status || 'idle',
                      lastCheck: new Date().toISOString(),
                      analysis_id: message.analysis_id,
                      symbols_count: message.symbols_count,
                      recommendations_count: message.recommendations_count,
                      prompt_updates_count: message.prompt_updates_count,
                      error: message.error
                    }
                  },
                  timestamp: new Date().toISOString()
                })
              }
              break

            case 'connection_established':
              if (process.env.NODE_ENV === 'development') {
                console.log('WebSocket connection established:', message.client_id)
              }
              store.setConnected(true)
              break

            case 'shutdown':
              console.warn('Server shutdown message received')
              store.addError('Server is shutting down')
              break

            default:
              console.debug('Unhandled message type:', message.type)
          }
        } catch (error) {
          console.error('Error processing WebSocket message:', error)
          store.addError(`Failed to process ${message.type} message: ${error}`)
        }
      }

      // Connection handlers
      const handleConnect = () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('WebSocket connected in system status store')
        }
        store.setConnected(true)
        store.clearErrors()
      }

      const handleError = (error: Event) => {
        console.error('WebSocket connection error:', error)
        store.setConnected(false)
        store.addError('WebSocket connection error')
      }

      // Subscribe to WebSocket
      const unsubscribe = wsClient.subscribe(handleMessage)
      const unsubscribeConnect = wsClient.onConnect(handleConnect)
      const unsubscribeError = wsClient.onError(handleError)

      // Start WebSocket if not already connected
      if (!wsClient.isConnected()) {
        wsClient.connect()
      }

      // Update connection info
      store.setConnectionInfo(wsClient.getConnectionInfo())

      // Mark as initialized
      set({ _webSocketInitialized: true })

      // Create cleanup function
      const cleanup = () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('Cleaning up WebSocket connection in system status store')
        }

        try {
          unsubscribe()
          unsubscribeConnect()
          unsubscribeError()
        } catch (error) {
          console.warn('Error during WebSocket cleanup:', error)
        }

        // Reset all WebSocket-related state
        set({
          _webSocketInitialized: false,
          _webSocketCleanup: null,
          isConnected: false,
          connectionInfo: null,
          systemStatus: null,
          claudeStatus: null,
          queueStatus: null
        })
      }

      // Store cleanup function
      set({ _webSocketCleanup: cleanup })

      return cleanup
    }
  }))
)

// Export selectors for easier use in components
export const useSystemHealth = () => {
  const store = useSystemStatusStore()

  return {
    overallHealth: store.getOverallHealth(),
    components: store.systemStatus?.components,
    metrics: store.systemStatus?.metrics,
    lastUpdate: store.lastUpdate,
    isConnected: store.isConnected,
    errors: store.errors,

    getComponentHealth: store.getComponentHealth,
    hasActiveConnections: store.hasActiveConnections
  }
}

export const useClaudeStatus = () => {
  const store = useSystemStatusStore()

  return {
    status: store.claudeStatus?.status,
    authMethod: store.claudeStatus?.auth_method,
    sdkConnected: store.claudeStatus?.sdk_connected,
    cliProcessRunning: store.claudeStatus?.cli_process_running,
    lastUpdate: store.claudeStatus?.timestamp,
    data: store.claudeStatus?.data
  }
}

export const useQueueStatus = () => {
  const store = useSystemStatusStore()

  return {
    queues: store.queueStatus?.queues,
    stats: store.queueStatus?.stats,
    lastUpdate: store.queueStatus?.timestamp,
    data: store.queueStatus?.data
  }
}

export const useWebSocketConnection = () => {
  const store = useSystemStatusStore()

  return {
    isConnected: store.isConnected,
    connectionInfo: store.connectionInfo,
    errors: store.errors,
    lastUpdate: store.lastUpdate
  }
}