import React, { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Settings, Brain, Globe, Save, RefreshCw, AlertTriangle } from 'lucide-react'
import { AIAgentConfigComponent } from './components/AIAgentConfig'
import { GlobalSettingsPanel } from './components/GlobalSettingsPanel'
import { useConfiguration } from './hooks/useConfiguration'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'

/**
 * Configuration Feature - Main orchestrator component
 *
 * Manages system-wide configuration including:
 * - AI agent runtime defaults
 * - Global settings
 *
 * Scheduler management is intentionally excluded from the product surface.
 */
const ConfigurationFeature: React.FC = () => {
  const [activeTab, setActiveTab] = useState('ai-agents')

  const {
    aiAgents,
    globalSettings,
    isLoading,
    isSaving,
    error,
    setGlobalSettings,
    loadConfiguration,
    saveConfiguration,
    updateAIAgent,
    updateGlobalSetting,
  } = useConfiguration()

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-6">
        <Breadcrumb />

        <PageHeader
          title="Configuration"
          description="Configure agent runtime defaults, quote-stream preferences, and system-wide limits for the paper-trading operator."
          icon={<Settings className="h-5 w-5" />}
          actions={
            <>
              <Button
                variant="tertiary"
                onClick={loadConfiguration}
                disabled={isLoading || isSaving}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                onClick={saveConfiguration}
                disabled={isLoading || isSaving}
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? 'Saving...' : 'Save All Changes'}
              </Button>
            </>
          }
        />
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
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="ai-agents" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            Agent Runtime
          </TabsTrigger>
          <TabsTrigger value="global-settings" className="flex items-center gap-2">
            <Globe className="w-4 h-4" />
            Global Settings
          </TabsTrigger>
        </TabsList>

        {/* AI Agents Tab */}
        <TabsContent value="ai-agents">
          <AIAgentConfigComponent
            aiAgents={aiAgents}
            isLoading={isLoading}
            onUpdateAgent={updateAIAgent}
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
