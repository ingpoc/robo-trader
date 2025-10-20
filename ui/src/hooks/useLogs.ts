import { useQuery } from '@tanstack/react-query'
import { logsAPI } from '@/api/endpoints'

export function useLogs(limit: number = 100) {
  return useQuery({
    queryKey: ['logs', limit],
    queryFn: () => logsAPI.getLogs(limit),
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })
}