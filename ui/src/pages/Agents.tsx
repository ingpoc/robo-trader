import { useState } from 'react'
import { useAgents } from '@/hooks/useAgents'
import { AgentConfigPanel } from '@/components/Dashboard/AgentConfigPanel'
import { Button } from '@/components/ui/Button'

export function Agents() {
  const { agents, isLoading } = useAgents()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg text-gray-600">Loading agents...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6 overflow-auto">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">AI Agents</h1>
        <p className="text-sm text-gray-600">Monitor and control autonomous agents</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {Object.entries(agents).map(([name, status]) => (
          <div key={name} className="p-4 bg-white border border-gray-200 rounded">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900 capitalize">
                {name.replace('_', ' ')}
              </h3>
              <div
                className={`px-2 py-1 text-xs rounded ${
                  status.status === 'running'
                    ? 'bg-green-100 text-green-900'
                    : status.status === 'idle'
                      ? 'bg-blue-100 text-blue-900'
                      : status.status === 'error'
                        ? 'bg-red-100 text-red-900'
                        : 'bg-gray-100 text-gray-900'
                }`}
              >
                {status.status}
              </div>
            </div>
            <div className="flex flex-col gap-2 text-sm mb-3">
              <div className="text-gray-600">{status.message}</div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>Tasks: {status.tasks_completed}</span>
                <span>Uptime: {status.uptime}</span>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSelectedAgent(selectedAgent === name ? null : name)}
            >
              {selectedAgent === name ? 'Hide Config' : 'Configure'}
            </Button>
          </div>
        ))}
      </div>

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
