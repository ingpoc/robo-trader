import { useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNewsEarningsStore, useNewsEarningsSelectors } from '@/stores/newsEarningsStore'
import { api } from '@/api/client'
import { newsEarningsAPI } from '@/api/endpoints'
import { API_ENDPOINTS, REFRESH_INTERVALS } from '@/lib/constants'
import type { NewsEarningsData } from '@/types/domain'

export const useNewsEarnings = () => {
  const {
    selectedSymbol,
    setSelectedSymbol,
    setPortfolioSymbols,
    setData,
    setRecommendations,
    setLoading,
    setError,
  } = useNewsEarningsStore()

  // Fetch dashboard data to get portfolio symbols
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get(API_ENDPOINTS.dashboard),
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  // Fetch news and earnings data for selected symbol
  const {
    data: newsEarningsData,
    isLoading: dataLoading,
    error,
    refetch: refetchNewsEarnings,
  } = useQuery({
    queryKey: ['news-earnings', selectedSymbol],
    queryFn: () => newsEarningsAPI.getNewsAndEarnings(selectedSymbol),
    enabled: !!selectedSymbol,
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
  })

  // Fetch upcoming earnings for all portfolio symbols
  const { data: upcomingEarningsData, refetch: refetchUpcoming } = useQuery({
    queryKey: ['upcoming-earnings'],
    queryFn: () => newsEarningsAPI.getUpcomingEarnings(60),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })

  // Fetch recommendations
  const { data: recommendationsData, refetch: refetchRecommendations } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => api.get(API_ENDPOINTS.recommendations),
    staleTime: 60000,
    gcTime: 10 * 60 * 1000,
  })

  // Extract portfolio symbols and set initial symbol
  useEffect(() => {
    if (dashboardData?.portfolio?.holdings) {
      const symbols = dashboardData.portfolio.holdings
        .map((holding: any) => holding.symbol)
        .filter(Boolean)
        .sort()

      setPortfolioSymbols(symbols)

      // Auto-select first symbol if none selected
      if (!selectedSymbol && symbols.length > 0) {
        setSelectedSymbol(symbols[0])
      }
    }
  }, [dashboardData, selectedSymbol, setSelectedSymbol, setPortfolioSymbols])

  // Update store with fetched data
  useEffect(() => {
    if (newsEarningsData && upcomingEarningsData) {
      const combinedData: NewsEarningsData = {
        ...newsEarningsData,
        upcoming_earnings: upcomingEarningsData.upcoming_earnings || [],
      }
      setData(combinedData)
    }
  }, [newsEarningsData, upcomingEarningsData, setData])

  // Update recommendations in store
  useEffect(() => {
    if (recommendationsData?.recommendations) {
      setRecommendations(recommendationsData.recommendations)
    }
  }, [recommendationsData, setRecommendations])

  // Update loading and error states
  useEffect(() => {
    setLoading(dataLoading || dashboardLoading)
  }, [dataLoading, dashboardLoading, setLoading])

  useEffect(() => {
    if (error) {
      setError(error.message || 'Failed to load data')
    } else {
      setError(null)
    }
  }, [error, setError])

  // Actions
  const refreshData = useCallback(async () => {
    await Promise.all([
      refetchNewsEarnings(),
      refetchUpcoming(),
      refetchRecommendations(),
    ])
  }, [refetchNewsEarnings, refetchUpcoming, refetchRecommendations])

  const selectSymbol = useCallback((symbol: string) => {
    setSelectedSymbol(symbol)
  }, [setSelectedSymbol])

  return {
    // State
    selectedSymbol,
    portfolioSymbols: useNewsEarningsSelectors.usePortfolioSymbols(),
    activeTab: useNewsEarningsSelectors.useActiveTab(),
    isLoading: useNewsEarningsSelectors.useIsLoading(),
    error: useNewsEarningsSelectors.useError(),
    lastUpdated: useNewsEarningsSelectors.useLastUpdated(),

    // Data
    newsData: useNewsEarningsSelectors.useNewsData(),
    earningsData: useNewsEarningsSelectors.useEarningsData(),
    recommendationsData: useNewsEarningsSelectors.useRecommendationsData(),
    upcomingEarningsData: useNewsEarningsSelectors.useUpcomingEarningsData(),

    // Actions
    selectSymbol,
    refreshData,
    setActiveTab: useNewsEarningsStore((state) => state.setActiveTab),
    toggleNewsExpansion: useNewsEarningsStore((state) => state.toggleNewsExpansion),
  }
}