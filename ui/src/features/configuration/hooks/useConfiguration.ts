import { useState, useEffect } from 'react'
import { useToast } from '@/hooks/use-toast'
import { configurationAPI } from '@/api/endpoints'
import type { BackgroundTaskConfig, AIAgentConfig, GlobalConfig } from '@/types/api'
import type { PromptConfig } from '../types'
import { logger } from '../utils'

export const useConfiguration = () => {
  const { toast } = useToast()

  // Configuration state
  const [backgroundTasks, setBackgroundTasks] = useState<Record<string, BackgroundTaskConfig>>({})
  const [aiAgents, setAIAgents] = useState<Record<string, AIAgentConfig>>({})
  const [globalSettings, setGlobalSettings] = useState<GlobalConfig | null>(null)
  const [prompts, setPrompts] = useState<Record<string, PromptConfig>>({})

  // UI state
  const [visiblePrompts, setVisiblePrompts] = useState<Set<string>>(new Set())
  const [editingPrompts, setEditingPrompts] = useState<Set<string>>(new Set())
  const [executingTasks, setExecutingTasks] = useState<Set<string>>(new Set())
  const [executingAgents, setExecutingAgents] = useState<Set<string>>(new Set())

  // Loading states
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load configuration on mount
  useEffect(() => {
    loadConfiguration()
  }, [])

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

  const saveConfiguration = async () => {
    try {
      setIsSaving(true)

      const savePromises = [
        ...Object.entries(backgroundTasks).map(([taskName, config]) =>
          configurationAPI.updateBackgroundTask(taskName, config)
        ),
        ...Object.entries(aiAgents).map(([agentName, config]) =>
          configurationAPI.updateAIAgent(agentName, config)
        )
      ]

      if (globalSettings) {
        savePromises.push(configurationAPI.updateGlobalSettings(globalSettings))
      }

      await Promise.all(savePromises)

      toast({
        title: "Configuration saved",
        description: "All changes have been saved successfully",
      })

      await loadConfiguration()

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save configuration'
      toast({
        title: "Failed to save configuration",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setIsSaving(false)
    }
  }

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

  const loadPrompt = async (taskName: string) => {
    try {
      const promptData = await configurationAPI.getPrompt(taskName)
      setPrompts(prev => ({
        ...prev,
        [taskName]: promptData
      }))
    } catch (err) {
      console.error(`Failed to load prompt for ${taskName}:`, err)
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

  const togglePrompt = (taskName: string) => {
    setVisiblePrompts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskName)) {
        newSet.delete(taskName)
        setEditingPrompts(editPrev => {
          const newEditSet = new Set(editPrev)
          newEditSet.delete(taskName)
          return newEditSet
        })
      } else {
        newSet.add(taskName)
        loadPrompt(taskName)
      }
      return newSet
    })
  }

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

  const updatePrompt = (taskName: string, field: 'content' | 'description', value: string) => {
    setPrompts(prev => ({
      ...prev,
      [taskName]: {
        ...prev[taskName],
        [field]: value
      }
    }))
  }

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

      await loadPrompt(taskName)

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

  return {
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

    // Setters (for direct manipulation when needed)
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
  }
}
