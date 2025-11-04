import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Settings, Cpu, Brain, Globe, Save, RefreshCw, AlertTriangle } from 'lucide-react'
import { BackgroundTasksConfig } from './components/BackgroundTasksConfig'
import { AIAgentConfigComponent } from './components/AIAgentConfig'
import { GlobalSettingsPanel } from './components/GlobalSettingsPanel'
import { useConfiguration } from './hooks/useConfiguration'

/**
 * Configuration Feature - Main orchestrator component
 *
 * Manages system-wide configuration including:
 * - Background tasks (schedulers)
 * - AI agents
 * - Global settings
 *
 * Refactored from 1,038-line monolithic component to focused sub-components.
 */
const ConfigurationFeature: React.FC = () => {
  const [activeTab, setActiveTab] = useState('background-tasks')

  // Use custom hook for all data management
  const {
    // State
    backgroundTasks,
    aiAgents,
    globalSettings,
    prompts,
    visiblePrompts,
    editingPrompts,
    executingTasks,
    executingAgents,
    isLoading,
    isSaving,
    error,

    // Setters
    setGlobalSettings,

    // Operations
    loadConfiguration,
    saveConfiguration,
    updateBackgroundTask,
    updateAIAgent,
    updateGlobalSetting,
    togglePrompt,
    togglePromptEditing,
    updatePrompt,
    savePrompt,
    executeScheduler,
    executeAgent,
  } = useConfiguration()

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Settings className="w-8 h-8" />
            Configuration
          </h1>
          <p className="text-gray-600 mt-1">
            Manage background tasks, AI agents, and system settings
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={loadConfiguration}
            disabled={isLoading || isSaving}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={saveConfiguration}
            disabled={isLoading || isSaving}
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save All Changes'}
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Configuration Tabs */}
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
        <TabsContent value="background-tasks">
          <BackgroundTasksConfig
            backgroundTasks={backgroundTasks}
            prompts={prompts}
            visiblePrompts={visiblePrompts}
            editingPrompts={editingPrompts}
            executingTasks={executingTasks}
            isLoading={isLoading}
            isSaving={isSaving}
            onUpdateTask={updateBackgroundTask}
            onExecuteTask={executeScheduler}
            onTogglePrompt={togglePrompt}
            onTogglePromptEditing={togglePromptEditing}
            onSavePrompt={savePrompt}
            onUpdatePrompt={updatePrompt}
          />
        </TabsContent>

        {/* AI Agents Tab */}
        <TabsContent value="ai-agents">
          <AIAgentConfigComponent
            aiAgents={aiAgents}
            executingAgents={executingAgents}
            isLoading={isLoading}
            onUpdateAgent={updateAIAgent}
            onExecuteAgent={executeAgent}
          />
        </TabsContent>

        {/* Global Settings Tab */}
        <TabsContent value="global-settings">
          <GlobalSettingsPanel
            globalSettings={globalSettings}
            isLoading={isLoading}
            onUpdateSetting={updateGlobalSetting}
            onSetGlobalSettings={setGlobalSettings}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ConfigurationFeature
