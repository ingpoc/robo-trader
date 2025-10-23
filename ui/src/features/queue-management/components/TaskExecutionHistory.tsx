import React, { useState, useMemo } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Search,
  Filter,
  XCircle,
  RotateCcw,
  Info,
} from 'lucide-react'
import type { TaskExecutionHistory, QueueType, TaskStatus, TaskPriority } from '@/types/queue'

interface TaskExecutionHistoryProps {
  history: TaskExecutionHistory[]
  selectedQueue?: QueueType
  onQueueSelect: (queueType: QueueType) => void
  isLoading?: boolean
}

const getStatusIcon = (status: TaskStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-600" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-600" />
    case 'cancelled':
      return <RotateCcw className="w-4 h-4 text-gray-600" />
    default:
      return <Clock className="w-4 h-4 text-blue-600" />
  }
}

const getStatusBadge = (status: TaskStatus) => {
  const variants = {
    completed: 'success',
    failed: 'error',
    cancelled: 'secondary',
    pending: 'secondary',
    executing: 'default',
  } as const

  return (
    <Badge variant={variants[status] || 'secondary'}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

const formatDuration = (ms?: number) => {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = ((ms % 60000) / 1000).toFixed(1)
  return `${minutes}m ${seconds}s`
}

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

const ErrorDetailsModal: React.FC<{
  task: TaskExecutionHistory
  isOpen: boolean
  onClose: () => void
}> = ({ task, isOpen, onClose }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-warmgray-900">Task Error Details</h3>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <XCircle className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-warmgray-700">Task ID</label>
                <p className="text-sm font-mono text-warmgray-900">{task.id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-warmgray-700">Task Type</label>
                <p className="text-sm text-warmgray-900">{task.task_type}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-warmgray-700">Queue</label>
                <p className="text-sm text-warmgray-900">{task.queue_type.replace('_', ' ')}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-warmgray-700">Failed At</label>
                <p className="text-sm text-warmgray-900">{formatDateTime(task.failed_at!)}</p>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-warmgray-700">Error Message</label>
              <div className="mt-1 p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800 font-mono whitespace-pre-wrap">
                  {task.error_message || 'No error message available'}
                </p>
              </div>
            </div>

            {task.metadata && Object.keys(task.metadata).length > 0 && (
              <div>
                <label className="text-sm font-medium text-warmgray-700">Task Metadata</label>
                <div className="mt-1 p-3 bg-warmgray-50 border border-warmgray-200 rounded-md">
                  <pre className="text-xs text-warmgray-800 whitespace-pre-wrap">
                    {JSON.stringify(task.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export const TaskExecutionHistory: React.FC<TaskExecutionHistoryProps> = ({
  history,
  selectedQueue,
  onQueueSelect,
  isLoading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')
  const [selectedTask, setSelectedTask] = useState<TaskExecutionHistory | null>(null)
  const [sortBy, setSortBy] = useState<'created_at' | 'execution_time_ms'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const filteredAndSortedHistory = useMemo(() => {
    let filtered = history.filter((task) => {
      const matchesSearch = searchTerm === '' ||
        task.task_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (task.error_message && task.error_message.toLowerCase().includes(searchTerm.toLowerCase()))

      const matchesStatus = statusFilter === 'all' || task.status === statusFilter

      return matchesSearch && matchesStatus
    })

    // Sort history
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime()
          bValue = new Date(b.created_at).getTime()
          break
        case 'execution_time_ms':
          aValue = a.execution_time_ms || 0
          bValue = b.execution_time_ms || 0
          break
        default:
          return 0
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

    return filtered
  }, [history, searchTerm, statusFilter, sortBy, sortOrder])

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const failedTasks = filteredAndSortedHistory.filter(task => task.status === 'failed')
  const successRate = history.length > 0 ? ((history.length - failedTasks.length) / history.length * 100) : 100

  if (isLoading) {
    return (
      <Card className="card-base">
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-warmgray-200 rounded w-1/4"></div>
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-warmgray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <>
      <Card className="card-base">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-warmgray-900">Task Execution History</h2>
              <div className="flex items-center gap-4 mt-2 text-sm text-warmgray-600">
                <span>Total: {history.length}</span>
                <span>Success Rate: {successRate.toFixed(1)}%</span>
                <span>Failed: {failedTasks.length}</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-warmgray-400" />
                <Input
                  placeholder="Search history..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>

              {/* Status Filter */}
              <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as TaskStatus | 'all')}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {filteredAndSortedHistory.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No History Found</h3>
              <p className="text-warmgray-600">
                {history.length === 0
                  ? 'No task execution history available.'
                  : 'No tasks match your current filters.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Task Type</TableHead>
                    <TableHead>Queue</TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-warmgray-50"
                      onClick={() => handleSort('created_at')}
                    >
                      Started
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-warmgray-50"
                      onClick={() => handleSort('execution_time_ms')}
                    >
                      Duration
                    </TableHead>
                    <TableHead>Retries</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedHistory.map((task) => (
                    <TableRow key={task.id} className="hover:bg-warmgray-50">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(task.status)}
                          {getStatusBadge(task.status)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium text-warmgray-900">{task.task_type}</div>
                          <div className="text-xs text-warmgray-500 font-mono">{task.id.slice(0, 8)}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{task.queue_type.replace('_', ' ')}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {formatDateTime(task.started_at || task.created_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {formatDuration(task.execution_time_ms)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {task.retry_count}
                        </div>
                      </TableCell>
                      <TableCell>
                        {task.status === 'failed' && task.error_message && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedTask(task)}
                          >
                            <Info className="w-4 h-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="flex items-center justify-between mt-4 text-sm text-warmgray-600">
            <div>
              Showing {filteredAndSortedHistory.length} of {history.length} tasks
            </div>
            {selectedQueue && (
              <div>
                Filtered by queue: {selectedQueue.replace('_', ' ')}
              </div>
            )}
          </div>
        </div>
      </Card>

      <ErrorDetailsModal
        task={selectedTask!}
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
      />
    </>
  )
}