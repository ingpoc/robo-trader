import { useEffect, useState } from 'react'

import { configurationAPI } from '@/api/endpoints'
import { useToast } from '@/hooks/use-toast'
import type { AIAgentConfig, GlobalConfig } from '@/types/api'

export const useConfiguration = () => {
  const { toast } = useToast()

  const [aiAgents, setAIAgents] = useState<Record<string, AIAgentConfig>>({})
  const [globalSettings, setGlobalSettings] = useState<GlobalConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void loadConfiguration()
  }, [])

  const loadConfiguration = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [aiAgentsData, globalSettingsData] = await Promise.all([
        configurationAPI.getAIAgents(),
        configurationAPI.getGlobalSettings(),
      ])

      setAIAgents(aiAgentsData.ai_agents)
      setGlobalSettings(globalSettingsData.global_settings)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load configuration'
      setError(errorMessage)
      toast({
        title: 'Failed to load configuration',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const saveConfiguration = async () => {
    try {
      setIsSaving(true)

      const savePromises: Promise<unknown>[] = [
        ...Object.entries(aiAgents).map(([agentName, config]) =>
          configurationAPI.updateAIAgent(agentName, config)
        ),
      ]

      if (globalSettings) {
        savePromises.push(configurationAPI.updateGlobalSettings(globalSettings))
      }

      await Promise.all(savePromises)

      toast({
        title: 'Configuration saved',
        description: 'Agent runtime and global settings were updated successfully.',
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save configuration'
      setError(errorMessage)
      toast({
        title: 'Failed to save configuration',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const updateAIAgent = (agentName: string, field: keyof AIAgentConfig, value: unknown) => {
    setAIAgents(prev => ({
      ...prev,
      [agentName]: {
        ...prev[agentName],
        [field]: value,
      },
    }))
  }

  const updateGlobalSetting = (section: keyof GlobalConfig, field: string, value: unknown) => {
    if (!globalSettings) {
      return
    }

    setGlobalSettings(prev => {
      if (!prev) {
        return prev
      }

      const sectionValue = prev[section]
      if (sectionValue && typeof sectionValue === 'object' && !Array.isArray(sectionValue)) {
        return {
          ...prev,
          [section]: {
            ...sectionValue,
            [field]: value,
          },
        }
      }

      return {
        ...prev,
        [section]: value,
      }
    })
  }

  return {
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
  }
}
