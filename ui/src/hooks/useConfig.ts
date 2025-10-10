import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { configAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'

export function useConfig() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data: config, isLoading, error } = useQuery({
    queryKey: ['config'],
    queryFn: configAPI.get,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  })

  const updateConfig = useMutation({
    mutationFn: configAPI.update,
    onSuccess: () => {
      addToast({
        title: 'Configuration Updated',
        description: 'Settings have been saved successfully',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
    onError: (error) => {
      addToast({
        title: 'Configuration Failed',
        description: error instanceof Error ? error.message : 'Failed to save settings',
        variant: 'error',
      })
    },
  })

  return {
    config,
    isLoading,
    error,
    updateConfig: updateConfig.mutate,
    isUpdating: updateConfig.isPending,
  }
}