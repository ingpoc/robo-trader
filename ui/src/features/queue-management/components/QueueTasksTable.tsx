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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Play,
  Pause,
  RotateCcw,
  X,
  MoreHorizontal,
  Search,
  Filter,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import type { QueueTask, QueueType, TaskStatus, TaskPriority } from '@/types/queue'

interface QueueTasksTableProps {
  tasks: QueueTask[]
  selectedQueue?: QueueType
  onQueueSelect: (queueType: QueueType) => void
  isLoading?: boolean
}

const getStatusIcon = (status: TaskStatus) => {
  switch (status) {
    case 'pending':
      return <Clock className="w-4 h-4 text-yellow-600" />
    case 'executing':
      return <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-600" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-600" />
    case 'cancelled':
      return <X className="w-4 h-4 text-gray-600" />
    default:
      return <AlertCircle className="w-4 h-4 text-gray-600" />
  }
}

const getStatusBadge = (status: TaskStatus) => {
  const variants = {
    pending: 'secondary',
    executing: 'default',
    completed: 'success',
    failed: 'error',
    cancelled: 'secondary',
  } as const

  return (
    <Badge variant={variants[status] || 'secondary'}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

const getPriorityBadge = (priority: TaskPriority) => {
  const variants = {
    low: 'secondary',
    medium: 'default',
    high: 'warning',
    critical: 'error',
  } as const

  return (
    <Badge variant={variants[priority] || 'secondary'}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </Badge>
  )
}

const formatDuration = (ms?: number) => {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

const formatDateTime = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

export const QueueTasksTable: React.FC<QueueTasksTableProps> = ({
  tasks,
  selectedQueue,
  onQueueSelect,
  isLoading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | 'all'>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'priority' | 'status'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const filteredAndSortedTasks = useMemo(() => {
    let filtered = tasks.filter((task) => {
      const matchesSearch = searchTerm === '' ||
        task.task_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.id.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = statusFilter === 'all' || task.status === statusFilter
      const matchesPriority = priorityFilter === 'all' || task.priority === priorityFilter

      return matchesSearch && matchesStatus && matchesPriority
    })

    // Sort tasks
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime()
          bValue = new Date(b.created_at).getTime()
          break
        case 'priority':
          const priorityOrder = { low: 1, medium: 2, high: 3, critical: 4 }
          aValue = priorityOrder[a.priority]
          bValue = priorityOrder[b.priority]
          break
        case 'status':
          aValue = a.status
          bValue = b.status
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
  }, [tasks, searchTerm, statusFilter, priorityFilter, sortBy, sortOrder])

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

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
    <Card className="card-base">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-warmgray-900">Queue Tasks</h2>

          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-warmgray-400" />
              <Input
                placeholder="Search tasks..."
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
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="executing">Executing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>

            {/* Priority Filter */}
            <Select value={priorityFilter} onValueChange={(value) => setPriorityFilter(value as TaskPriority | 'all')}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priority</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {filteredAndSortedTasks.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Tasks Found</h3>
            <p className="text-warmgray-600">
              {tasks.length === 0
                ? 'No tasks are currently in the queue.'
                : 'No tasks match your current filters.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50"
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableHead>
                  <TableHead>Task Type</TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50"
                    onClick={() => handleSort('priority')}
                  >
                    Priority
                  </TableHead>
                  <TableHead>Queue</TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50"
                    onClick={() => handleSort('created_at')}
                  >
                    Created
                  </TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Retries</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAndSortedTasks.map((task) => (
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
                    <TableCell>{getPriorityBadge(task.priority)}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{task.queue_type.replace('_', ' ')}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {formatDateTime(task.created_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {task.execution_time_ms ? formatDuration(task.execution_time_ms) : '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {task.retry_count}/{task.max_retries}
                      </div>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem>
                            <Play className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {task.status === 'failed' && (
                            <DropdownMenuItem>
                              <RotateCcw className="w-4 h-4 mr-2" />
                              Retry Task
                            </DropdownMenuItem>
                          )}
                          {(task.status === 'pending' || task.status === 'executing') && (
                            <DropdownMenuItem>
                              <X className="w-4 h-4 mr-2" />
                              Cancel Task
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div className="flex items-center justify-between mt-4 text-sm text-warmgray-600">
          <div>
            Showing {filteredAndSortedTasks.length} of {tasks.length} tasks
          </div>
          {selectedQueue && (
            <div>
              Filtered by queue: {selectedQueue.replace('_', ' ')}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}