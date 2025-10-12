import { useCallback } from 'react'
import { api } from '@/api/client'

export const useRecommendations = () => {
  const approve = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/${id}/approve`)
  }, [])

  const reject = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/${id}/reject`)
  }, [])

  const discuss = useCallback(async (id: string) => {
    await api.post(`/api/recommendations/${id}/discuss`)
  }, [])

  return {
    approve,
    reject,
    discuss,
  }
}