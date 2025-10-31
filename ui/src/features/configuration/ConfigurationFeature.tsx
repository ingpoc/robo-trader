import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Settings, Cpu, Brain, Globe, Clock, ToggleLeft, Zap, Save, RefreshCw, AlertTriangle, Eye, Play, Loader2 } from 'lucide-react'
import { configurationAPI } from '@/api/endpoints'
import { useToast } from '@/hooks/use-toast'
import type { BackgroundTaskConfig, AIAgentConfig, GlobalConfig } from '@/types/api'

// Simple logger for client-side
const logger = {
  info: (message: string) => console.log(`[Configuration] ${message}`),
  error: (message: string) => console.error(`[Configuration] ${message}`)
}


const ConfigurationFeature: React.FC = () => {
  const { toast } = useToast()

  // Loading and error states
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  // Configuration state
  const [backgroundTasks, setBackgroundTasks] = useState<Record<string, BackgroundTaskConfig>>({})
  const [aiAgents, setAIAgents] = useState<Record<string, AIAgentConfig>>({})
  const [globalSettings, setGlobalSettings] = useState<GlobalConfig | null>(null)

  const [activeTab, setActiveTab] = useState('background-tasks')
  const [visiblePrompts, setVisiblePrompts] = useState<Set<string>>(new Set())
  const [prompts, setPrompts] = useState<Record<string, PromptConfig>>({})
  const [editingPrompts, setEditingPrompts] = useState<Set<string>>(new Set())
  const [executingTasks, setExecutingTasks] = useState<Set<string>>(new Set())
  const [executingAgents, setExecutingAgents] = useState<Set<string>>(new Set())

  // Get prompt for scheduler type from database
  const getSchedulerPrompt = (taskName: string) => {
    return prompts[taskName]?.content || `No prompt available for ${taskName}`
  }

  // Toggle prompt visibility
  const togglePrompt = (taskName: string) => {
    setVisiblePrompts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskName)) {
        newSet.delete(taskName)
        // Also stop editing when hiding
        setEditingPrompts(editPrev => {
          const newEditSet = new Set(editPrev)
          newEditSet.delete(taskName)
          return newEditSet
        })
      } else {
        newSet.add(taskName)
        // Load prompt when showing
        loadPrompt(taskName)
      }
      return newSet
    })
  }

  // Load individual prompt
  const loadPrompt = async (taskName: string) => {
    try {
      const promptData = await configurationAPI.getPrompt(taskName)
      setPrompts(prev => ({
        ...prev,
        [taskName]: promptData
      }))
    } catch (err) {
      console.error(`Failed to load prompt for ${taskName}:`, err)
      // Set empty prompt if loading fails
      setPrompts(prev => ({
        ...prev,
        [taskName]: {
          prompt_name: taskName,
          content: '',
          description: `Prompt for ${taskName.replace('_', ' ')}`,
          created_at: '',
          updated_at: ''
        }
      }))
    }
  }

  // Toggle prompt editing mode
  const togglePromptEditing = (taskName: string) => {
    setEditingPrompts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskName)) {
        newSet.delete(taskName)
      } else {
        newSet.add(taskName)
      }
      return newSet
    })
  }

  // Save prompt
  const savePrompt = async (taskName: string) => {
    try {
      const prompt = prompts[taskName]
      if (!prompt) return

      await configurationAPI.updatePrompt(taskName, {
        content: prompt.content,
        description: prompt.description
      })

      toast({
        title: "Success",
        description: `Prompt for ${taskName.replace('_', ' ')} saved successfully`,
      })

      // Reload to get updated timestamp
      await loadPrompt(taskName)

      // Stop editing mode
      setEditingPrompts(prev => {
        const newSet = new Set(prev)
        newSet.delete(taskName)
        return newSet
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save prompt'
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    }
  }

  // Update prompt content
  const updatePrompt = (taskName: string, field: 'content' | 'description', value: string) => {
    setPrompts(prev => ({
      ...prev,
      [taskName]: {
        ...prev[taskName],
        [field]: value
    }
    }))
  }

  // Execute scheduler manually
  const executeScheduler = async (taskName: string) => {
    try {
      setExecutingTasks(prev => new Set(prev).add(taskName))

      const response = await configurationAPI.executeScheduler(taskName)

      toast({
        title: "Scheduler Execution Started",
        description: `Manual execution of ${taskName.replace('_', ' ')} has been initiated. Check System Health for status updates.`,
      })

      logger.info(`Manual execution started for ${taskName}: ${response.task_id}`)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute scheduler'
      toast({
        title: "Execution Failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setExecutingTasks(prev => {
        const newSet = new Set(prev)
        newSet.delete(taskName)
        return newSet
      })
    }
  }

  // Execute AI agent manually
  const executeAgent = async (agentName: string) => {
    try {
      setExecutingAgents(prev => new Set(prev).add(agentName))

      const response = await configurationAPI.executeAgent(agentName)

      toast({
        title: "AI Agent Execution Started",
        description: `Manual execution of ${agentName.replace('_', ' ')} has been initiated. Check AI Transparency tab for Claude's analysis and activity.`,
      })

      logger.info(`Manual execution started for AI agent ${agentName}`)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute AI agent'
      toast({
        title: "Execution Failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setExecutingAgents(prev => {
        const newSet = new Set(prev)
        newSet.delete(agentName)
        return newSet
      })
    }
  }

  // Load configuration data from API
  const loadConfiguration = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [backgroundTasksData, aiAgentsData, globalSettingsData] = await Promise.all([
        configurationAPI.getBackgroundTasks(),
        configurationAPI.getAIAgents(),
        configurationAPI.getGlobalSettings()
      ])

      setBackgroundTasks(backgroundTasksData.background_tasks)
      setAIAgents(aiAgentsData.ai_agents)
      setGlobalSettings(globalSettingsData.global_settings)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load configuration'
      setError(errorMessage)
      toast({
        title: "Failed to load configuration",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Load configuration on mount
  useEffect(() => {
    loadConfiguration()
  }, [])

  // Save all configuration changes
  const saveConfiguration = async () => {
    try {
      setIsSaving(true)
      setError(null)

      // Save background tasks
      const backgroundPromises = Object.entries(backgroundTasks).map(([taskName, config]) =>
        configurationAPI.updateBackgroundTask(taskName, config)
      )

      // Save AI agents
      const aiAgentPromises = Object.entries(aiAgents).map(([agentName, config]) =>
        configurationAPI.updateAIAgent(agentName, config)
      )

      // Save global settings
      const globalSettingsPromise = globalSettings
        ? configurationAPI.updateGlobalSettings(globalSettings)
        : Promise.resolve()

      await Promise.all([
        ...backgroundPromises,
        ...aiAgentPromises,
        globalSettingsPromise
      ])

      toast({
        title: "Configuration saved",
        description: "All configuration changes have been saved successfully.",
      })

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save configuration'
      setError(errorMessage)
      toast({
        title: "Failed to save configuration",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setIsSaving(false)
    }
  }

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
    setGlobalSettings(prev => {
      if (!prev) return prev
      return {
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
      }
    })
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configuration</h1>
          <p className="text-gray-600 mt-1">Manage background tasks, AI agents, and system settings</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="gap-2"
            onClick={loadConfiguration}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            disabled={true}
          >
            <Settings className="w-4 h-4" />
            Reset to Defaults
          </Button>
          <Button
            className="gap-2"
            onClick={saveConfiguration}
            disabled={isSaving || isLoading || Object.keys(backgroundTasks).length === 0}
          >
            <Save className={`w-4 h-4 ${isSaving ? 'animate-spin' : ''}`} />
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      )}

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

            {isLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
                <p className="text-gray-600">Loading configuration...</p>
              </div>
            ) : Object.keys(backgroundTasks).length === 0 ? (
              <div className="text-center py-8">
                <Cpu className="w-8 h-8 mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600">No background tasks configured</p>
              </div>
            ) : (
              Object.entries(backgroundTasks).map(([taskName, config]) => (
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

                  </div>

                  <div className="text-sm text-gray-600">
                    <Clock className="inline w-3 h-3 mr-1" />
                    Runs {getFrequencyDisplay(config.frequency, config.frequencyUnit)} when enabled
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-4 border-t space-y-2">
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => executeScheduler(taskName)}
                        disabled={executingTasks.has(taskName) || !config.enabled}
                        className="flex-1"
                      >
                        {executingTasks.has(taskName) ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Executing...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2" />
                            Run Now
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => togglePrompt(taskName)}
                        className="flex-1"
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        {visiblePrompts.has(taskName) ? 'Hide Prompt' : 'View/Edit Prompt'}
                      </Button>
                    </div>
                  </div>

                  {/* Prompt Display/Edit */}
                  {visiblePrompts.has(taskName) && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg border space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-sm">Perplexity API Prompt:</h4>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => togglePromptEditing(taskName)}
                        >
                          {editingPrompts.has(taskName) ? 'Cancel Edit' : 'Edit Prompt'}
                        </Button>
                      </div>

                      {editingPrompts.has(taskName) ? (
                        <>
                          {/* Description Field */}
                          <div className="space-y-2">
                            <Label htmlFor={`${taskName}-description`} className="text-xs font-medium">
                              Description
                            </Label>
                            <Input
                              id={`${taskName}-description`}
                              value={prompts[taskName]?.description || ''}
                              onChange={(e) => updatePrompt(taskName, 'description', e.target.value)}
                              placeholder="Brief description of this prompt's purpose"
                              className="text-sm"
                            />
                          </div>

                          {/* Content Field */}
                          <div className="space-y-2">
                            <Label htmlFor={`${taskName}-content`} className="text-xs font-medium">
                              Prompt Content
                            </Label>
                            <Textarea
                              id={`${taskName}-content`}
                              value={prompts[taskName]?.content || ''}
                              onChange={(e) => updatePrompt(taskName, 'content', e.target.value)}
                              placeholder="Enter the AI prompt content..."
                              className="min-h-48 font-mono text-xs"
                            />
                          </div>

                          {/* Save/Cancel Buttons */}
                          <div className="flex gap-2 pt-2">
                            <Button
                              size="sm"
                              onClick={() => savePrompt(taskName)}
                              disabled={isSaving}
                              className="flex-1"
                            >
                              <Save className="w-4 h-4 mr-2" />
                              {isSaving ? 'Saving...' : 'Save Prompt'}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => togglePromptEditing(taskName)}
                              className="flex-1"
                            >
                              Cancel
                            </Button>
                          </div>
                        </>
                      ) : (
                        <div className="space-y-3">
                          <div className="text-xs text-gray-600">
                            <strong>Description:</strong> {prompts[taskName]?.description || 'No description available'}
                          </div>
                          <div className="text-xs text-gray-600">
                            <strong>Last Updated:</strong> {prompts[taskName]?.updated_at ? new Date(prompts[taskName].updated_at).toLocaleString() : 'Never'}
                          </div>
                          <div>
                            <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-white p-3 rounded border max-h-48 overflow-y-auto">
                              {prompts[taskName]?.content || 'Loading prompt...'}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
              ))
            )}
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

            {isLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
                <p className="text-gray-600">Loading AI agents configuration...</p>
              </div>
            ) : Object.keys(aiAgents).length === 0 ? (
              <div className="text-center py-8">
                <Brain className="w-8 h-8 mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600">No AI agents configured</p>
              </div>
            ) : (
              Object.entries(aiAgents).map(([agentName, config]) => (
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

                  {/* Action Button */}
                  <div className="pt-4 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => executeAgent(agentName)}
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
              ))
            )}
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

            {isLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
                <p className="text-gray-600">Loading global settings...</p>
              </div>
            ) : !globalSettings ? (
              <div className="text-center py-8">
                <Globe className="w-8 h-8 mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600">Global settings not loaded</p>
              </div>
            ) : (
              <>
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
                        checked={globalSettings?.claudeUsage?.enabled ?? true}
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
                          value={globalSettings?.claudeUsage?.dailyTokenLimit ?? 50000}
                      onChange={(e) => updateGlobalSetting('claudeUsage', 'dailyTokenLimit', parseInt(e.target.value))}
                          disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="cost-threshold">Cost Alert Threshold ($)</Label>
                    <Input
                      id="cost-threshold"
                      type="number"
                      step="0.01"
                          value={globalSettings?.claudeUsage?.costThreshold ?? 10.00}
                      onChange={(e) => updateGlobalSetting('claudeUsage', 'costThreshold', parseFloat(e.target.value))}
                          disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Switch
                    id="cost-alerts"
                        checked={globalSettings?.claudeUsage?.costAlerts ?? true}
                    onCheckedChange={(checked) => updateGlobalSetting('claudeUsage', 'costAlerts', checked)}
                        disabled={!(globalSettings?.claudeUsage?.enabled ?? true)}
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
                        checked={globalSettings?.schedulerDefaults?.marketHoursOnly ?? true}
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
                            value={globalSettings?.schedulerDefaults?.defaultFrequency ?? 30}
                        onChange={(e) => updateGlobalSetting('schedulerDefaults', 'defaultFrequency', parseInt(e.target.value))}
                        className="w-20"
                      />
                      <Select
                            value={globalSettings?.schedulerDefaults?.defaultFrequencyUnit ?? 'minutes'}
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
                          value={globalSettings?.schedulerDefaults?.retryAttempts ?? 3}
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
                          value={globalSettings?.schedulerDefaults?.retryDelayMinutes ?? 5}
                      onChange={(e) => updateGlobalSetting('schedulerDefaults', 'retryDelayMinutes', parseInt(e.target.value))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  System Limits
                </CardTitle>
                <CardDescription>
                  Configure core system parameters and limits
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <Label htmlFor="max-turns">Max Conversation Turns</Label>
                    <Input
                      id="max-turns"
                      type="number"
                      min="1"
                      max="50"
                      value={globalSettings.maxTurns ?? 5}
                      onChange={e => setGlobalSettings(prev => ({...prev, maxTurns: parseInt(e.target.value)}))}
                    />
                    <p className="text-xs text-gray-500">Maximum number of conversation turns allowed per session</p>
                  </div>
                  <div>
                    <Label htmlFor="risk-tolerance">Risk Tolerance (1-10)</Label>
                    <Input
                      id="risk-tolerance"
                      type="number"
                      min="1"
                      max="10"
                      value={globalSettings.riskTolerance ?? 5}
                      onChange={e => setGlobalSettings(prev => ({...prev, riskTolerance: parseInt(e.target.value)}))}
                    />
                    <p className="text-xs text-gray-500">Higher = more aggressive trading strategies</p>
                  </div>
                  <div>
                    <Label htmlFor="daily-api-limit">Daily API Call Limit</Label>
                    <Input
                      id="daily-api-limit"
                      type="number"
                      min="1"
                      value={globalSettings.dailyApiLimit ?? 25}
                      onChange={e => setGlobalSettings(prev => ({...prev, dailyApiLimit: parseInt(e.target.value)}))}
                    />
                    <p className="text-xs text-gray-500">Maximum number of API calls allowed daily</p>
                  </div>
                </div>
              </CardContent>
            </Card>
              </>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ConfigurationFeature