/**
 * Enhanced Scheduler Status Component
 * Displays detailed status of all background schedulers with full task visibility
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { CheckCircle, AlertTriangle, ChevronDown, ChevronRight, Clock, PlayCircle, Calendar, Activity, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'

// Types based on backend scheduler data
interface SchedulerJob {
  job_id: string
  name: string
  status: 'running' | 'idle' | 'paused' | 'error'
  last_run: string
  next_run?: string
  execution_count: number
  average_duration_ms: number
  last_error?: string
}

interface ExecutionRecord {
  task_name: string
  task_id: string
  execution_type: 'manual' | 'scheduled'
  user: string
  timestamp: string
}

interface SchedulerInfo {
  scheduler_id: string
  name: string
  status: 'running' | 'stopped' | 'error'
  event_driven: boolean
  uptime_seconds: number
  jobs_processed: number
  jobs_failed: number
  active_jobs: number
  completed_jobs: number
  last_run_time: string
  execution_history?: ExecutionRecord[]
  total_executions?: number
  jobs: SchedulerJob[]
}

export interface SchedulerStatusProps {
  status: {
    healthy: boolean
    schedulers?: SchedulerInfo[]
  } | null
  isLoading: boolean
}

const SchedulerCard: React.FC<{
  scheduler: SchedulerInfo;
  isExpanded: boolean;
  onToggle: () => void
}> = ({ scheduler, isExpanded, onToggle }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayCircle className="w-4 h-4 text-emerald-600" />
      case 'stopped':
        return <Clock className="w-4 h-4 text-warmgray-400" />
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-600" />
      default:
        return <Clock className="w-4 h-4 text-warmgray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'
      case 'stopped':
        return 'bg-warmgray-100 text-warmgray-800 border-warmgray-200'
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-warmgray-100 text-warmgray-800 border-warmgray-200'
    }
  }

  const getJobStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayCircle className="w-3 h-3 text-blue-600 animate-pulse" />
      case 'idle':
        return <Clock className="w-3 h-3 text-warmgray-400" />
      case 'paused':
        return <AlertTriangle className="w-3 h-3 text-amber-600" />
      case 'error':
        return <AlertTriangle className="w-3 h-3 text-red-600" />
      default:
        return <Clock className="w-3 h-3 text-warmgray-400" />
    }
  }

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const successRate = scheduler.jobs_processed > 0
    ? ((scheduler.jobs_processed - scheduler.jobs_failed) / scheduler.jobs_processed * 100).toFixed(1)
    : '100'

  return (
    <Card className={cn(
      "transition-all duration-200",
      scheduler.status === 'error' && "border-l-4 border-l-red-500",
      scheduler.status === 'running' && "border-l-4 border-l-emerald-500"
    )}>
      <CardHeader
        className="pb-3 cursor-pointer hover:bg-warmgray-50/50 dark:hover:bg-warmgray-900/50 transition-colors"
        onClick={onToggle}
      >
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon(scheduler.status)}
            <span className="text-lg font-semibold">
              {scheduler.name}
            </span>
            <span className={cn(
              "px-2 py-1 rounded-full text-xs font-medium border",
              getStatusColor(scheduler.status)
            )}>
              {scheduler.status}
            </span>
            {scheduler.event_driven && (
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                Event Driven
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 text-sm text-warmgray-600">
              {scheduler.active_jobs > 0 && (
                <span className="flex items-center gap-1 text-blue-600 font-medium">
                  <Activity className="w-4 h-4" />
                  {scheduler.active_jobs}
                </span>
              )}
              <span>{scheduler.completed_jobs} done</span>
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
          {/* Scheduler Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Uptime</p>
              <p className="text-lg font-semibold text-emerald-600">
                {formatUptime(scheduler.uptime_seconds)}
              </p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Processed</p>
              <p className="text-lg font-semibold text-blue-600">
                {scheduler.jobs_processed}
              </p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Failed</p>
              <p className="text-lg font-semibold text-red-600">
                {scheduler.jobs_failed}
              </p>
            </div>
            <div>
              <p className="text-xs text-warmgray-500 uppercase tracking-wide">Success Rate</p>
              <p className="text-lg font-semibold text-emerald-600">
                {successRate}%
              </p>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex justify-between items-center p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
              <span className="text-sm text-warmgray-600">Active Jobs</span>
              <span className="text-sm font-medium text-blue-600">
                {scheduler.active_jobs}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg">
              <span className="text-sm text-warmgray-600">Last Run</span>
              <span className="text-sm font-medium">
                {formatTime(scheduler.last_run_time)}
              </span>
            </div>
          </div>

          {/* Individual Jobs */}
          {scheduler.jobs && scheduler.jobs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-warmgray-700 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Scheduled Jobs ({scheduler.jobs.length})
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {scheduler.jobs.map((job) => (
                  <div
                    key={job.job_id}
                    className="flex items-center justify-between p-3 bg-white dark:bg-warmgray-800 rounded-lg border border-warmgray-200 dark:border-warmgray-700"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {getJobStatusIcon(job.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">
                            {job.name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-warmgray-500">
                            ID: {job.job_id.substring(0, 8)}...
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-warmgray-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Last: {formatTime(job.last_run)}
                          </span>
                          {job.next_run && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Next: {formatTime(job.next_run)}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Activity className="w-3 h-3" />
                            {job.execution_count} runs
                          </span>
                        </div>
                        {job.last_error && (
                          <p className="text-xs text-red-600 mt-1 truncate">
                            Error: {job.last_error}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <span className={cn(
                        "px-2 py-1 rounded text-xs font-medium",
                        job.status === 'running' && "bg-blue-100 text-blue-800",
                        job.status === 'idle' && "bg-warmgray-100 text-warmgray-800",
                        job.status === 'paused' && "bg-amber-100 text-amber-800",
                        job.status === 'error' && "bg-red-100 text-red-800"
                      )}>
                        {job.status}
                      </span>
                      <span className="text-xs text-warmgray-500">
                        {formatDuration(job.average_duration_ms)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Execution History */}
          {scheduler.execution_history && scheduler.execution_history.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-warmgray-700 mb-3 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Recent Executions ({scheduler.execution_history.length})
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {scheduler.execution_history.slice(0, 10).map((execution, index) => (
                  <div
                    key={`${execution.task_name}-${execution.task_id}-${index}`}
                    className="flex items-center justify-between p-3 bg-white dark:bg-warmgray-800 rounded-lg border border-warmgray-200 dark:border-warmgray-700"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        execution.status === 'completed' && "bg-emerald-500",
                        execution.status === 'failed' && "bg-red-500",
                        execution.status === 'running' && "bg-blue-500 animate-pulse"
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">
                            {execution.task_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-warmgray-500">
                            {execution.execution_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-warmgray-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatTime(execution.timestamp)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Activity className="w-3 h-3" />
                            {execution.symbols?.length || 0} symbols
                          </span>
                          {execution.user && (
                            <span className="text-xs">
                              by {execution.user}
                            </span>
                          )}
                        </div>
                        {execution.error_message && (
                          <p className="text-xs text-red-600 mt-1 truncate">
                            Error: {execution.error_message}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <span className={cn(
                        "px-2 py-1 rounded text-xs font-medium",
                        execution.status === 'completed' && "bg-emerald-100 text-emerald-800",
                        execution.status === 'failed' && "bg-red-100 text-red-800",
                        execution.status === 'running' && "bg-blue-100 text-blue-800"
                      )}>
                        {execution.status}
                      </span>
                      <span className="text-xs text-warmgray-500">
                        {execution.execution_time_seconds ? `${execution.execution_time_seconds.toFixed(1)}s` : 'N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!scheduler.jobs || scheduler.jobs.length === 0) && (!scheduler.execution_history || scheduler.execution_history.length === 0) && (
            <div className="text-center py-8 text-warmgray-500">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No jobs or executions for this scheduler</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

// Custom hook to fetch real scheduler data
const useRealSchedulerData = () => {
  const [schedulerData, setSchedulerData] = useState<SchedulerInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSchedulerData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch real scheduler data from the monitoring API using the API client
        const { monitoringAPI } = await import('@/api/endpoints')
        const data = await monitoringAPI.getSchedulerStatus()

        // Use the new comprehensive scheduler data from the API
        const schedulers: SchedulerInfo[] = []

        if (data.status === 'running' && data.schedulers) {
          // Transform API scheduler data to component format
          for (const scheduler of data.schedulers) {
            const schedulerInfo = {
              scheduler_id: scheduler.scheduler_id,
              name: scheduler.name,
              status: scheduler.status,
              event_driven: scheduler.event_driven,
              uptime_seconds: scheduler.uptime_seconds,
              jobs_processed: scheduler.jobs_processed,
              jobs_failed: scheduler.jobs_failed,
              active_jobs: scheduler.active_jobs,
              completed_jobs: scheduler.completed_jobs,
              last_run_time: scheduler.last_run_time,
              execution_history: scheduler.execution_history,
              total_executions: scheduler.total_executions,
              jobs: scheduler.jobs || []
            }
            schedulers.push(schedulerInfo)
          }
        }

        setSchedulerData(schedulers)
        setLoading(false)
      } catch (err) {
        console.error('Failed to fetch scheduler data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load scheduler data')
        setSchedulerData([])
        console.log('Setting loading to false due to error')
        setLoading(false)
      }
    }

    fetchSchedulerData()

    // Set up polling for real-time updates (every 15 seconds)
    const interval = setInterval(fetchSchedulerData, 15000)

    return () => {
      clearInterval(interval)
    }
  }, [])

  return { schedulerData, loading, error }
}

export const SchedulerStatus: React.FC<SchedulerStatusProps> = ({ status, isLoading }) => {
  const [expandedSchedulers, setExpandedSchedulers] = useState<Set<string>>(new Set())
  const { schedulerData, loading: schedulerLoading, error: schedulerError } = useRealSchedulerData()


  // Show loading state while scheduler data is being fetched
  // Note: We don't wait for isLoading (WebSocket) since we have our own API loading state
  if (schedulerLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading scheduler status...</p>
        </CardContent>
      </Card>
    )
  }

  // Show error state if data fetching failed
  if (schedulerError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-red-400" />
            <p className="text-red-600 font-medium mb-2">Failed to load scheduler data</p>
            <p className="text-sm text-warmgray-500">{schedulerError}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const toggleScheduler = (schedulerId: string) => {
    setExpandedSchedulers(prev => {
      const newSet = new Set(prev)
      if (newSet.has(schedulerId)) {
        newSet.delete(schedulerId)
      } else {
        newSet.add(schedulerId)
      }
      return newSet
    })
  }

  // Use real scheduler data from API, fallback to WebSocket health data if available
  const schedulers = schedulerData.length > 0 ? schedulerData : (status?.schedulers || [])

  return (
    <div className="space-y-4">
      {/* Overall Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              Scheduler Overview
              {status?.healthy ? (
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-600" />
              )}
            </span>
            <span className={`text-sm font-normal ${
              status?.healthy ? 'text-emerald-600' : 'text-red-600'
            }`}>
              {status?.healthy ? 'All Schedulers Operational' : 'Attention Required'}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-warmgray-900 dark:text-warmgray-100">
                {schedulers.length}
              </p>
              <p className="text-sm text-warmgray-600">Total Schedulers</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">
                {schedulers.filter(s => s.status === 'running').length}
              </p>
              <p className="text-sm text-warmgray-600">Running</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {schedulers.reduce((sum, s) => sum + s.active_jobs, 0)}
              </p>
              <p className="text-sm text-warmgray-600">Active Jobs</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">
                {schedulers.reduce((sum, s) => sum + s.jobs.length, 0)}
              </p>
              <p className="text-sm text-warmgray-600">Total Jobs</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Individual Scheduler Cards */}
      <div className="space-y-3">
        {schedulers.map((scheduler) => (
          <SchedulerCard
            key={scheduler.scheduler_id}
            scheduler={scheduler}
            isExpanded={expandedSchedulers.has(scheduler.scheduler_id)}
            onToggle={() => toggleScheduler(scheduler.scheduler_id)}
          />
        ))}
      </div>

      {schedulers.length === 0 && (
        <Card>
          <CardContent className="text-center py-8">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-warmgray-400" />
            <p className="text-warmgray-500">No scheduler data available</p>
            <p className="text-sm text-warmgray-400 mt-1">
              Schedulers may be initializing or experiencing issues
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default SchedulerStatus
