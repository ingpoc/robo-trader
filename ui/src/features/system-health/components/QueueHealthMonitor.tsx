/**
 * Queue Health Monitor Component
 * Displays health and status of all task queues
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

export interface QueueHealthMonitorProps {
  health: {
    healthy: boolean
    totalTasks: number
    runningQueues: number
    totalQueues: number
  } | null
  isLoading: boolean
}

export const QueueHealthMonitor: React.FC<QueueHealthMonitorProps> = ({ health, isLoading }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading queue health...</p>
        </CardContent>
      </Card>
    )
  }

  const getStatusColor = (healthy: boolean) => {
    return healthy ? 'text-emerald-600' : 'text-rose-600'
  }

  const getStatusText = (healthy: boolean) => {
    return healthy ? 'Healthy' : 'Error'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Queue Health
          <span className={`text-sm font-normal ${getStatusColor(health?.healthy ?? false)}`}>
            {getStatusText(health?.healthy ?? false)}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Total Tasks</span>
          <span className="text-2xl font-bold">{health?.totalTasks || 0}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Running Queues</span>
          <span className="text-lg font-semibold">{health?.runningQueues || 0}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Total Queues</span>
          <span className="text-lg font-semibold">{health?.totalQueues || 0}</span>
        </div>

        {/* Add a simple queue visualization */}
        {(health?.totalQueues ?? 0) > 0 && (
          <div className="border-t pt-4">
            <p className="text-sm text-warmgray-600 mb-2">Queue Distribution</p>
            <div className="w-full bg-warmgray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  health?.healthy ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
                style={{
                  width: `${Math.min(((health?.runningQueues ?? 0) / Math.max(health?.totalQueues ?? 1)) * 100, 100)}%`
                }}
              />
            </div>
            <p className="text-xs text-warmgray-500 mt-1">
              {health?.runningQueues || 0} of {health?.totalQueues || 0} queues active
            </p>
          </div>
        )}

        {health === null && (
          <p className="text-warmgray-500 text-sm">No queue data available</p>
        )}
      </CardContent>
    </Card>
  )
}

export default QueueHealthMonitor
