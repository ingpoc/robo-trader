import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dashboardAPI } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'

export function usePortfolio() {
  const queryClient = useQueryClient()
  const addToast = useDashboardStore((state) => state.addToast)

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardAPI.getDashboardData,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  const portfolioScan = useMutation({
    mutationFn: dashboardAPI.portfolioScan,
    onSuccess: () => {
      addToast({
        title: 'Portfolio Scan Started',
        description: 'Analyzing your portfolio...',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error) => {
      addToast({
        title: 'Scan Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  const marketScreening = useMutation({
    mutationFn: dashboardAPI.marketScreening,
    onSuccess: () => {
      addToast({
        title: 'Market Screening Started',
        description: 'Scanning market opportunities...',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error) => {
      addToast({
        title: 'Screening Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'error',
      })
    },
  })

  return {
    portfolio: data?.portfolio,
    analytics: data?.analytics,
    intents: data?.intents || [],
    isLoading,
    error,
    portfolioScan: portfolioScan.mutate,
    marketScreening: marketScreening.mutate,
    isScanning: portfolioScan.isPending || marketScreening.isPending,
  }
}
