import { useQuery } from '@tanstack/react-query'
import { dashboardAPI } from '@/api/endpoints'

export function usePortfolio() {
  const { data, isLoading, error, refetch } = useQuery(
    ['dashboard'],
    dashboardAPI.getDashboardData,
    {
      staleTime: 30000,
      cacheTime: 5 * 60 * 1000,
    }
  )

  return {
    portfolio: data?.portfolio,
    analytics: data?.analytics,
    aiStatus: data?.ai_status,
    alerts: data?.alerts || [],
    intents: data?.intents || [],
    isLoading,
    error,
    refetch,
  }
}
