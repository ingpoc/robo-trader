import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { alertsAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { Alert } from '@/types/api'

export function useAlerts() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data: alertsData, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: alertsAPI.getActive,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
    retry: (failureCount, error) => {
      // Don't retry on 404s or auth errors
      if (error instanceof Error && (error.message.includes('404') || error.message.includes('401'))) {
        return false
      }
      return failureCount < 3
    },
    onError: (error) => {
      console.warn('Failed to load alerts:', error)
      // Don't show toast for alerts - they're not critical
    }
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
    error,
    handleAction: handleAction.mutate,
    isHandlingAction: handleAction.isPending,
  }
}