/**
 * Agents Feature Component
 * Main orchestrator for agent management and configuration
 */

import React, { useState } from 'react'
import { useAgents } from '@/hooks/useAgents'
import { useAgentConfig } from './hooks/useAgentConfig'
import { AgentCard } from './components/AgentCard'
import { AgentConfigCard } from './components/AgentConfigCard'
import { Card, CardContent } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Activity, SkeletonLoader, AlertCircle } from 'lucide-react'

export interface AgentsFeatureProps {
  onClose?: () => void
}

export const AgentsFeature: React.FC<AgentsFeatureProps> = ({ onClose }) => {
  const { agents, isLoading: agentsLoading } = useAgents()
  const { features, loading: configLoading, error: configError, updateFeature } = useAgentConfig()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'agents' | 'config'>('agents')

  const isLoading = agentsLoading || configLoading
  const hasAgents = Object.keys(agents).length > 0
  const hasFeatures = features && Object.keys(features).length > 0

  // Render loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-4">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-4 w-64 bg-muted rounded animate-pulse" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="space-y-3 pt-6">
                <div className="h-6 w-32 bg-muted rounded animate-pulse" />
                <div className="h-4 w-full bg-muted rounded animate-pulse" />
                <div className="h-8 w-24 bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">
          AI Agents
        </h2>
        <p className="text-warmgray-600 dark:text-warmgray-400">
          Monitor and control autonomous trading agents
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(tab) => setActiveTab(tab as 'agents' | 'config')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="agents">Active Agents</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        {/* Agents Tab */}
        <TabsContent value="agents" className="space-y-4">
          {!hasAgents ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Activity className="w-12 h-12 text-warmgray-400 mb-4" />
                <h3 className="text-lg font-medium text-warmgray-900 dark:text-warmgray-100 mb-2 font-serif">
                  No Agents Configured
                </h3>
                <p className="text-sm text-warmgray-600 dark:text-warmgray-400 text-center max-w-xs">
                  Configure AI agents to start automated trading and monitoring.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.entries(agents).map(([name, status]) => (
                <AgentCard
                  key={name}
                  name={name}
                  status={status}
                  isClaudeAgent={name === 'claude_paper_trader'}
                  onConfigure={() => {
                    setSelectedAgent(name)
                    setActiveTab('config')
                  }}
                />
              ))}
            </div>
          )}

          {/* Selected Agent Config */}
          {selectedAgent && hasFeatures && (
            <div className="mt-6 space-y-4">
              <h3 className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100">
                {selectedAgent.replace(/_/g, ' ')} - Configuration
              </h3>
              {Object.entries(features).map(([featureName, config]) => (
                <AgentConfigCard
                  key={featureName}
                  featureName={featureName}
                  config={config}
                  onUpdate={(updates) => updateFeature(featureName, updates)}
                  error={configError}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-4">
          {configError && (
            <div className="flex items-start gap-2 p-4 bg-red-50 dark:bg-red-950 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-semibold text-red-600 mb-1">Configuration Error</h4>
                <p className="text-sm text-red-600">{configError}</p>
              </div>
            </div>
          )}

          {!hasFeatures ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Activity className="w-12 h-12 text-warmgray-400 mb-4" />
                <h3 className="text-lg font-medium text-warmgray-900 dark:text-warmgray-100 mb-2 font-serif">
                  No Features Available
                </h3>
                <p className="text-sm text-warmgray-600 dark:text-warmgray-400 text-center max-w-xs">
                  Agent features will appear here once configured.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {Object.entries(features).map(([featureName, config]) => (
                <AgentConfigCard
                  key={featureName}
                  featureName={featureName}
                  config={config}
                  onUpdate={(updates) => updateFeature(featureName, updates)}
                  error={configError}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AgentsFeature
