import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { formatDate, formatDateTime, formatRelativeTime } from '@/utils/format'
import { newsEarningsAPI } from '@/api/endpoints'
import { api } from '@/api/client'
import { useRecommendations } from '@/hooks/useRecommendations'
import { TrendingUp, TrendingDown, Minus, ExternalLink, Calendar, BarChart3, Target, AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

interface NewsItem {
  symbol: string
  title: string
  summary: string
  content?: string
  source?: string
  sentiment: string
  relevance_score: number
  published_at: string
  fetched_at: string
  citations?: string[]
  created_at: string
}

interface EarningsReport {
  symbol: string
  fiscal_period: string
  fiscal_year?: number
  fiscal_quarter?: number
  report_date: string
  eps_actual?: number
  eps_estimated?: number
  revenue_actual?: number
  revenue_estimated?: number
  surprise_pct?: number
  guidance?: string
  next_earnings_date?: string
  fetched_at: string
  created_at: string
}


export function NewsEarnings() {
    const [selectedSymbol, setSelectedSymbol] = useState<string>('')
    const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([])
    const [activeTab, setActiveTab] = useState<'news' | 'earnings' | 'recommendations'>('news')

   const { recommendations, isLoading: recommendationsLoading, approve, reject, discuss } = useRecommendations()

  // Fetch portfolio data to get available symbols
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/api/dashboard'),
    refetchInterval: 10000,
  })

  // Fetch news and earnings data for selected symbol
  const { data: newsEarningsData, isLoading: dataLoading, error } = useQuery({
    queryKey: ['news-earnings', selectedSymbol],
    queryFn: () => newsEarningsAPI.getNewsAndEarnings(selectedSymbol),
    enabled: !!selectedSymbol,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Fetch upcoming earnings for all portfolio symbols
  const { data: upcomingEarningsData, isLoading: upcomingLoading } = useQuery({
    queryKey: ['upcoming-earnings'],
    queryFn: () => newsEarningsAPI.getUpcomingEarnings(60), // Next 60 days
    refetchInterval: 300000, // Refetch every 5 minutes
  })

  // Extract portfolio symbols
  useEffect(() => {
    if (dashboardData && (dashboardData as any).portfolio?.holdings) {
      const symbols = (dashboardData as any).portfolio.holdings
        .map((holding: any) => holding.symbol)
        .filter(Boolean)
        .sort()
      setPortfolioSymbols(symbols)

      // Auto-select first symbol if none selected
      if (!selectedSymbol && symbols.length > 0) {
        setSelectedSymbol(symbols[0])
      }
    }
  }, [dashboardData, selectedSymbol])

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950 dark:border-emerald-800'
      case 'negative':
        return 'text-rose-700 bg-rose-50 border-rose-200 dark:text-rose-400 dark:bg-rose-950 dark:border-rose-800'
      default:
        return 'text-warmgray-700 bg-warmgray-50 border-warmgray-300 dark:text-warmgray-400 dark:bg-warmgray-950 dark:border-warmgray-800'
    }
  }

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive':
        return <TrendingUp className="w-4 h-4" />
      case 'negative':
        return <TrendingDown className="w-4 h-4" />
      default:
        return <Minus className="w-4 h-4" />
    }
  }


  const getRiskColor = (surprise?: number) => {
    if (!surprise) return 'text-warmgray-500'
    if (Math.abs(surprise) > 10) return 'text-rose-600'
    if (Math.abs(surprise) > 5) return 'text-copper-600'
    return 'text-emerald-600'
  }

  const getRecommendationColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900 dark:text-emerald-200 dark:border-emerald-800'
      case 'sell':
        return 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900 dark:text-rose-200 dark:border-rose-800'
      case 'hold':
        return 'bg-copper-100 text-copper-800 border-copper-200 dark:bg-copper-900 dark:text-copper-200 dark:border-copper-800'
      default:
        return 'bg-warmgray-100 text-warmgray-800 border-warmgray-300 dark:bg-warmgray-900 dark:text-warmgray-200 dark:border-warmgray-800'
    }
  }

  const getRecommendationIcon = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy':
        return <TrendingUp className="w-5 h-5" />
      case 'sell':
        return <TrendingDown className="w-5 h-5" />
      case 'hold':
        return <Minus className="w-5 h-5" />
      default:
        return <Target className="w-5 h-5" />
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-emerald-600" />
      case 'rejected':
        return <XCircle className="w-4 h-4 text-rose-600" />
      case 'discussing':
        return <Clock className="w-4 h-4 text-copper-600" />
      default:
        return <Clock className="w-4 h-4 text-warmgray-400" />
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-emerald-600'
    if (confidence >= 0.6) return 'text-copper-600'
    return 'text-rose-600'
  }

  if (dashboardLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-warmgray-50 to-warmgray-100 dark:from-warmgray-900 dark:to-warmgray-800">
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-warmgray-900 font-serif dark:text-warmgray-100">
            Market Intelligence Hub
          </h1>
          <p className="text-lg text-warmgray-600 dark:text-warmgray-400 max-w-2xl mx-auto">
            Real-time news, earnings analysis, and AI-powered recommendations for informed trading decisions
          </p>
        </div>

        {/* Symbol Selector */}
        <Card className="shadow-md border-warmgray-300 bg-white/70 dark:bg-warmgray-800/70 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
              <div className="flex-1 min-w-0">
                <label htmlFor="symbol-select" className="block text-sm font-semibold text-warmgray-700 dark:text-warmgray-300 mb-2">
                  Select Portfolio Stock
                </label>
                <Select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="w-full"
                >
                  <option value="">Choose a stock to analyze...</option>
                  {portfolioSymbols.map((symbol) => (
                    <option key={symbol} value={symbol}>
                      {symbol}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="flex items-center gap-2"
                >
                  <BarChart3 className="w-4 h-4" />
                  Refresh
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {selectedSymbol && (
          <>
            {/* Tab Navigation */}
            <div className="flex justify-center">
              <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-xl p-1 shadow-lg border border-slate-200 dark:border-slate-700">
                <div className="flex space-x-1">
                  {[
                    { id: 'news', label: 'News Feed', icon: '📰' },
                    { id: 'earnings', label: 'Earnings', icon: '📊' },
                    { id: 'recommendations', label: 'AI Recommendations', icon: '🤖' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center gap-2 ${
                        activeTab === tab.id
                          ? 'bg-copper-500 text-white shadow-md transform scale-105'
                          : 'text-warmgray-600 dark:text-warmgray-400 hover:text-warmgray-900 dark:hover:text-warmgray-200 hover:bg-warmgray-100 dark:hover:bg-warmgray-700'
                      }`}
                    >
                      <span className="text-lg">{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Tab Content */}
          {activeTab === 'news' && (
            <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
                    📰 News Feed for {selectedSymbol}
                  </CardTitle>
                  {newsEarningsData?.last_updated && (
                    <div className="text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-3 py-1 rounded-full">
                      Updated {formatRelativeTime(newsEarningsData.last_updated)}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {dataLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center space-y-4">
                      <LoadingSpinner />
                      <p className="text-slate-600 dark:text-slate-400">Loading latest news...</p>
                    </div>
                  </div>
                ) : error ? (
                  <div className="text-center py-12">
                    <div className="bg-rose-50 dark:bg-rose-950 border border-rose-200 dark:border-rose-800 rounded-xl p-6 max-w-md mx-auto">
                      <AlertTriangle className="w-12 h-12 text-rose-600 dark:text-rose-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-rose-900 dark:text-rose-100 mb-2">Unable to load news data</h3>
                      <p className="text-rose-700 dark:text-rose-300 text-sm mb-4">
                        {error?.message?.includes('404') ? 'Stock data not found. Please select a different stock.' :
                         error?.message?.includes('500') ? 'Server error. Please try again in a few moments.' :
                         error?.message?.includes('timeout') ? 'Request timed out. Please check your connection and try again.' :
                         'Failed to fetch news data. Please refresh the page or try again later.'}
                      </p>
                      <Button
                        onClick={() => window.location.reload()}
                        variant="outline"
                        className="border-rose-300 text-rose-700 hover:bg-rose-50"
                      >
                        Retry
                      </Button>
                    </div>
                  </div>
                ) : (newsEarningsData?.news && newsEarningsData.news.length > 0) ? (
                  <Accordion type="multiple" className="space-y-4">
                    {newsEarningsData.news.map((item: NewsItem, index: number) => (
                      <AccordionItem
                        key={index}
                        value={`news-${index}`}
                        className="group border border-slate-200 dark:border-slate-700 rounded-xl hover:shadow-lg hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-300 bg-white dark:bg-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/80"
                      >
                        <AccordionTrigger className="px-6 py-4 hover:no-underline">
                          <div className="flex items-start justify-between w-full mr-4">
                            <h3 className="font-bold text-lg text-slate-900 dark:text-slate-100 flex-1 leading-tight text-left">
                              {item.title}
                            </h3>
                            <div className={`px-3 py-2 rounded-full text-sm font-semibold border-2 flex items-center gap-2 transition-all duration-200 ml-4 ${getSentimentColor(item.sentiment)}`}>
                              {getSentimentIcon(item.sentiment)}
                              <span className="capitalize">{item.sentiment}</span>
                            </div>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent className="px-6 pb-4">
                          <div className="space-y-4">
                            <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                              {item.content || item.summary}
                            </p>

                            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
                              <div className="flex items-center gap-6 text-sm text-slate-500 dark:text-slate-400">
                                {item.source && (
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">Source:</span>
                                    <span className="bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded-md">{item.source}</span>
                                  </div>
                                )}
                                <div className="flex items-center gap-2">
                                  <Calendar className="w-4 h-4" />
                                  <span>{formatDateTime(item.published_at)}</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="text-right">
                                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Relevance</div>
                                  <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                                    {(item.relevance_score * 100).toFixed(0)}%
                                  </div>
                                </div>
                                {item.citations && item.citations.length > 0 && (
                                  <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-700">
                                    <ExternalLink className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                ) : (
                  <div className="text-center py-12">
                    <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl">📰</span>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Recent News</h3>
                    <p className="text-slate-600 dark:text-slate-400">No recent news found for {selectedSymbol}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'earnings' && (
            <div className="space-y-6">
              {/* Earnings Reports */}
              <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
                    📊 Earnings Reports for {selectedSymbol}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {dataLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="text-center space-y-4">
                        <LoadingSpinner />
                        <p className="text-slate-600 dark:text-slate-400">Loading earnings data...</p>
                      </div>
                    </div>
                  ) : error ? (
                    <div className="text-center py-12">
                      <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md mx-auto">
                        <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Unable to load earnings data</h3>
                        <p className="text-red-700 dark:text-red-300 text-sm">
                          {error?.message?.includes('404') ? 'Earnings data not found for this stock.' :
                           error?.message?.includes('500') ? 'Server error retrieving earnings. Please try again later.' :
                           error?.message?.includes('timeout') ? 'Request timed out. Please check your connection.' :
                           'Failed to fetch earnings data. Data may not be available yet.'}
                        </p>
                      </div>
                    </div>
                  ) : (newsEarningsData?.earnings && newsEarningsData.earnings.length > 0) ? (
                    <Accordion type="multiple" className="space-y-6">
                      {newsEarningsData.earnings.map((report: EarningsReport, index: number) => (
                        <AccordionItem
                          key={index}
                          value={`earnings-${index}`}
                          className="border border-slate-200 dark:border-slate-700 rounded-xl bg-gradient-to-r from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 hover:shadow-lg transition-all duration-300"
                        >
                          <AccordionTrigger className="px-6 py-4 hover:no-underline">
                            <div className="flex items-center justify-between w-full">
                              <div className="flex items-center gap-4">
                                <h4 className="font-bold text-xl text-slate-900 dark:text-slate-100">{report.fiscal_period}</h4>
                                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                                  <Calendar className="w-4 h-4" />
                                  <span className="text-sm">{formatDate(report.report_date)}</span>
                                </div>
                              </div>
                              {report.surprise_pct !== undefined && report.surprise_pct !== null && (
                                <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${
                                  Math.abs(report.surprise_pct) > 10 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                  Math.abs(report.surprise_pct) > 5 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' :
                                  'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
                                }`}>
                                  <Target className="w-4 h-4" />
                                  {report.surprise_pct >= 0 ? '+' : ''}{report.surprise_pct.toFixed(1)}% Surprise
                                </div>
                              )}
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="px-6 pb-4">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                              {/* EPS Data */}
                              <div className="space-y-3">
                                <h5 className="font-semibold text-slate-900 dark:text-slate-100">EPS Performance</h5>
                                <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                                    {report.eps_actual ? `$${report.eps_actual.toFixed(2)}` : 'N/A'}
                                  </div>
                                  {report.eps_estimated && (
                                    <div className="text-sm text-slate-600 dark:text-slate-400">
                                      Est: ${report.eps_estimated.toFixed(2)}
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Revenue Data */}
                              <div className="space-y-3">
                                <h5 className="font-semibold text-slate-900 dark:text-slate-100">Revenue</h5>
                                <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                                  {report.revenue_actual ? (
                                    <>
                                      <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                                        ${(report.revenue_actual / 1000000).toFixed(0)}M
                                      </div>
                                      {report.revenue_estimated && (
                                        <div className="text-sm text-slate-600 dark:text-slate-400">
                                          Est: ${(report.revenue_estimated / 1000000).toFixed(0)}M
                                        </div>
                                      )}
                                    </>
                                  ) : (
                                    <div className="text-slate-500 dark:text-slate-400">N/A</div>
                                  )}
                                </div>
                              </div>

                              {/* Next Earnings */}
                              <div className="space-y-3">
                                <h5 className="font-semibold text-slate-900 dark:text-slate-100">Next Report</h5>
                                <div className="bg-white dark:bg-slate-700 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
                                  {report.next_earnings_date ? (
                                    <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                                      {formatDate(report.next_earnings_date)}
                                    </div>
                                  ) : (
                                    <div className="text-slate-500 dark:text-slate-400">TBD</div>
                                  )}
                                </div>
                              </div>
                            </div>

                            {report.guidance && (
                              <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
                                <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Management Guidance</h5>
                                <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                                  <p className="text-blue-900 dark:text-blue-100">{report.guidance}</p>
                                </div>
                              </div>
                            )}
                          </AccordionContent>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  ) : (
                    <div className="text-center py-12">
                      <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">📊</span>
                      </div>
                      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Earnings Data</h3>
                      <p className="text-slate-600 dark:text-slate-400">No earnings reports found for {selectedSymbol}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Upcoming Earnings Calendar */}
              <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
                    📅 Upcoming Earnings Calendar
                  </CardTitle>
                  <p className="text-slate-600 dark:text-slate-400">
                    Next earnings reports for your portfolio stocks (next 60 days)
                  </p>
                </CardHeader>
                <CardContent>
                  {upcomingLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-center space-y-4">
                        <LoadingSpinner />
                        <p className="text-slate-600 dark:text-slate-400">Loading upcoming earnings...</p>
                      </div>
                    </div>
                  ) : upcomingEarningsData?.upcoming_earnings && upcomingEarningsData.upcoming_earnings.length > 0 ? (
                    (() => {
                      const portfolioEarnings = upcomingEarningsData.upcoming_earnings
                        .filter(earnings => portfolioSymbols.includes(earnings.symbol))
                        .sort((a, b) => new Date(a.next_earnings_date).getTime() - new Date(b.next_earnings_date).getTime());

                      // Group by weeks
                      const groupedEarnings = portfolioEarnings.reduce((groups, earnings) => {
                        const date = new Date(earnings.next_earnings_date);
                        const weekStart = new Date(date);
                        weekStart.setDate(date.getDate() - date.getDay()); // Start of week (Sunday)
                        const weekKey = weekStart.toISOString().split('T')[0];

                        if (!groups[weekKey]) {
                          groups[weekKey] = [];
                        }
                        groups[weekKey].push(earnings);
                        return groups;
                      }, {} as Record<string, typeof portfolioEarnings>);

                      return portfolioEarnings.length > 0 ? (
                        <Accordion type="multiple" className="space-y-4">
                          {Object.entries(groupedEarnings)
                            .sort(([a], [b]) => a.localeCompare(b))
                            .map(([weekKey, earnings]) => {
                              const weekStart = new Date(weekKey);
                              const weekEnd = new Date(weekStart);
                              weekEnd.setDate(weekStart.getDate() + 6);
                              const weekLabel = `${formatDate(weekStart.toISOString())} - ${formatDate(weekEnd.toISOString())}`;

                              return (
                                <AccordionItem
                                  key={weekKey}
                                  value={`week-${weekKey}`}
                                  className="border border-slate-200 dark:border-slate-700 rounded-lg bg-gradient-to-r from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 hover:shadow-md transition-all duration-200"
                                >
                                  <AccordionTrigger className="px-4 py-3 hover:no-underline">
                                    <div className="flex items-center gap-3">
                                      <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                                        {weekLabel} ({earnings.length} report{earnings.length !== 1 ? 's' : ''})
                                      </span>
                                    </div>
                                  </AccordionTrigger>
                                  <AccordionContent className="px-4 pb-3">
                                    <div className="space-y-3">
                                      {earnings.map((earning, index) => (
                                        <div
                                          key={index}
                                          className="flex items-center justify-between p-3 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/50"
                                        >
                                          <div className="flex items-center gap-4">
                                            <div className="bg-blue-100 dark:bg-blue-900 rounded-full w-10 h-10 flex items-center justify-center">
                                              <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                                                {earning.symbol.slice(0, 2)}
                                              </span>
                                            </div>
                                            <div>
                                              <h4 className="font-bold text-lg text-slate-900 dark:text-slate-100">
                                                {earning.symbol}
                                              </h4>
                                              <p className="text-sm text-slate-600 dark:text-slate-400">
                                                {earning.fiscal_period}
                                              </p>
                                              {earning.guidance && (
                                                <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 max-w-md truncate">
                                                  {earning.guidance}
                                                </p>
                                              )}
                                            </div>
                                          </div>
                                          <div className="text-right">
                                            <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                                              {formatDate(earning.next_earnings_date)}
                                            </div>
                                            <div className="text-sm text-slate-600 dark:text-slate-400">
                                              {Math.ceil((new Date(earning.next_earnings_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))} days
                                            </div>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </AccordionContent>
                                </AccordionItem>
                              );
                            })}
                        </Accordion>
                      ) : (
                        <div className="text-center py-8">
                          <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                            <span className="text-2xl">📅</span>
                          </div>
                          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Upcoming Earnings</h3>
                          <p className="text-slate-600 dark:text-slate-400">No earnings reports scheduled for your portfolio stocks in the next 60 days.</p>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="text-center py-8">
                      <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">📅</span>
                      </div>
                      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Upcoming Earnings</h3>
                      <p className="text-slate-600 dark:text-slate-400">Unable to load upcoming earnings data.</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === 'recommendations' && (
            <div className="space-y-6">
              {/* Recommendations Overview */}
              <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
                    🤖 AI Trading Recommendations
                  </CardTitle>
                  <p className="text-slate-600 dark:text-slate-400">
                    Real-time AI-powered buy/sell/hold recommendations based on fundamental and technical analysis
                  </p>
                </CardHeader>
                <CardContent>
                  {recommendationsLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="text-center space-y-4">
                        <LoadingSpinner />
                        <p className="text-slate-600 dark:text-slate-400">Loading AI recommendations...</p>
                      </div>
                    </div>
                  ) : recommendations && recommendations.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {recommendations.map((rec) => (
                        <div
                          key={rec.id}
                          className="border border-slate-200 dark:border-slate-700 rounded-xl p-6 bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 hover:shadow-lg transition-all duration-300"
                        >
                          {/* Header */}
                          <div className="flex items-start justify-between mb-4">
                            <div>
                              <h3 className="font-bold text-xl text-slate-900 dark:text-slate-100 mb-1">
                                {rec.recommendation.symbol}
                              </h3>
                              <div className="flex items-center gap-2">
                                {getStatusIcon(rec.status)}
                                <span className="text-sm text-slate-600 dark:text-slate-400 capitalize">
                                  {rec.status}
                                </span>
                              </div>
                            </div>
                            <div className={`px-4 py-2 rounded-full text-sm font-bold border-2 flex items-center gap-2 ${getRecommendationColor(rec.recommendation.action)}`}>
                              {getRecommendationIcon(rec.recommendation.action)}
                              <span>{rec.recommendation.action.toUpperCase()}</span>
                            </div>
                          </div>

                          {/* Confidence & Reasoning */}
                          <div className="space-y-4">
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Confidence</span>
                                <span className={`text-sm font-bold ${getConfidenceColor(rec.recommendation.confidence)}`}>
                                  {(rec.recommendation.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                <div
                                  className={`h-2 rounded-full transition-all duration-300 ${
                                    rec.recommendation.confidence >= 0.8 ? 'bg-emerald-500' :
                                    rec.recommendation.confidence >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
                                  }`}
                                  style={{ width: `${rec.recommendation.confidence * 100}%` }}
                                />
                              </div>
                            </div>

                            <div>
                              <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-2">Analysis</h4>
                              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                                {rec.recommendation.reasoning}
                              </p>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          {rec.status === 'pending' && (
                            <div className="flex gap-2 mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
                              <Button
                                onClick={() => approve(rec.id)}
                                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                                size="sm"
                              >
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Approve
                              </Button>
                              <Button
                                onClick={() => reject(rec.id)}
                                variant="outline"
                                className="flex-1 border-red-300 text-red-700 hover:bg-red-50"
                                size="sm"
                              >
                                <XCircle className="w-4 h-4 mr-2" />
                                Reject
                              </Button>
                              <Button
                                onClick={() => discuss(rec.id)}
                                variant="outline"
                                className="flex-1 border-amber-300 text-amber-700 hover:bg-amber-50"
                                size="sm"
                              >
                                <Clock className="w-4 h-4 mr-2" />
                                Discuss
                              </Button>
                            </div>
                          )}

                          {/* Timestamp */}
                          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              Generated {rec.created_at ? formatRelativeTime(rec.created_at) : 'recently'}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">🤖</span>
                      </div>
                      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Active Recommendations</h3>
                      <p className="text-slate-600 dark:text-slate-400 mb-6">
                        AI recommendations will appear here when the system analyzes market conditions and generates trading signals.
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
                        {[
                          { icon: '📰', title: 'News Analysis', desc: 'Sentiment and relevance scoring' },
                          { icon: '📊', title: 'Earnings Data', desc: 'Fundamental analysis integration' },
                          { icon: '📈', title: 'Technical Signals', desc: 'Chart patterns and indicators' }
                        ].map((feature, index) => (
                          <div key={index} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
                            <div className="text-2xl mb-2">{feature.icon}</div>
                            <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">{feature.title}</h4>
                            <p className="text-sm text-slate-600 dark:text-slate-400">{feature.desc}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Performance Metrics */}
              {recommendations && recommendations.length > 0 && (
                <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2 text-slate-900 dark:text-slate-100">
                      <BarChart3 className="w-5 h-5" />
                      Recommendation Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-emerald-600 mb-1">
                          {recommendations.filter(r => r.status === 'approved').length}
                        </div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">Approved</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-amber-600 mb-1">
                          {recommendations.filter(r => r.status === 'discussing').length}
                        </div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">Under Discussion</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600 mb-1">
                          {recommendations.filter(r => r.status === 'rejected').length}
                        </div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">Rejected</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600 mb-1">
                          {recommendations.filter(r => r.status === 'pending').length}
                        </div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">Pending</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          </>
        )}
      </div>
    </div>
  )
}