import { useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiAPI, recommendationsAPI } from '@/api/endpoints'
import type { Recommendation } from '@/types/api'

export const useRecommendations = () => {
  const queryClient = useQueryClient()

  // Fetch recommendations from API
  const { data, isLoading, isPending, error } = useQuery({
    queryKey: ['recommendations'],
    queryFn: async () => {
      const response = await aiAPI.getRecommendations()
      return response.recommendations
    },
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
  })

  const recommendations: Recommendation[] = data || []

  // Approve recommendation mutation
  const approveMutation = useMutation({
    mutationFn: (id: string) => recommendationsAPI.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  // Reject recommendation mutation
  const rejectMutation = useMutation({
    mutationFn: (id: string) => recommendationsAPI.reject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  // Discuss recommendation mutation
  const discussMutation = useMutation({
    mutationFn: (id: string) => recommendationsAPI.discuss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  const approve = useCallback(
    async (id: string) => {
      await approveMutation.mutateAsync(id)
    },
    [approveMutation]
  )

  const reject = useCallback(
    async (id: string) => {
      await rejectMutation.mutateAsync(id)
    },
    [rejectMutation]
  )

  const discuss = useCallback(
    async (id: string) => {
      await discussMutation.mutateAsync(id)
    },
    [discussMutation]
  )

  return {
    recommendations,
    approve,
    reject,
    discuss,
    isPending: isPending || approveMutation.isPending || rejectMutation.isPending || discussMutation.isPending,
    isLoading,
    error,
  }
}
