import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiAPI, recommendationsAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'

export function useRecommendations() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data, isLoading } = useQuery({
    queryKey: ['recommendations'],
    queryFn: aiAPI.getRecommendations,
    refetchInterval: 15000,
  })

  const approve = useMutation({
    mutationFn: recommendationsAPI.approve,
    onSuccess: (_, id) => {
      addToast({
        title: 'Recommendation Approved',
        description: 'Trade will be executed',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error) => {
      addToast({
        title: 'Approval Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  const reject = useMutation({
    mutationFn: recommendationsAPI.reject,
    onSuccess: () => {
      addToast({
        title: 'Recommendation Rejected',
        variant: 'default',
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
    onError: (error) => {
      addToast({
        title: 'Rejection Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  const discuss = useMutation({
    mutationFn: recommendationsAPI.discuss,
    onSuccess: () => {
      addToast({
        title: 'Marked for Discussion',
        variant: 'default',
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
    onError: (error) => {
      addToast({
        title: 'Action Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  return {
    recommendations: data?.recommendations || [],
    isLoading,
    approve: approve.mutate,
    reject: reject.mutate,
    discuss: discuss.mutate,
    isPending: approve.isPending || reject.isPending || discuss.isPending,
  }
}
