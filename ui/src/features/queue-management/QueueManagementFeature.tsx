import React, { useState, useEffect } from 'react'
import { useQueueManagement } from '@/hooks/useQueue'
import { useQueueStore } from '@/stores/queueStore'
import { QueueStatusOverview } from './components/QueueStatusOverview'
import { QueueTasksTable } from './components/QueueTasksTable'
import { QueueConfigurationPanel } from './components/QueueConfigurationPanel'
import { TaskExecutionHistory } from './components/TaskExecutionHistory'
import { QueuePerformanceMetrics } from './components/QueuePerformanceMetrics'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Activity, Settings, BarChart3, History, Play, Pause, RotateCcw, AlertTriangle, Loader2 } from 'lucide-react'
import type { QueueType } from '@/types/queue'

const QueueManagementFeature: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview')
  const { selectedQueue, setSelectedQueue } = useQueueStore()
  const {
    statuses,
    tasks,
    history,
    metrics,
    health,
    triggerTask,
    pauseQueue,
    resumeQueue,
    clearCompleted,
    isLoading,
    error,
  } = useQueueManagement(selectedQueue)

  const handleQueueSelect = (queueType: QueueType) => {
    setSelectedQueue(queueType)
  }

  const handleTriggerTask = () => {
    if (selectedQueue) {
      triggerTask.mutate({
        queue_type: selectedQueue,
        task_type: 'manual_trigger',
      })
    }
  }

  const handlePauseQueue = () => {
    if (selectedQueue) {
      pauseQueue.mutate(selectedQueue)
    }
  }

  const handleResumeQueue = () => {
    if (selectedQueue) {
      resumeQueue.mutate(selectedQueue)
    }
  }

  const handleClearCompleted = () => {
    clearCompleted.mutate(selectedQueue)
  }

  // Initialize WebSocket connection for real-time updates
  useEffect(() => {
    // WebSocket integration is handled in the useQueueWebSocket hook
    // which is called within useQueueManagement
  }, [])

  if (error) {
    return (
      <div className="page-wrapper">
        <div className="page-header">
          <h1 className="page-title">Queue Management</h1>
          <p className="page-subtitle">Monitor and manage background task queues</p>
        </div>

        <Card className="card-base">
          <div className="p-6 text-center">
            <div className="text-red-600 mb-4">
              <Activity className="w-12 h-12 mx-auto mb-2" />
              <h3 className="text-lg font-semibold">Connection Error</h3>
            </div>
            <p className="text-warmgray-600 mb-4">{error}</p>
            <Button
              onClick={() => window.location.reload()}
              className="btn-primary"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Retry Connection
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Queue Management</h1>
            <p className="page-subtitle">Monitor and manage background task queues</p>
          </div>

          <div className="flex items-center gap-3">
            {selectedQueue && (
              <>
                <Button
                  onClick={handleTriggerTask}
                  disabled={triggerTask.isPending || isLoading}
                  className="btn-primary"
                >
                  {triggerTask.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Trigger Task
                </Button>

                <Button
                  onClick={handlePauseQueue}
                  disabled={pauseQueue.isPending || isLoading}
                  variant="outline"
                >
                  {pauseQueue.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Pause className="w-4 h-4 mr-2" />
                  )}
                  Pause Queue
                </Button>

                <Button
                  onClick={handleResumeQueue}
                  disabled={resumeQueue.isPending || isLoading}
                  variant="outline"
                >
                  {resumeQueue.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Resume Queue
                </Button>

                <Button
                  onClick={handleClearCompleted}
                  disabled={clearCompleted.isPending || isLoading}
                  variant="outline"
                >
                  {clearCompleted.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4 mr-2" />
                  )}
                  Clear Completed
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Health Status */}
        {health.data && (
          <div className="flex items-center gap-4 mt-4">
            <Badge
              variant={
                health.data.overall_health === 'healthy'
                  ? 'success'
                  : health.data.overall_health === 'warning'
                  ? 'warning'
                  : 'error'
              }
            >
              System Health: {health.data.overall_health}
            </Badge>

            {statuses.data?.stats && (
              <div className="flex items-center gap-4 text-sm text-warmgray-600">
                <span>Active Queues: {statuses.data.stats.active_queues}</span>
                <span>Total Tasks: {statuses.data.stats.total_pending_tasks}</span>
                <span>Failed Tasks: {statuses.data.stats.total_failed_tasks}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList
          className="grid w-full grid-cols-5"
          role="tablist"
          aria-label="Queue management sections"
        >
          <TabsTrigger
            value="overview"
            className="flex items-center gap-2"
            aria-controls="overview-panel"
          >
            <Activity className="w-4 h-4" aria-hidden="true" />
            Overview
          </TabsTrigger>
          <TabsTrigger
            value="tasks"
            className="flex items-center gap-2"
            aria-controls="tasks-panel"
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            Tasks
          </TabsTrigger>
          <TabsTrigger
            value="history"
            className="flex items-center gap-2"
            aria-controls="history-panel"
          >
            <History className="w-4 h-4" aria-hidden="true" />
            History
          </TabsTrigger>
          <TabsTrigger
            value="metrics"
            className="flex items-center gap-2"
            aria-controls="metrics-panel"
          >
            <BarChart3 className="w-4 h-4" aria-hidden="true" />
            Metrics
          </TabsTrigger>
          <TabsTrigger
            value="config"
            className="flex items-center gap-2"
            aria-controls="config-panel"
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            Configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="overview"
          className="space-y-6"
          id="overview-panel"
          role="tabpanel"
          aria-labelledby="overview-tab"
        >
          <QueueStatusOverview
            statuses={statuses.data?.queues || []}
            onQueueSelect={handleQueueSelect}
            selectedQueue={selectedQueue}
            isLoading={statuses.isLoading}
          />
        </TabsContent>

        <TabsContent
          value="tasks"
          className="space-y-6"
          id="tasks-panel"
          role="tabpanel"
          aria-labelledby="tasks-tab"
        >
          <QueueTasksTable
            tasks={tasks.data?.tasks || []}
            selectedQueue={selectedQueue}
            onQueueSelect={handleQueueSelect}
            isLoading={tasks.isLoading}
          />
        </TabsContent>

        <TabsContent
          value="history"
          className="space-y-6"
          id="history-panel"
          role="tabpanel"
          aria-labelledby="history-tab"
        >
          <TaskExecutionHistory
            history={history.data?.history || []}
            selectedQueue={selectedQueue}
            onQueueSelect={handleQueueSelect}
            isLoading={history.isLoading}
          />
        </TabsContent>

        <TabsContent
          value="metrics"
          className="space-y-6"
          id="metrics-panel"
          role="tabpanel"
          aria-labelledby="metrics-tab"
        >
          <QueuePerformanceMetrics
            metrics={metrics.data?.metrics || []}
            selectedQueue={selectedQueue}
            onQueueSelect={handleQueueSelect}
            isLoading={metrics.isLoading}
          />
        </TabsContent>

        <TabsContent
          value="config"
          className="space-y-6"
          id="config-panel"
          role="tabpanel"
          aria-labelledby="config-tab"
        >
          <QueueConfigurationPanel
            selectedQueue={selectedQueue}
            onQueueSelect={handleQueueSelect}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export { QueueManagementFeature }