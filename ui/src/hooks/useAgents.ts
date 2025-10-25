import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { AgentConfig } from '@/types/api'

export function useAgents() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data: agentsData, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsAPI.getStatus,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  const updateConfig = useMutation({
    mutationFn: ({ agentName, config }: { agentName: string; config: AgentConfig }) =>
      agentsAPI.updateConfig(agentName, config),
    onSuccess: (_, { agentName }) => {
      addToast({
        title: 'Configuration Updated',
        description: `${agentName} settings saved`,
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
    onError: (error) => {
      addToast({
        title: 'Update Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  return {
    agents: agentsData?.agents || {},
    isLoading,
    updateConfig: updateConfig.mutate,
    isUpdating: updateConfig.isPending,
  }
}
