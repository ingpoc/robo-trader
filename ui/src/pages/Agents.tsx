import { useState } from 'react'
import { useAgents } from '@/hooks/useAgents'
import { AgentConfigPanel } from '@/components/Dashboard/AgentConfigPanel'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { CheckCircle, XCircle, Clock, AlertTriangle, Settings, Activity, Users } from 'lucide-react'

export function Agents() {
  const { agents, isLoading } = useAgents()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-6 animate-fade-in">
        <Breadcrumb />
        <div className="flex flex-col gap-4">
          <SkeletonLoader className="h-8 w-48" />
          <SkeletonLoader className="h-4 w-64" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="shadow-sm">
              <CardHeader>
                <SkeletonLoader className="h-6 w-32" />
              </CardHeader>
              <CardContent className="space-y-3">
                <SkeletonLoader className="h-4 w-full" />
                <SkeletonLoader className="h-4 w-3/4" />
                <SkeletonLoader className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">AI Agents</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Monitor and control autonomous trading agents</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(agents).map(([name, status]) => (
          <Card key={name} className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg capitalize flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-600" />
                  {name.replace('_', ' ')}
                </CardTitle>
                <div
                  className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 ${
                    status.status === 'running'
                      ? 'bg-green-100 text-green-900 dark:bg-green-900 dark:text-green-200'
                      : status.status === 'idle'
                        ? 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-200'
                        : status.status === 'error'
                          ? 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-200'
                          : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-200'
                  }`}
                >
                  {status.status === 'running' ? (
                    <CheckCircle className="w-3 h-3" />
                  ) : status.status === 'error' ? (
                    <XCircle className="w-3 h-3" />
                  ) : status.status === 'idle' ? (
                    <Clock className="w-3 h-3" />
                  ) : (
                    <AlertTriangle className="w-3 h-3" />
                  )}
                  {status.status}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <div>{status.message}</div>
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-500">
                  <span>Tasks: {status.tasks_completed}</span>
                  <span>Uptime: {status.uptime}</span>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedAgent(selectedAgent === name ? null : name)}
                className="w-full"
                aria-label={`Configure ${name.replace('_', ' ')} agent`}
              >
                <Settings className="w-4 h-4 mr-2" />
                {selectedAgent === name ? 'Hide Config' : 'Configure'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {Object.keys(agents).length === 0 && (
        <Card className="shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Activity className="w-12 h-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Agents Configured</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
              Configure AI agents to start automated trading and monitoring.
            </p>
          </CardContent>
        </Card>
      )}

      {selectedAgent && (
        <div className="mt-6">
          <AgentConfigPanel
            agentName={selectedAgent}
            onClose={() => setSelectedAgent(null)}
          />
        </div>
      )}
    </div>
  )
}