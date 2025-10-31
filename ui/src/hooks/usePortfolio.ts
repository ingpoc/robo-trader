import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dashboardAPI } from '@/api/endpoints'
import { toast } from '@/hooks/use-toast'

export function usePortfolio() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardAPI.getDashboardData,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  const portfolioScan = useMutation({
    mutationFn: dashboardAPI.portfolioScan,
    onSuccess: (response) => {
      // Check if OAuth is required
      if (response.status === 'oauth_required' && response.auth_url) {
        // Open OAuth URL in new window
        window.open(response.auth_url, '_blank', 'width=600,height=700')
        toast({
          title: 'OAuth Authentication Required',
          description: response.message || 'Please complete authentication in the popup window, then click Scan Portfolio again.',
          variant: 'default',
        })
      } else if (response.status === 'Portfolio scan completed') {
        // Portfolio scan completed successfully
        const source = response.source || 'unknown'
        const holdingsCount = response.holdings_count || 0
        
        // Show appropriate toast based on source
        if (source === 'zerodha_live' || source === 'zerodha') {
          toast({
            title: 'Portfolio Updated Successfully',
            description: `Portfolio updated successfully from Kite. ${holdingsCount} holdings loaded.`,
            variant: 'success',
          })
        } else if (source === 'csv_fallback' || source === 'csv') {
          toast({
            title: 'Portfolio Updated',
            description: `Portfolio updated from CSV. ${holdingsCount} holdings loaded.`,
            variant: 'success',
          })
        } else {
          toast({
            title: 'Portfolio Scan Completed',
            description: response.message || `Successfully loaded ${holdingsCount} holdings.`,
            variant: 'success',
          })
        }
        
        // Refresh dashboard data
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      } else {
        // Other success cases
        toast({
        title: 'Portfolio Scan Started',
        description: 'Analyzing your portfolio...',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      }
    },
    onError: (error) => {
      toast({
        title: 'Scan Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    },
  })

  const marketScreening = useMutation({
    mutationFn: dashboardAPI.marketScreening,
    onSuccess: () => {
      toast({
        title: 'Market Screening Started',
        description: 'Scanning market opportunities...',
        variant: 'success',
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (error) => {
      toast({
        title: 'Screening Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
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
