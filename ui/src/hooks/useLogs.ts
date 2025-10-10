import { useQuery } from '@tanstack/react-query'
import { logsAPI } from '@/api/endpoints'

export function useLogs(limit: number = 100) {
  return useQuery({
    queryKey: ['logs', limit],
    queryFn: () => logsAPI.getLogs(limit),
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Consider data fresh for 10 seconds
    retry: 2,
  })
}