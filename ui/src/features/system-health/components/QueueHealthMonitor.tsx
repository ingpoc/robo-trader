/**
 * Queue Health Monitor Component
 * Displays health and status of all task queues
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

export interface QueueHealthMonitorProps {
  health: any | null
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Queue Health</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Total Tasks Queued</span>
          <span className="text-2xl font-bold">{health?.totalTasks || 0}</span>
        </div>
        {health?.queues?.map((queue: any, index: number) => (
          <div key={index} className="border-t pt-3">
            <p className="font-semibold">{queue.name}</p>
            <div className="flex justify-between text-sm text-warmgray-600 mt-2">
              <span>Tasks: {queue.taskCount}</span>
              <span>Success Rate: {queue.successRate?.toFixed(1)}%</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export default QueueHealthMonitor
