import { useQuery, useMutation } from '@tanstack/react-query'
import { analyticsAPI } from '@/api/endpoints'
import type { PerformanceData } from '@/types/api'

export function useAnalytics(period: string = '30d') {
  return useQuery<PerformanceData>({
    queryKey: ['analytics', 'performance', period],
    queryFn: () => analyticsAPI.getPerformance(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  })
}

export function usePortfolioAnalytics() {
  return useQuery<PerformanceData>({
    queryKey: ['analytics', 'portfolio-deep'],
    queryFn: analyticsAPI.getPortfolioDeep,
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  })
}

export function useStrategyOptimization() {
  const optimizeStrategy = useMutation({
    mutationFn: analyticsAPI.optimizeStrategy,
    onSuccess: (data) => {
      // Handle optimization result
      console.log('Strategy optimization completed:', data)
    },
  })

  return {
    optimizeStrategy: optimizeStrategy.mutate,
    isOptimizing: optimizeStrategy.isPending,
  }
}