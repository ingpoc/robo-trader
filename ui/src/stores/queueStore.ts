import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type {
  QueueManagementState,
  QueueStatus,
  QueueTask,
  TaskExecutionHistory,
  QueuePerformanceMetrics,
  QueueStats,
  QueueType,
  TaskFilter,
  QueueTriggerRequest,
  QueueConfigurationUpdate,
  QueueWebSocketEvent,
} from '@/types/queue'

interface QueueStore extends QueueManagementState {
  // Actions
  setQueues: (queues: QueueStatus[]) => void
  setStats: (stats: QueueStats) => void
  setSelectedQueue: (queueType: QueueType | undefined) => void
  setTasks: (tasks: QueueTask[]) => void
  setExecutionHistory: (history: TaskExecutionHistory[]) => void
  setPerformanceMetrics: (metrics: QueuePerformanceMetrics[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | undefined) => void
  updateLastUpdated: () => void

  // Queue operations
  updateQueueStatus: (queueType: QueueType, status: Partial<QueueStatus>) => void
  updateTaskStatus: (taskId: string, status: Partial<QueueTask>) => void
  addTask: (task: QueueTask) => void
  removeTask: (taskId: string) => void

  // WebSocket integration
  handleWebSocketEvent: (event: QueueWebSocketEvent) => void

  // Computed getters
  getSelectedQueue: () => QueueStatus | undefined
  getQueueTasks: (queueType?: QueueType) => QueueTask[]
  getQueueMetrics: (queueType?: QueueType) => QueuePerformanceMetrics[]
  getActiveTasks: (queueType?: QueueType) => QueueTask[]
  getFailedTasks: (queueType?: QueueType) => QueueTask[]
  getPendingTasks: (queueType?: QueueType) => QueueTask[]
}

export const useQueueStore = create<QueueStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    queues: [],
    selectedQueue: undefined,
    tasks: [],
    executionHistory: [],
    performanceMetrics: [],
    isLoading: false,
    error: undefined,
    lastUpdated: new Date().toISOString(),

    // Actions
    setQueues: (queues) => set({ queues }),
    setStats: (stats) => set({ stats }),
    setSelectedQueue: (selectedQueue) => set({ selectedQueue }),
    setTasks: (tasks) => set({ tasks }),
    setExecutionHistory: (executionHistory) => set({ executionHistory }),
    setPerformanceMetrics: (performanceMetrics) => set({ performanceMetrics }),
    setLoading: (isLoading) => set({ isLoading }),
    setError: (error) => set({ error }),
    updateLastUpdated: () => set({ lastUpdated: new Date().toISOString() }),

    // Queue operations
    updateQueueStatus: (queueType, status) =>
      set((state) => ({
        queues: state.queues.map((queue) =>
          queue.queue_type === queueType ? { ...queue, ...status } : queue
        ),
      })),

    updateTaskStatus: (taskId, status) =>
      set((state) => ({
        tasks: state.tasks.map((task) =>
          task.id === taskId ? { ...task, ...status } : task
        ),
      })),

    addTask: (task) =>
      set((state) => ({
        tasks: [task, ...state.tasks],
      })),

    removeTask: (taskId) =>
      set((state) => ({
        tasks: state.tasks.filter((task) => task.id !== taskId),
      })),

    // WebSocket event handler
    handleWebSocketEvent: (event) => {
      const { type, data } = event

      switch (type) {
        case 'queue_status_update':
          // Handle the backend's queue status update format
          if (event.queues) {
            // Backend sends all queues at once
            const queues = event.queues
            const stats = event.stats || {}

            // Update all queues in the store - cast to partial type since backend format differs
            set({
              queues: Object.entries(queues).map(([queueName, queueInfo]: [string, any]) => ({
                queue_type: queueName as QueueType,
                name: queueName,
                description: '',
                is_active: queueInfo.running || false,
                total_tasks: 0,
                pending_tasks: 0,
                executing_tasks: 0,
                completed_tasks: 0,
                failed_tasks: 0,
                average_execution_time_ms: 0,
                throughput_per_minute: 0,
                error_rate_percentage: 0,
                configuration: {} as any,
                ...queueInfo,
              })) as QueueStatus[],
              stats: stats,
              lastUpdated: event.timestamp || new Date().toISOString()
            })
          } else if (data && data.queue_type) {
            // Legacy format support
            get().updateQueueStatus(data.queue_type, data)
          }
          break
        case 'task_status_update':
          // Type narrow to QueueTask which has id
          if ('id' in data) {
            get().updateTaskStatus(data.id, data as any)
          }
          break
        case 'performance_metrics_update':
          // Cast data to proper type for performance metrics
          if ('queue_type' in data) {
            set((state) => ({
              performanceMetrics: state.performanceMetrics.map((metric) =>
                metric.queue_type === data.queue_type ? (data as QueuePerformanceMetrics) : metric
              ),
            }))
          }
          break
        case 'configuration_change':
          // Handle configuration changes if needed
          break
      }

      get().updateLastUpdated()
    },

    // Computed getters
    getSelectedQueue: () => {
      const { queues, selectedQueue } = get()
      return queues.find((queue) => queue.queue_type === selectedQueue)
    },

    getQueueTasks: (queueType) => {
      const { tasks, selectedQueue } = get()
      const targetQueue = queueType || selectedQueue
      return targetQueue
        ? tasks.filter((task) => task.queue_type === targetQueue)
        : tasks
    },

    getQueueMetrics: (queueType) => {
      const { performanceMetrics, selectedQueue } = get()
      const targetQueue = queueType || selectedQueue
      return targetQueue
        ? performanceMetrics.filter((metric) => metric.queue_type === targetQueue)
        : performanceMetrics
    },

    getActiveTasks: (queueType) => {
      return get().getQueueTasks(queueType).filter(
        (task) => task.status === 'executing'
      )
    },

    getFailedTasks: (queueType) => {
      return get().getQueueTasks(queueType).filter(
        (task) => task.status === 'failed'
      )
    },

    getPendingTasks: (queueType) => {
      return get().getQueueTasks(queueType).filter(
        (task) => task.status === 'pending'
      )
    },
  }))
)

// Selectors for optimized re-renders
export const useQueueStatus = () =>
  useQueueStore((state) => state.queues)

export const useSelectedQueue = () =>
  useQueueStore((state) => state.getSelectedQueue())

export const useQueueTasks = (queueType?: QueueType) =>
  useQueueStore((state) => state.getQueueTasks(queueType))

export const useQueueMetrics = (queueType?: QueueType) =>
  useQueueStore((state) => state.getQueueMetrics(queueType))

export const useQueueLoading = () =>
  useQueueStore((state) => state.isLoading)

export const useQueueError = () =>
  useQueueStore((state) => state.error)

export const useQueueStats = () =>
  useQueueStore((state) => state.stats)