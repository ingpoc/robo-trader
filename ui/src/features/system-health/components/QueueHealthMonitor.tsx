/**
 * Enhanced Queue Health Monitor Component
 * Displays detailed health and status of all task queues with full task visibility
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { ChevronDown, ChevronRight, Clock, CheckCircle, AlertCircle, PlayCircle, RefreshCw } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useSystemStatusStore } from '@/stores/systemStatusStore'

// Types based on backend models
interface TaskInfo {
  task_id: string
  task_type: string
  priority: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying'
  retry_count: number
  max_retries: number
  scheduled_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  duration_ms?: number
}

interface QueueInfo {
  queue_name: string
  status: 'healthy' | 'idle' | 'error'
  pending_count: number
  running_count: number
  completed_today: number
  failed_count: number
  total_tasks: number
  last_activity: string
  average_duration_ms: number
}

export interface QueueHealthMonitorProps {
  health: {
    healthy: boolean
    totalTasks: number
    runningQueues: number
    totalQueues: number
    queues?: QueueInfo[]
  } | null
  isLoading: boolean
}

// Custom hook to get queue data from centralized store (WebSocket-driven)
const useRealQueueData = () => {
  const [queueData, setQueueData] = useState<QueueInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Get store data from centralized WebSocket-driven store
  const store = useSystemStatusStore()

  useEffect(() => {
    // Use WebSocket-driven store data instead of polling
    if (store.queueStatus && store.queueStatus.queues) {
      try {
        let transformedQueues: QueueInfo[]

        // Handle both array format (from WebSocket) and object format (legacy)
        if (Array.isArray(store.queueStatus.queues)) {
          // New format: Array of queue objects with queue_name field
          transformedQueues = store.queueStatus.queues.map((queue: any) => ({
            queue_name: queue.queue_name,
            status: queue.status === 'running' || queue.status === 'active' ? 'healthy' : queue.status === 'idle' ? 'idle' : 'error',
            pending_count: queue.pending_count || 0,
            running_count: queue.running_count || 0,
            completed_today: queue.completed_today || 0,
            failed_count: queue.failed_count || 0,
            total_tasks: queue.total_tasks || 0,
            last_activity: queue.last_activity || '',
            average_duration_ms: Math.round((queue.average_duration_ms || 0))
          }))
        } else {
          // Legacy format: Object with queue names as keys
          transformedQueues = Object.entries(store.queueStatus.queues).map(
            ([queueName, queue]: [string, any]) => ({
              queue_name: queueName,
              status: queue.status === 'running' || queue.status === 'active' ? 'healthy' : queue.status === 'idle' ? 'idle' : 'error',
              pending_count: queue.pending_count || 0,
              running_count: queue.running_count || 0,
              completed_today: queue.completed_today || 0,
              failed_count: queue.failed_count || 0,
              total_tasks: queue.total_tasks || 0,
              last_activity: queue.last_activity || 0,
              average_duration_ms: Math.round((queue.average_duration_ms || 0))
            })
          )
        }

        console.log('Transformed WebSocket queues:', transformedQueues)
        setQueueData(transformedQueues)
        setLoading(false)
        setError(null)
      } catch (err) {
        console.error('Failed to transform queue data:', err)
        setError('Failed to parse queue data')
      }
    } else if (!store.isConnected && !loading) {
      setError('WebSocket not connected')
    }
  }, [store.queueStatus, store.isConnected])

  // Fallback: Poll API if WebSocket data is unavailable
  useEffect(() => {
    if (loading && !store.queueStatus) {
      const fetchQueueData = async () => {
        try {
          setError(null)
          const response = await fetch('/api/queues/status')

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const data: QueueStatusResponse = await response.json()

          console.log('API response data:', data)
          const transformedQueues: QueueInfo[] = data.queues.map(queue => ({
            queue_name: queue.queue_name,
            status: queue.status === 'running' || queue.status === 'active' ? 'healthy' : queue.status === 'idle' ? 'idle' : 'error',
            pending_count: queue.pending_count,
            running_count: queue.running_count,
            completed_today: queue.completed_today,
            failed_count: queue.failed_count,
            total_tasks: queue.total_tasks,
            last_activity: queue.last_activity || '',
            average_duration_ms: Math.round((queue.average_duration_ms || 0))
          }))

          console.log('Transformed API queues:', transformedQueues)
          setQueueData(transformedQueues)
          setLoading(false)
        } catch (err) {
          console.error('Failed to fetch queue data:', err)
          setError(err instanceof Error ? err.message : 'Failed to load queue data')
          setQueueData([])
          setLoading(false)
        }
      }

      fetchQueueData()
    }
  }, [loading, store.queueStatus])

  return { queueData, loading, error }
}

// API response types - matches QueueStatusDTO schema from backend
interface QueueStatusResponse {
  queues: Array<{
    queue_name: string
    status: 'running' | 'active' | 'idle' | 'error' | 'stopped'
    pending_count: number
    running_count: number
    completed_today: number
    failed_count: number
    total_tasks: number
    is_healthy: boolean
    is_active: boolean
    success_rate: number
    snapshot_ts: string
    average_duration_ms: number
    last_activity?: string
    current_task?: any
  }>
  stats: {
    total_queues: number
    total_pending_tasks: number
    total_active_tasks: number
    total_completed_tasks: number
    total_failed_tasks: number
    last_updated: string
  }
}

const QueueCard: React.FC<{ queue: QueueInfo; isExpanded: boolean; onToggle: () => void }> = ({
  queue, isExpanded, onToggle
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-emerald-600" />
      case 'idle':
        return <Clock className="w-4 h-4 text-amber-600" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-600" />
      default:
        return <Clock className="w-4 h-4 text-warmgray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'
      case 'idle':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-warmgray-100 text-warmgray-800 border-warmgray-200'
    }
  }

  const getTaskStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayCircle className="w-3 h-3 text-blue-600 animate-pulse" />
      case 'completed':
        return <CheckCircle className="w-3 h-3 text-emerald-600" />
      case 'failed':
        return <AlertCircle className="w-3 h-3 text-red-600" />
      case 'retrying':
        return <RefreshCw className="w-3 h-3 text-amber-600 animate-spin" />
      case 'pending':
        return <Clock className="w-3 h-3 text-warmgray-400" />
      default:
        return <Clock className="w-3 h-3 text-warmgray-400" />
    }
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  
  return (
    <Card className={cn(
      "transition-all duration-200",
      queue.status === 'error' && "border-l-4 border-l-red-500",
      queue.status === 'healthy' && queue.running_count > 0 && "border-l-4 border-l-blue-500"
    )}>
      <CardHeader
        className="pb-3 cursor-pointer hover:bg-warmgray-50/50 dark:hover:bg-warmgray-900/50 transition-colors"
        onClick={onToggle}
      >
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon(queue.status)}
            <span className="text-lg font-semibold capitalize">
              {queue.queue_name ? queue.queue_name.replace('_', ' ') : `Queue ${JSON.stringify(queue).substring(0, 30)}...`}
            </span>
            <span className={cn(
              "px-2 py-1 rounded-full text-xs font-medium border",
              getStatusColor(queue.status)
            )}>
              {queue.status}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 text-sm text-warmgray-600">
              {queue.running_count > 0 && (
                <span className="flex items-center gap-1 text-blue-600 font-medium">
                  <PlayCircle className="w-4 h-4" />
                  {queue.running_count}
                </span>
              )}
              <span>{queue.pending_count} pending</span>
              <span>{queue.completed_today} done</span>
            </div>
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-warmgray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-warmgray-400" />
            )}
          </div>
        </CardTitle>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Queue Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Running</p>
              <p className="text-lg font-semibold text-blue-600">{queue.running_count}</p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Pending</p>
              <p className="text-lg font-semibold text-amber-600">{queue.pending_count}</p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Completed Today</p>
              <p className="text-lg font-semibold text-emerald-600">{queue.completed_today}</p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Failed</p>
              <p className="text-lg font-semibold text-red-600">{queue.failed_count}</p>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="flex justify-between items-center p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
            <span className="text-sm text-warmgray-600">Average Duration</span>
            <span className="text-sm font-medium">
              {formatDuration(queue.average_duration_ms)}
            </span>
          </div>

          {queue.last_completed_at && (
            <div className="flex justify-between items-center p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
              <span className="text-sm text-warmgray-600">Last Completed</span>
              <span className="text-sm font-medium">
                {formatTime(queue.last_completed_at)}
              </span>
            </div>
          )}

          {/* Current Tasks */}
          {queue.current_tasks && queue.current_tasks.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-warmgray-700 mb-3">Current Tasks</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {queue.current_tasks.map((task) => (
                  <div
                    key={task.task_id}
                    className="flex items-center justify-between p-3 bg-white dark:bg-warmgray-800 rounded-lg border border-warmgray-200 dark:border-warmgray-700"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {getTaskStatusIcon(task.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">
                            {task.task_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-warmgray-500">
                            Priority: {task.priority}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-warmgray-500 mt-1">
                          <span>ID: {task.task_id.substring(0, 8)}...</span>
                          {task.started_at && (
                            <span>Started: {formatTime(task.started_at)}</span>
                          )}
                          {task.duration_ms && (
                            <span>Duration: {formatDuration(task.duration_ms)}</span>
                          )}
                        </div>
                        {task.error_message && (
                          <p className="text-xs text-red-600 mt-1 truncate">
                            {task.error_message}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <span className={cn(
                        "px-2 py-1 rounded text-xs font-medium",
                        task.status === 'running' && "bg-blue-100 text-blue-800",
                        task.status === 'completed' && "bg-emerald-100 text-emerald-800",
                        task.status === 'failed' && "bg-red-100 text-red-800",
                        task.status === 'retrying' && "bg-amber-100 text-amber-800",
                        task.status === 'pending' && "bg-warmgray-100 text-warmgray-800"
                      )}>
                        {task.status}
                      </span>
                      {task.retry_count > 0 && (
                        <span className="text-xs text-amber-600 font-medium">
                          {task.retry_count}/{task.max_retries}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!queue.current_tasks || queue.current_tasks.length === 0) && (
            <div className="text-center py-8 text-warmgray-500">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No active tasks in this queue</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

export const QueueHealthMonitor: React.FC<QueueHealthMonitorProps> = ({ health, isLoading }) => {
  const [expandedQueues, setExpandedQueues] = useState<Set<string>>(new Set())
  const { queueData, loading, error } = useRealQueueData()

  // Show loading state while initial data is being fetched
  if (isLoading || loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading queue health...</p>
        </CardContent>
      </Card>
    )
  }

  // Show error state if data fetching failed
  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-400" />
            <p className="text-red-600 font-medium mb-2">Failed to load queue data</p>
            <p className="text-sm text-warmgray-500">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const toggleQueue = (queueName: string) => {
    setExpandedQueues(prev => {
      const newSet = new Set(prev)
      if (newSet.has(queueName)) {
        newSet.delete(queueName)
      } else {
        newSet.add(queueName)
      }
      return newSet
    })
  }

  // Use real queue data from API, fallback to WebSocket health data if available
  const queues = queueData.length > 0 ? queueData : (health?.queues || [])

  return (
    <div className="space-y-4">
      {/* Overall Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              Queue Health Overview
              {health?.healthy ? (
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600" />
              )}
            </span>
            <span className={`text-sm font-normal ${
              health?.healthy ? 'text-emerald-600' : 'text-red-600'
            }`}>
              {health?.healthy ? 'All Systems Operational' : 'Attention Required'}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-warmgray-900 dark:text-warmgray-100">
                {queues.length}
              </p>
              <p className="text-sm text-warmgray-600">Total Queues</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {queues.reduce((sum, q) => sum + q.running_count, 0)}
              </p>
              <p className="text-sm text-warmgray-600">Running Tasks</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">
                {queues.reduce((sum, q) => sum + q.pending_count, 0)}
              </p>
              <p className="text-sm text-warmgray-600">Pending Tasks</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">
                {queues.reduce((sum, q) => sum + q.completed_today, 0)}
              </p>
              <p className="text-sm text-warmgray-600">Completed Today</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Individual Queue Cards */}
      <div className="space-y-3">
        {queues.map((queue) => (
          <QueueCard
            key={queue.queue_name}
            queue={queue}
            isExpanded={expandedQueues.has(queue.queue_name)}
            onToggle={() => toggleQueue(queue.queue_name)}
          />
        ))}
      </div>

      {queues.length === 0 && (
        <Card>
          <CardContent className="text-center py-8">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-warmgray-400" />
            <p className="text-warmgray-500">No queue data available</p>
            <p className="text-sm text-warmgray-400 mt-1">
              Queue system may be initializing or experiencing issues
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default QueueHealthMonitor
