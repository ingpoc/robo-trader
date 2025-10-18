import { memo, Suspense } from 'react'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useNewsEarnings } from '@/hooks/useNewsEarnings'
import { TabNavigation } from '@/components/ui/TabNavigation'
import { SymbolSelector } from './components/SymbolSelector'
import { NewsFeed } from './components/NewsFeed'
import { EarningsReports } from './components/EarningsReports'
import { UpcomingEarnings } from './components/UpcomingEarnings'
import { RecommendationsPanel } from './components/RecommendationsPanel'

const NewsEarningsFeature = memo(() => {
  const {
    selectedSymbol,
    portfolioSymbols,
    activeTab,
    isLoading,
    error,
    lastUpdated,
    newsData,
    earningsData,
    recommendationsData,
    upcomingEarningsData,
    selectSymbol,
    setActiveTab,
    refreshData,
  } = useNewsEarnings()

  const tabs = [
    { id: 'news', label: 'News Feed', icon: '📰' },
    { id: 'earnings', label: 'Earnings', icon: '📊' },
    { id: 'recommendations', label: 'AI Recommendations', icon: '🤖' },
  ] as const

  const renderTabContent = () => {
    switch (activeTab) {
      case 'news':
        return (
          <NewsFeed
            news={newsData}
            lastUpdated={lastUpdated}
            isLoading={isLoading}
            error={error}
            onRetry={refreshData}
          />
        )
      case 'earnings':
        return (
          <div className="space-y-6">
            <EarningsReports
              earnings={earningsData}
              isLoading={isLoading}
              error={error}
              onRetry={refreshData}
            />
            <UpcomingEarnings
              earnings={upcomingEarningsData}
              portfolioSymbols={portfolioSymbols}
              isLoading={isLoading}
              error={error}
              onRetry={refreshData}
            />
          </div>
        )
      case 'recommendations':
        return (
          <RecommendationsPanel
            recommendations={recommendationsData}
            isLoading={isLoading}
            error={error}
            onRetry={refreshData}
          />
        )
      default:
        return null
    }
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-warmgray-50 to-warmgray-100 dark:from-warmgray-900 dark:to-warmgray-800">
        <div className="max-w-7xl mx-auto p-6 space-y-8">
          {/* Header */}
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-warmgray-900 to-warmgray-600 dark:from-warmgray-100 dark:to-warmgray-400 bg-clip-text text-transparent">
              Market Intelligence Hub
            </h1>
            <p className="text-lg text-warmgray-600 dark:text-warmgray-400 max-w-2xl mx-auto">
              Real-time news, earnings analysis, and AI-powered recommendations for informed trading decisions
            </p>
          </div>

          {/* Symbol Selector */}
          <SymbolSelector
            selectedSymbol={selectedSymbol}
            portfolioSymbols={portfolioSymbols}
            onSymbolChange={selectSymbol}
            onRefresh={refreshData}
            isLoading={isLoading}
          />

          {selectedSymbol && (
            <>
              {/* Tab Navigation */}
              <TabNavigation
                activeTab={activeTab}
                onTabChange={setActiveTab}
                tabs={tabs}
              />

              {/* Tab Content */}
              <Suspense fallback={<LoadingSpinner />}>
                {renderTabContent()}
              </Suspense>
            </>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
})

NewsEarningsFeature.displayName = 'NewsEarningsFeature'

export { NewsEarningsFeature }