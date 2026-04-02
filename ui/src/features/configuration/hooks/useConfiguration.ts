import { useEffect, useState } from 'react'

import { configurationAPI, operatorAPI, runtimeAPI } from '@/api/endpoints'
import { useToast } from '@/hooks/use-toast'
import type { AIAgentConfig, AccountPolicy, ConfigurationStatus, GlobalConfig } from '@/types/api'
import type { PaperTradingOperatorSnapshot, RuntimeHealthResponse } from '@/features/paper-trading/types'

interface UseConfigurationOptions {
  accountId: string | null
}

export const useConfiguration = ({ accountId }: UseConfigurationOptions) => {
  const { toast } = useToast()

  const [aiAgents, setAIAgents] = useState<Record<string, AIAgentConfig>>({})
  const [globalSettings, setGlobalSettings] = useState<GlobalConfig | null>(null)
  const [configurationStatus, setConfigurationStatus] = useState<ConfigurationStatus | null>(null)
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealthResponse | null>(null)
  const [accountPolicy, setAccountPolicy] = useState<AccountPolicy | null>(null)
  const [operatorSnapshot, setOperatorSnapshot] = useState<PaperTradingOperatorSnapshot | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void loadConfiguration()
  }, [accountId])

  const loadConfiguration = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [aiAgentsData, globalSettingsData, configurationStatusData, runtimeHealthData, accountPolicyData, snapshotData] =
        await Promise.all([
          configurationAPI.getAIAgents(),
          configurationAPI.getGlobalSettings(),
          configurationAPI.getStatus(),
          runtimeAPI.getHealth(),
          accountId ? configurationAPI.getAccountPolicy(accountId) : Promise.resolve(null),
          accountId ? operatorAPI.getOperatorSnapshot(accountId) : Promise.resolve(null),
        ])

      setAIAgents(aiAgentsData.ai_agents)
      setGlobalSettings(globalSettingsData.global_settings)
      setConfigurationStatus(configurationStatusData.configuration_status)
      setRuntimeHealth(runtimeHealthData)
      setAccountPolicy(accountPolicyData?.policy ?? null)
      setOperatorSnapshot(snapshotData)
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

      if (accountId && accountPolicy) {
        savePromises.push(configurationAPI.updateAccountPolicy(accountId, accountPolicy))
      }

      await Promise.all(savePromises)
      await loadConfiguration()

      toast({
        title: 'Configuration saved',
        description: 'Runtime state was refreshed and operator policy changes were applied.',
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

  const updateGlobalSetting = (field: keyof GlobalConfig, value: unknown) => {
    setGlobalSettings(prev => ({
      ...(prev ?? {}),
      [field]: value,
    }))
  }

  const updateAccountPolicy = (field: keyof AccountPolicy, value: unknown) => {
    setAccountPolicy(prev => (prev ? { ...prev, [field]: value } : prev))
  }

  return {
    aiAgents,
    globalSettings,
    configurationStatus,
    runtimeHealth,
    accountPolicy,
    operatorSnapshot,
    isLoading,
    isSaving,
    error,
    setGlobalSettings,
    loadConfiguration,
    saveConfiguration,
    updateAIAgent,
    updateGlobalSetting,
    updateAccountPolicy,
  }
}
