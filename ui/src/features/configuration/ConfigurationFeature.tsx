import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Settings, Cpu, Brain, Globe, Clock, ToggleLeft, Zap } from 'lucide-react'

// Type definitions for our configuration interfaces
interface BackgroundTaskConfig {
  enabled: boolean
  frequency: number
  frequencyUnit: 'seconds' | 'minutes' | 'hours' | 'days'
  useClaude: boolean
  priority: 'low' | 'medium' | 'high'
  stockSymbols: string[]
}

interface AIAgentConfig {
  enabled: boolean
  useClaude: boolean
  tools: string[]
  responseFrequency: number
  responseFrequencyUnit: 'minutes' | 'hours'
  scope: 'portfolio' | 'market' | 'watchlist'
  maxTokensPerRequest: number
}

interface GlobalConfig {
  claudeUsage: {
    enabled: boolean
    dailyTokenLimit: number
    costAlerts: boolean
    costThreshold: number
  }
  schedulerDefaults: {
    defaultFrequency: number
    defaultFrequencyUnit: 'minutes' | 'hours'
    marketHoursOnly: boolean
    retryAttempts: number
    retryDelayMinutes: number
  }
}

const ConfigurationFeature: React.FC = () => {
  // Background tasks state
  const [backgroundTasks, setBackgroundTasks] = useState<Record<string, BackgroundTaskConfig>>({
    earnings_processor: {
      enabled: true,
      frequency: 1,
      frequencyUnit: 'hours',
      useClaude: true,
      priority: 'high',
      stockSymbols: []
    },
    news_processor: {
      enabled: true,
      frequency: 30,
      frequencyUnit: 'minutes',
      useClaude: true,
      priority: 'medium',
      stockSymbols: []
    },
    fundamental_analyzer: {
      enabled: false,
      frequency: 4,
      frequencyUnit: 'hours',
      useClaude: true,
      priority: 'medium',
      stockSymbols: []
    },
    deep_fundamental_processor: {
      enabled: false,
      frequency: 24,
      frequencyUnit: 'hours',
      useClaude: true,
      priority: 'low',
      stockSymbols: []
    }
  })

  // AI agents state
  const [aiAgents, setAIAgents] = useState<Record<string, AIAgentConfig>>({
    technical_analyst: {
      enabled: true,
      useClaude: true,
      tools: ['analyze_chart_patterns', 'calculate_indicators', 'identify_support_resistance'],
      responseFrequency: 30,
      responseFrequencyUnit: 'minutes',
      scope: 'portfolio',
      maxTokensPerRequest: 2000
    },
    fundamental_screener: {
      enabled: false,
      useClaude: true,
      tools: ['analyze_financials', 'screen_stocks', 'calculate_valuation'],
      responseFrequency: 2,
      responseFrequencyUnit: 'hours',
      scope: 'market',
      maxTokensPerRequest: 3000
    },
    risk_manager: {
      enabled: true,
      useClaude: true,
      tools: ['assess_portfolio_risk', 'calculate_position_size', 'monitor_drawdown'],
      responseFrequency: 15,
      responseFrequencyUnit: 'minutes',
      scope: 'portfolio',
      maxTokensPerRequest: 1500
    },
    portfolio_analyzer: {
      enabled: true,
      useClaude: true,
      tools: ['analyze_performance', 'calculate_metrics', 'identify_optimization'],
      responseFrequency: 1,
      responseFrequencyUnit: 'hours',
      scope: 'portfolio',
      maxTokensPerRequest: 2500
    }
  })

  // Global settings state
  const [globalSettings, setGlobalSettings] = useState<GlobalConfig>({
    claudeUsage: {
      enabled: true,
      dailyTokenLimit: 50000,
      costAlerts: true,
      costThreshold: 10.00
    },
    schedulerDefaults: {
      defaultFrequency: 30,
      defaultFrequencyUnit: 'minutes',
      marketHoursOnly: true,
      retryAttempts: 3,
      retryDelayMinutes: 5
    }
  })

  const [activeTab, setActiveTab] = useState('background-tasks')

  // Helper functions
  const getFrequencyDisplay = (frequency: number, unit: string) => {
    if (frequency === 1) {
      return `1 ${unit.slice(0, -1)}`
    }
    return `${frequency} ${unit}`
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'destructive'
      case 'medium': return 'default'
      case 'low': return 'secondary'
      default: return 'default'
    }
  }

  const getScopeColor = (scope: string) => {
    switch (scope) {
      case 'portfolio': return 'default'
      case 'market': return 'secondary'
      case 'watchlist': return 'outline'
      default: return 'default'
    }
  }

  // Update handlers
  const updateBackgroundTask = (taskName: string, field: keyof BackgroundTaskConfig, value: any) => {
    setBackgroundTasks(prev => ({
      ...prev,
      [taskName]: {
        ...prev[taskName],
        [field]: value
      }
    }))
  }

  const updateAIAgent = (agentName: string, field: keyof AIAgentConfig, value: any) => {
    setAIAgents(prev => ({
      ...prev,
      [agentName]: {
        ...prev[agentName],
        [field]: value
      }
    }))
  }

  const updateGlobalSetting = (section: keyof GlobalConfig, field: string, value: any) => {
    setGlobalSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }))
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configuration</h1>
          <p className="text-gray-600 mt-1">Manage background tasks, AI agents, and system settings</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <Settings className="w-4 h-4" />
            Reset to Defaults
          </Button>
          <Button className="gap-2">
            <Zap className="w-4 h-4" />
            Save Configuration
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="background-tasks" className="flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            Background Tasks
          </TabsTrigger>
          <TabsTrigger value="ai-agents" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            AI Agents
          </TabsTrigger>
          <TabsTrigger value="global-settings" className="flex items-center gap-2">
            <Globe className="w-4 h-4" />
            Global Settings
          </TabsTrigger>
        </TabsList>

        {/* Background Tasks Tab */}
        <TabsContent value="background-tasks" className="space-y-6">
          <div className="grid gap-4">
            <Alert>
              <AlertDescription>
                Configure background scheduler tasks that process data automatically.
                Set frequency, Claude usage, and priority for each task.
              </AlertDescription>
            </Alert>

            {Object.entries(backgroundTasks).map(([taskName, config]) => (
              <Card key={taskName}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        {taskName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </CardTitle>
                      <CardDescription>
                        Background scheduler processor
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getPriorityColor(config.priority)}>
                        {config.priority} priority
                      </Badge>
                      <Switch
                        checked={config.enabled}
                        onCheckedChange={(checked) => updateBackgroundTask(taskName, 'enabled', checked)}
                      />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor={`${taskName}-frequency`}>Frequency</Label>
                      <div className="flex gap-2">
                        <Input
                          id={`${taskName}-frequency`}
                          type="number"
                          min="1"
                          value={config.frequency}
                          onChange={(e) => updateBackgroundTask(taskName, 'frequency', parseInt(e.target.value))}
                          className="w-24"
                          disabled={!config.enabled}
                        />
                        <Select
                          value={config.frequencyUnit}
                          onValueChange={(value) => updateBackgroundTask(taskName, 'frequencyUnit', value)}
                          disabled={!config.enabled}
                        >
                          <SelectTrigger className="w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="minutes">Minutes</SelectItem>
                            <SelectItem value="hours">Hours</SelectItem>
                            <SelectItem value="days">Days</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Priority</Label>
                      <Select
                        value={config.priority}
                        onValueChange={(value) => updateBackgroundTask(taskName, 'priority', value)}
                        disabled={!config.enabled}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`${taskName}-claude`}>Claude AI Usage</Label>
                      <div className="flex items-center gap-2">
                        <Switch
                          id={`${taskName}-claude`}
                          checked={config.useClaude}
                          onCheckedChange={(checked) => updateBackgroundTask(taskName, 'useClaude', checked)}
                          disabled={!config.enabled}
                        />
                        <span className="text-sm text-gray-600">
                          {config.useClaude ? 'AI analysis enabled' : 'Basic processing only'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`${taskName}-symbols`}>Stock Symbols</Label>
                      <Input
                        id={`${taskName}-symbols`}
                        placeholder="Enter symbols (comma-separated)"
                        defaultValue={config.stockSymbols.join(', ')}
                        onChange={(e) => updateBackgroundTask(taskName, 'stockSymbols', e.target.value.split(',').map(s => s.trim()).filter(s => s))}
                        disabled={!config.enabled}
                      />
                    </div>
                  </div>

                  <div className="text-sm text-gray-600">
                    <Clock className="inline w-3 h-3 mr-1" />
                    Runs {getFrequencyDisplay(config.frequency, config.frequencyUnit)} when enabled
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* AI Agents Tab */}
        <TabsContent value="ai-agents" className="space-y-6">
          <div className="grid gap-4">
            <Alert>
              <AlertDescription>
                Configure AI agents that perform specialized analysis and decision-making tasks.
                Control their tools, response frequency, and analysis scope.
              </AlertDescription>
            </Alert>

            {Object.entries(aiAgents).map(([agentName, config]) => (
              <Card key={agentName}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        {agentName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </CardTitle>
                      <CardDescription>
                        AI agent with specialized capabilities
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getScopeColor(config.scope)}>
                        {config.scope}
                      </Badge>
                      <Switch
                        checked={config.enabled}
                        onCheckedChange={(checked) => updateAIAgent(agentName, 'enabled', checked)}
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
                          onCheckedChange={(checked) => updateAIAgent(agentName, 'useClaude', checked)}
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
                        onValueChange={(value) => updateAIAgent(agentName, 'scope', value)}
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
                          onChange={(e) => updateAIAgent(agentName, 'responseFrequency', parseInt(e.target.value))}
                          className="w-24"
                          disabled={!config.enabled}
                        />
                        <Select
                          value={config.responseFrequencyUnit}
                          onValueChange={(value) => updateAIAgent(agentName, 'responseFrequencyUnit', value)}
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
                        onChange={(e) => updateAIAgent(agentName, 'maxTokensPerRequest', parseInt(e.target.value))}
                        disabled={!config.enabled}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Available Tools</Label>
                    <div className="flex flex-wrap gap-1">
                      {config.tools.map(tool => (
                        <Badge key={tool} variant="outline" className="text-xs">
                          {tool.replace('_', ' ')}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="text-sm text-gray-600">
                    <Brain className="inline w-3 h-3 mr-1" />
                    Responds every {getFrequencyDisplay(config.responseFrequency, config.responseFrequencyUnit)}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Global Settings Tab */}
        <TabsContent value="global-settings" className="space-y-6">
          <div className="grid gap-6">
            <Alert>
              <AlertDescription>
                System-wide configuration that affects all components.
                Set global limits, defaults, and system behavior.
              </AlertDescription>
            </Alert>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  Claude AI Settings
                </CardTitle>
                <CardDescription>
                  Global Claude AI configuration and limits
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label htmlFor="claude-enabled">Enable Claude AI</Label>
                    <p className="text-sm text-gray-600">
                      Master switch for all Claude AI usage
                    </p>
                  </div>
                  <Switch
                    id="claude-enabled"
                    checked={globalSettings.claudeUsage.enabled}
                    onCheckedChange={(checked) => updateGlobalSetting('claudeUsage', 'enabled', checked)}
                  />
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="token-limit">Daily Token Limit</Label>
                    <Input
                      id="token-limit"
                      type="number"
                      value={globalSettings.claudeUsage.dailyTokenLimit}
                      onChange={(e) => updateGlobalSetting('claudeUsage', 'dailyTokenLimit', parseInt(e.target.value))}
                      disabled={!globalSettings.claudeUsage.enabled}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="cost-threshold">Cost Alert Threshold ($)</Label>
                    <Input
                      id="cost-threshold"
                      type="number"
                      step="0.01"
                      value={globalSettings.claudeUsage.costThreshold}
                      onChange={(e) => updateGlobalSetting('claudeUsage', 'costThreshold', parseFloat(e.target.value))}
                      disabled={!globalSettings.claudeUsage.enabled}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Switch
                    id="cost-alerts"
                    checked={globalSettings.claudeUsage.costAlerts}
                    onCheckedChange={(checked) => updateGlobalSetting('claudeUsage', 'costAlerts', checked)}
                    disabled={!globalSettings.claudeUsage.enabled}
                  />
                  <Label htmlFor="cost-alerts">Enable cost alerts</Label>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Scheduler Defaults
                </CardTitle>
                <CardDescription>
                  Default settings for background schedulers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-2">
                  <Switch
                    id="market-hours"
                    checked={globalSettings.schedulerDefaults.marketHoursOnly}
                    onCheckedChange={(checked) => updateGlobalSetting('schedulerDefaults', 'marketHoursOnly', checked)}
                  />
                  <Label htmlFor="market-hours">Run during market hours only</Label>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="default-frequency">Default Frequency</Label>
                    <div className="flex gap-2">
                      <Input
                        id="default-frequency"
                        type="number"
                        min="1"
                        value={globalSettings.schedulerDefaults.defaultFrequency}
                        onChange={(e) => updateGlobalSetting('schedulerDefaults', 'defaultFrequency', parseInt(e.target.value))}
                        className="w-20"
                      />
                      <Select
                        value={globalSettings.schedulerDefaults.defaultFrequencyUnit}
                        onValueChange={(value) => updateGlobalSetting('schedulerDefaults', 'defaultFrequencyUnit', value)}
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
                    <Label htmlFor="retry-attempts">Retry Attempts</Label>
                    <Input
                      id="retry-attempts"
                      type="number"
                      min="1"
                      max="10"
                      value={globalSettings.schedulerDefaults.retryAttempts}
                      onChange={(e) => updateGlobalSetting('schedulerDefaults', 'retryAttempts', parseInt(e.target.value))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="retry-delay">Retry Delay (minutes)</Label>
                    <Input
                      id="retry-delay"
                      type="number"
                      min="1"
                      max="60"
                      value={globalSettings.schedulerDefaults.retryDelayMinutes}
                      onChange={(e) => updateGlobalSetting('schedulerDefaults', 'retryDelayMinutes', parseInt(e.target.value))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ConfigurationFeature