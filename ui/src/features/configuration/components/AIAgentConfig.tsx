import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Brain, RefreshCw, Play, Loader2 } from 'lucide-react'
import type { AIAgentConfig } from '@/types/api'
import { getFrequencyDisplay, getScopeColor, formatTaskName } from '../utils'

interface AIAgentConfigProps {
  aiAgents: Record<string, AIAgentConfig>
  executingAgents: Set<string>
  isLoading: boolean
  onUpdateAgent: (agentName: string, field: keyof AIAgentConfig, value: any) => void
  onExecuteAgent: (agentName: string) => void
}

export const AIAgentConfigComponent: React.FC<AIAgentConfigProps> = ({
  aiAgents,
  executingAgents,
  isLoading,
  onUpdateAgent,
  onExecuteAgent,
}) => {
  if (isLoading) {
    return (
      <div className="text-center py-8">
        <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
        <p className="text-gray-600">Loading AI agents configuration...</p>
      </div>
    )
  }

  if (Object.keys(aiAgents).length === 0) {
    return (
      <div className="text-center py-8">
        <Brain className="w-8 h-8 mx-auto mb-3 text-gray-400" />
        <p className="text-gray-600">No AI agents configured</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Configure AI agents that perform specialized analysis and decision-making tasks.
          Control their tools, response frequency, and analysis scope.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4">
        {Object.entries(aiAgents).map(([agentName, config]) => (
          <Card key={agentName}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{formatTaskName(agentName)}</CardTitle>
                  <CardDescription>AI agent with specialized capabilities</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={getScopeColor(config.scope)}>{config.scope}</Badge>
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={(checked) => onUpdateAgent(agentName, 'enabled', checked)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={`${agentName}-claude`}>Claude AI Usage</Label>
                  <div className="flex items-center gap-2">
                    <Switch
                      id={`${agentName}-claude`}
                      checked={config.useClaude}
                      onCheckedChange={(checked) => onUpdateAgent(agentName, 'useClaude', checked)}
                      disabled={!config.enabled}
                    />
                    <span className="text-sm text-gray-600">
                      {config.useClaude ? 'AI-powered' : 'Basic mode'}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${agentName}-scope`}>Analysis Scope</Label>
                  <Select
                    value={config.scope}
                    onValueChange={(value) => onUpdateAgent(agentName, 'scope', value)}
                    disabled={!config.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="portfolio">Portfolio</SelectItem>
                      <SelectItem value="market">Market</SelectItem>
                      <SelectItem value="watchlist">Watchlist</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${agentName}-frequency`}>Response Frequency</Label>
                  <div className="flex gap-2">
                    <Input
                      id={`${agentName}-frequency`}
                      type="number"
                      min="1"
                      value={config.responseFrequency}
                      onChange={(e) => onUpdateAgent(agentName, 'responseFrequency', parseInt(e.target.value))}
                      className="w-24"
                      disabled={!config.enabled}
                    />
                    <Select
                      value={config.responseFrequencyUnit}
                      onValueChange={(value) => onUpdateAgent(agentName, 'responseFrequencyUnit', value)}
                      disabled={!config.enabled}
                    >
                      <SelectTrigger className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="minutes">Minutes</SelectItem>
                        <SelectItem value="hours">Hours</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${agentName}-tokens`}>Max Tokens per Request</Label>
                  <Input
                    id={`${agentName}-tokens`}
                    type="number"
                    min="500"
                    max="8000"
                    step="500"
                    value={config.maxTokensPerRequest}
                    onChange={(e) => onUpdateAgent(agentName, 'maxTokensPerRequest', parseInt(e.target.value))}
                    disabled={!config.enabled}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Available Tools</Label>
                <div className="flex flex-wrap gap-1">
                  {config.tools.map(tool => (
                    <Badge key={tool} variant="tertiary" className="text-xs">
                      {tool.replace('_', ' ')}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="text-sm text-gray-600">
                <Brain className="inline w-3 h-3 mr-1" />
                Responds every {getFrequencyDisplay(config.responseFrequency, config.responseFrequencyUnit)}
              </div>

              {/* Action Button */}
              <div className="pt-4 border-t">
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => onExecuteAgent(agentName)}
                  disabled={executingAgents.has(agentName) || !config.enabled}
                  className="w-full"
                >
                  {executingAgents.has(agentName) ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Run Now
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
