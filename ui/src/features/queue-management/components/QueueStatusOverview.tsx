import React from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/progress'
import {
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Play,
  Pause,
  Settings
} from 'lucide-react'
import type { QueueStatus, QueueType } from '@/types/queue'

interface QueueStatusOverviewProps {
  statuses: QueueStatus[]
  onQueueSelect: (queueType: QueueType) => void
  selectedQueue?: QueueType
  isLoading?: boolean
}

const getQueueIcon = (queueType: QueueType) => {
  switch (queueType) {
    case 'PORTFOLIO_SCHEDULER':
      return <Activity className="w-5 h-5" />
    case 'DATA_FETCHER_SCHEDULER':
      return <Clock className="w-5 h-5" />
    case 'AI_ANALYSIS_QUEUE':
      return <Settings className="w-5 h-5" />
    default:
      return <Activity className="w-5 h-5" />
  }
}

const getQueueColor = (queueType: QueueType) => {
  switch (queueType) {
    case 'PORTFOLIO_SCHEDULER':
      return 'text-blue-600'
    case 'DATA_FETCHER_SCHEDULER':
      return 'text-green-600'
    case 'AI_ANALYSIS_QUEUE':
      return 'text-purple-600'
    default:
      return 'text-gray-600'
  }
}

const getStatusBadge = (isActive: boolean) => {
  return (
    <Badge variant={isActive ? 'success' : 'secondary'}>
      {isActive ? (
        <>
          <Play className="w-3 h-3 mr-1" />
          Active
        </>
      ) : (
        <>
          <Pause className="w-3 h-3 mr-1" />
          Paused
        </>
      )}
    </Badge>
  )
}

const QueueCard: React.FC<{
  status: QueueStatus
  isSelected: boolean
  onSelect: () => void
}> = ({ status, isSelected, onSelect }) => {
  const totalTasks = status.total_tasks
  const activeTasks = status.pending_tasks + status.executing_tasks
  const completionRate = totalTasks > 0 ? ((status.completed_tasks / totalTasks) * 100) : 0

  return (
    <Card
      className={`card-interactive cursor-pointer transition-all duration-200 ${
        isSelected ? 'ring-2 ring-copper-500 shadow-lg' : ''
      }`}
      onClick={onSelect}
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg bg-warmgray-100 ${getQueueColor(status.queue_type)}`}>
              {getQueueIcon(status.queue_type)}
            </div>
            <div>
              <h3 className="font-semibold text-warmgray-900">{status.name}</h3>
              <p className="text-sm text-warmgray-600">{status.description}</p>
            </div>
          </div>
          {getStatusBadge(status.is_active)}
        </div>

        <div className="space-y-4">
          {/* Task Statistics */}
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-warmgray-900">{status.pending_tasks}</div>
              <div className="text-xs text-warmgray-600 uppercase tracking-wide">Pending</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{status.executing_tasks}</div>
              <div className="text-xs text-warmgray-600 uppercase tracking-wide">Executing</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-warmgray-600">Completion Rate</span>
              <span className="font-medium">{completionRate.toFixed(1)}%</span>
            </div>
            <Progress value={completionRate} className="h-2" />
          </div>

          {/* Performance Metrics */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-warmgray-200">
            <div className="text-center">
              <div className="text-lg font-semibold text-warmgray-900">
                {status.throughput_per_minute.toFixed(1)}
              </div>
              <div className="text-xs text-warmgray-600">Tasks/min</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-warmgray-900">
                {status.average_execution_time_ms.toFixed(0)}ms
              </div>
              <div className="text-xs text-warmgray-600">Avg Time</div>
            </div>
            <div className="text-center">
              <div className={`text-lg font-semibold ${
                status.error_rate_percentage > 5 ? 'text-red-600' :
                status.error_rate_percentage > 1 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {status.error_rate_percentage.toFixed(1)}%
              </div>
              <div className="text-xs text-warmgray-600">Error Rate</div>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex items-center justify-between pt-4 border-t border-warmgray-200">
            <div className="flex items-center gap-4">
              {status.failed_tasks > 0 && (
                <div className="flex items-center gap-1 text-red-600">
                  <XCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">{status.failed_tasks} failed</span>
                </div>
              )}
              {status.error_rate_percentage > 5 && (
                <div className="flex items-center gap-1 text-yellow-600">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm font-medium">High error rate</span>
                </div>
              )}
            </div>

            {status.last_activity_at && (
              <div className="text-xs text-warmgray-500">
                Last activity: {new Date(status.last_activity_at).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}

export const QueueStatusOverview: React.FC<QueueStatusOverviewProps> = ({
  statuses,
  onQueueSelect,
  selectedQueue,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="card-base">
            <div className="p-6 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-warmgray-200 rounded-lg"></div>
                <div className="flex-1">
                  <div className="h-4 bg-warmgray-200 rounded mb-2"></div>
                  <div className="h-3 bg-warmgray-200 rounded"></div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="h-8 bg-warmgray-200 rounded"></div>
                  <div className="h-8 bg-warmgray-200 rounded"></div>
                </div>
                <div className="h-2 bg-warmgray-200 rounded"></div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="h-6 bg-warmgray-200 rounded"></div>
                  <div className="h-6 bg-warmgray-200 rounded"></div>
                  <div className="h-6 bg-warmgray-200 rounded"></div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  if (statuses.length === 0) {
    return (
      <Card className="card-base">
        <div className="p-12 text-center">
          <Activity className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Queues Available</h3>
          <p className="text-warmgray-600">Unable to load queue status information.</p>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-warmgray-900">Queue Status Overview</h2>
        <div className="text-sm text-warmgray-600">
          {statuses.filter(q => q.is_active).length} of {statuses.length} queues active
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statuses.map((status) => (
          <QueueCard
            key={status.queue_type}
            status={status}
            isSelected={selectedQueue === status.queue_type}
            onSelect={() => onQueueSelect(status.queue_type)}
          />
        ))}
      </div>
    </div>
  )
}