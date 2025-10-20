import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { alertsAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { Alert } from '@/types/api'

export function useAlerts() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: alertsAPI.getActive,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  const handleAction = useMutation({
    mutationFn: ({ alertId, action }: { alertId: string; action: string }) =>
      alertsAPI.handleAction(alertId, { action }),
    onSuccess: (_, { alertId, action }) => {
      addToast({
        title: 'Alert Action Completed',
        description: `Alert ${alertId} marked as ${action}`,
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
    onError: (error) => {
      addToast({
        title: 'Alert Action Failed',
        description: error instanceof Error ? error.message : 'Failed to handle alert',
        variant: 'error',
      })
    },
  })

  return {
    alerts: alertsData?.alerts || [],
    isLoading,
    handleAction: handleAction.mutate,
    isHandlingAction: handleAction.isPending,
  }
}