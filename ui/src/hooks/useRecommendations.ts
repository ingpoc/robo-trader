import { useCallback } from 'react'
import { api } from '@/api/client'

export const useRecommendations = () => {
  const recommendations = [] // Mock empty array for now
  const isPending = false
  const isLoading = false

  const approve = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/approve/${id}`)
  }, [])

  const reject = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/reject/${id}`)
  }, [])

  const discuss = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/discuss/${id}`)
  }, [])

  return {
    recommendations,
    approve,
    reject,
    discuss,
    isPending,
    isLoading,
  }
}