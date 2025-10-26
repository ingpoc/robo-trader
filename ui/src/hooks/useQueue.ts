import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect } from 'react'
import { queueAPI } from '@/api/endpoints'
import { useQueueStore } from '@/stores/queueStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import type {
  QueueType,
  TaskFilter,
  QueueTriggerRequest,
  QueueConfigurationUpdate,
} from '@/types/queue'

// Query keys
const QUEUE_KEYS = {
  all: ['queues'] as const,
  statuses: () => [...QUEUE_KEYS.all, 'statuses'] as const,
  tasks: (filters?: TaskFilter) => [...QUEUE_KEYS.all, 'tasks', filters] as const,
  history: (queueType?: QueueType) => [...QUEUE_KEYS.all, 'history', queueType] as const,
  metrics: (queueType?: QueueType) => [...QUEUE_KEYS.all, 'metrics', queueType] as const,
  config: (queueType: QueueType) => [...QUEUE_KEYS.all, 'config', queueType] as const,
  health: () => [...QUEUE_KEYS.all, 'health'] as const,
}

export function useQueueStatuses() {
  const { setQueues, setStats, setLoading, setError } = useQueueStore()

  return useQuery({
    queryKey: QUEUE_KEYS.statuses(),
    queryFn: async () => {
      const response = await queueAPI.getQueueStatuses()
      return response
    },
    refetchInterval: false, // Disable polling - use WebSocket instead
    onSuccess: (data) => {
      setQueues(data.queues)
      setStats(data.stats)
      setLoading(false)
      setError(undefined)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })
}

export function useQueueTasks(filters?: TaskFilter) {
  const { setTasks, setLoading, setError } = useQueueStore()

  return useQuery({
    queryKey: QUEUE_KEYS.tasks(filters),
    queryFn: async () => {
      const response = await queueAPI.getQueueTasks(filters)
      return response
    },
    refetchInterval: false, // Disable polling - use WebSocket instead
    onSuccess: (data) => {
      setTasks(data.tasks)
      setLoading(false)
      setError(undefined)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })
}

export function useTaskHistory(queueType?: QueueType, limit = 100) {
  const { setExecutionHistory, setLoading, setError } = useQueueStore()

  return useQuery({
    queryKey: QUEUE_KEYS.history(queueType),
    queryFn: async () => {
      const response = await queueAPI.getTaskHistory(queueType, limit)
      return response
    },
    refetchInterval: false, // Disable polling - use WebSocket instead
    onSuccess: (data) => {
      setExecutionHistory(data.history)
      setLoading(false)
      setError(undefined)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })
}

export function useQueueMetrics(queueType?: QueueType, hours = 24) {
  const { setPerformanceMetrics, setLoading, setError } = useQueueStore()

  return useQuery({
    queryKey: QUEUE_KEYS.metrics(queueType),
    queryFn: async () => {
      const response = await queueAPI.getPerformanceMetrics(queueType, hours)
      return response
    },
    refetchInterval: false, // Disable polling - use WebSocket instead
    onSuccess: (data) => {
      setPerformanceMetrics(data.metrics)
      setLoading(false)
      setError(undefined)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })
}

export function useQueueHealth() {
  return useQuery({
    queryKey: QUEUE_KEYS.health(),
    queryFn: async () => {
      const response = await queueAPI.getHealthStatus()
      return response
    },
    refetchInterval: false, // Disable polling - use WebSocket instead
  })
}

export function useTriggerTask() {
  const queryClient = useQueryClient()
  const { addTask } = useQueueStore()

  return useMutation({
    mutationFn: async (request: QueueTriggerRequest) => {
      const response = await queueAPI.triggerTask(request)
      return response
    },
    onSuccess: (data, variables) => {
      // Invalidate and refetch queue data
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.statuses() })
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.tasks() })

      // Add the new task to the store (if we have task details)
      // Note: The API might not return full task details, so we may need to refetch
    },
  })
}

export function useUpdateQueueConfiguration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (update: QueueConfigurationUpdate) => {
      const response = await queueAPI.updateConfiguration(update)
      return response
    },
    onSuccess: (data, variables) => {
      // Invalidate configuration and status queries
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.config(variables.queue_type) })
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.statuses() })
    },
  })
}

export function usePauseQueue() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (queueType: QueueType) => {
      const response = await queueAPI.pauseQueue(queueType)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.statuses() })
    },
  })
}

export function useResumeQueue() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (queueType: QueueType) => {
      const response = await queueAPI.resumeQueue(queueType)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.statuses() })
    },
  })
}

export function useCancelTask() {
  const queryClient = useQueryClient()
  const { removeTask } = useQueueStore()

  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await queueAPI.cancelTask(taskId)
      return response
    },
    onSuccess: (data, taskId) => {
      removeTask(taskId)
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.tasks() })
    },
  })
}

export function useRetryTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await queueAPI.retryTask(taskId)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.tasks() })
    },
  })
}

export function useClearCompletedTasks() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (queueType?: QueueType) => {
      const response = await queueAPI.clearCompletedTasks(queueType)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.tasks() })
      queryClient.invalidateQueries({ queryKey: QUEUE_KEYS.history() })
    },
  })
}

// WebSocket integration hook
export function useQueueWebSocket() {
  const { handleWebSocketEvent } = useQueueStore()
  const { isConnected } = useWebSocket()

  useEffect(() => {
    if (isConnected) {
      // Subscribe to queue-related WebSocket events
      const handleQueueEvent = (event: any) => {
        if (event.type?.startsWith('queue_') ||
            event.type?.startsWith('task_') ||
            event.type?.startsWith('performance_') ||
            event.type?.startsWith('configuration_') ||
            event.type === 'system_health_update') {
          handleWebSocketEvent(event)
        }
      }

      // Subscribe to the WebSocket client for queue events
      const unsubscribe = wsClient.subscribe(handleQueueEvent)

      return () => {
        unsubscribe()
      }
    }
  }, [isConnected, handleWebSocketEvent])

  return { isConnected }
}

// Combined hook for queue management
export function useQueueManagement(queueType?: QueueType) {
  const statuses = useQueueStatuses()
  const tasks = useQueueTasks()
  const history = useTaskHistory(queueType)
  const metrics = useQueueMetrics(queueType)
  const health = useQueueHealth()

  const triggerTask = useTriggerTask()
  const updateConfig = useUpdateQueueConfiguration()
  const pauseQueue = usePauseQueue()
  const resumeQueue = useResumeQueue()
  const cancelTask = useCancelTask()
  const retryTask = useRetryTask()
  const clearCompleted = useClearCompletedTasks()

  const { setSelectedQueue } = useQueueStore()

  const selectQueue = useCallback((type: QueueType | undefined) => {
    setSelectedQueue(type)
  }, [setSelectedQueue])

  return {
    // Data
    statuses,
    tasks,
    history,
    metrics,
    health,

    // Actions
    selectQueue,
    triggerTask,
    updateConfig,
    pauseQueue,
    resumeQueue,
    cancelTask,
    retryTask,
    clearCompleted,

    // Loading states
    isLoading: statuses.isLoading || tasks.isLoading || history.isLoading || metrics.isLoading,
    error: statuses.error || tasks.error || history.error || metrics.error,
  }
}