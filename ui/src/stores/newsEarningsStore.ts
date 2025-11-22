import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type {
  NewsEarningsState,
  NewsItem,
  EarningsReport,
  UpcomingEarnings,
  Recommendation,
  NewsEarningsData,
  TabType,
} from '@/types/domain'

interface NewsEarningsStore extends NewsEarningsState {
  // Data
  newsData: NewsItem[]
  earningsData: EarningsReport[]
  upcomingEarningsData: UpcomingEarnings[]
  recommendationsData: Recommendation[]
  lastUpdated: string | null

  // Actions
  setSelectedSymbol: (symbol: string) => void
  setPortfolioSymbols: (symbols: string[]) => void
  setActiveTab: (tab: TabType) => void
  toggleNewsExpansion: (newsId: string) => void
  setData: (data: NewsEarningsData) => void
  setRecommendations: (recommendations: Recommendation[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // Computed getters
  getFilteredNews: () => NewsItem[]
  getFilteredEarnings: () => EarningsReport[]
  getFilteredRecommendations: () => Recommendation[]
  getUpcomingEarningsForPortfolio: () => UpcomingEarnings[]
}

// Data-only initial values (actions are defined inline in the store)
const initialData = {
  newsData: [] as NewsItem[],
  earningsData: [] as EarningsReport[],
  upcomingEarningsData: [] as UpcomingEarnings[],
  recommendationsData: [] as Recommendation[],
  lastUpdated: null as string | null,
}

export const useNewsEarningsStore = create<NewsEarningsStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    selectedSymbol: '',
    portfolioSymbols: [],
    activeTab: 'news',
    expandedNews: new Set(),
    filters: {
      symbol: '',
      sentiment: [],
      dateRange: undefined,
      minRelevance: 0,
    },
    isLoading: false,
    error: null,

    ...initialData,

    // Actions
    setSelectedSymbol: (symbol) =>
      set({ selectedSymbol: symbol, filters: { ...get().filters, symbol } }),

    setPortfolioSymbols: (symbols) => set({ portfolioSymbols: symbols }),

    setActiveTab: (tab) => set({ activeTab: tab }),

    toggleNewsExpansion: (newsId) => {
      const expandedNews = new Set(get().expandedNews)
      if (expandedNews.has(newsId)) {
        expandedNews.delete(newsId)
      } else {
        expandedNews.add(newsId)
      }
      set({ expandedNews })
    },

    setData: (data) =>
      set({
        newsData: data.news,
        earningsData: data.earnings,
        upcomingEarningsData: data.upcoming_earnings,
        lastUpdated: data.last_updated,
        selectedSymbol: data.symbol,
      }),

    setRecommendations: (recommendations) =>
      set({ recommendationsData: recommendations }),

    setLoading: (loading) => set({ isLoading: loading }),

    setError: (error) => set({ error, isLoading: false }),

    // Computed getters
    getFilteredNews: () => {
      const { newsData, filters } = get()
      return newsData.filter((item) => {
        if (filters.sentiment && filters.sentiment.length > 0) {
          if (!filters.sentiment.includes(item.sentiment)) return false
        }
        if (filters.minRelevance && item.relevance_score < filters.minRelevance) {
          return false
        }
        return true
      })
    },

    getFilteredEarnings: () => {
      const { earningsData } = get()
      return earningsData
    },

    getFilteredRecommendations: () => {
      const { recommendationsData } = get()
      return recommendationsData
    },

    getUpcomingEarningsForPortfolio: () => {
      const { upcomingEarningsData, portfolioSymbols } = get()
      return upcomingEarningsData.filter((earnings) =>
        portfolioSymbols.includes(earnings.symbol)
      )
    },
  }))
)

// Selectors for optimized re-renders
export const useNewsEarningsSelectors = {
  useSelectedSymbol: () =>
    useNewsEarningsStore((state) => state.selectedSymbol),

  usePortfolioSymbols: () =>
    useNewsEarningsStore((state) => state.portfolioSymbols),

  useActiveTab: () =>
    useNewsEarningsStore((state) => state.activeTab),

  useExpandedNews: () =>
    useNewsEarningsStore((state) => state.expandedNews),

  useIsLoading: () =>
    useNewsEarningsStore((state) => state.isLoading),

  useError: () =>
    useNewsEarningsStore((state) => state.error),

  useNewsData: () =>
    useNewsEarningsStore((state) => state.getFilteredNews()),

  useEarningsData: () =>
    useNewsEarningsStore((state) => state.getFilteredEarnings()),

  useRecommendationsData: () =>
    useNewsEarningsStore((state) => state.getFilteredRecommendations()),

  useUpcomingEarningsData: () =>
    useNewsEarningsStore((state) => state.getUpcomingEarningsForPortfolio()),

  useLastUpdated: () =>
    useNewsEarningsStore((state) => state.lastUpdated),
}