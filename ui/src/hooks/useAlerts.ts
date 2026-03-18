import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { alertsAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { Alert } from '@/types/api'

export function useAlerts() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadAlerts = async () => {
      setIsLoading(true)
      try {
        const response = await alertsAPI.getActive()
        if (!cancelled) {
          setAlerts(response.alerts || [])
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          const nextError = err instanceof Error ? err : new Error('Failed to load alerts')
          setAlerts([])
          setError(nextError)
          console.warn('Failed to load alerts:', nextError)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadAlerts()

    return () => {
      cancelled = true
    }
  }, [])

  const handleAction = useMutation({
    mutationFn: ({ alertId, action }: { alertId: string; action: string }) =>
      alertsAPI.handleAction(alertId, action),
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
    alerts,
    isLoading,
    error,
    handleAction: handleAction.mutate,
    isHandlingAction: handleAction.isPending,
  }
}
