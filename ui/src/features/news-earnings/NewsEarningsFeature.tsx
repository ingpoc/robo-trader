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
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'

interface NewsEarningsFeatureProps {
  embedded?: boolean
}

const NewsEarningsFeature = memo(({ embedded = false }: NewsEarningsFeatureProps) => {
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
    { id: 'news', label: 'News Feed', active: activeTab === 'news' },
    { id: 'earnings', label: 'Earnings', active: activeTab === 'earnings' },
    { id: 'recommendations', label: 'AI Recommendations', active: activeTab === 'recommendations' },
  ]

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
      <div className={embedded ? 'space-y-6' : 'page-wrapper'}>
        <div className="flex flex-col gap-6">
          {!embedded ? <Breadcrumb /> : null}

          {!embedded ? (
            <PageHeader
              title="News & Earnings"
              description="Review catalysts, earnings surprises, and recommendation candidates that can feed the paper-trading decision loop."
            />
          ) : null}

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
