import { usePortfolio } from '@/hooks/usePortfolio'
import { useAnalytics } from '@/hooks/useAnalytics'
import { useDashboardStore } from '@/store/dashboardStore'
import { MetricCard } from '@/components/Dashboard/MetricCard'
import { ChartCard } from '@/components/Dashboard/ChartCard'
import { HoldingsTable } from '@/components/Dashboard/HoldingsTable'
import { QuickTradeForm } from '@/components/Dashboard/QuickTradeForm'
import { AIInsights } from '@/components/Dashboard/AIInsights'
import { AlertCenter } from '@/components/Dashboard/AlertCenter'
import { Button } from '@/components/ui/Button'
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Breadcrumb } from '@/components/common/Breadcrumb'

export function Dashboard() {
  const { portfolio, analytics, isLoading, portfolioScan, marketScreening, isScanning } =
    usePortfolio()
  const { data: performanceData, isLoading: isAnalyticsLoading } = useAnalytics('30d')
  const dashboardData = useDashboardStore((state) => state.dashboardData)

  if (isLoading || isAnalyticsLoading) {
    return (
      <div className="flex flex-col gap-6 lg:gap-8 p-4 lg:p-6 animate-fade-in">
        {/* Header skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <SkeletonLoader className="h-8 w-48" />
          <div className="flex gap-2">
            <SkeletonLoader className="h-8 w-16" />
            <SkeletonLoader className="h-8 w-20" />
          </div>
        </div>

        {/* Metrics skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} className="h-24" />
          ))}
        </div>

        {/* Charts skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SkeletonCard className="h-64" />
          <SkeletonCard className="h-64" />
        </div>

        {/* Widgets skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-48" />
        </div>
      </div>
    )
  }

  const chartData = performanceData?.chart_data?.map(point => ({
    name: new Date(point.timestamp).toLocaleDateString('en-US', { weekday: 'short' }),
    value: point.value,
  })) || []

  // Calculate asset allocation from portfolio data
  const total = portfolio ? portfolio.exposure_total + portfolio.cash.free : 0
  const allocationData = portfolio && total > 0 ? [
    { name: 'Cash', value: (portfolio.cash.free / total) * 100 },
    { name: 'Equity', value: (portfolio.exposure_total / total) * 100 },
  ] : [
    { name: 'Cash', value: 100 },
    { name: 'Equity', value: 0 },
  ]

  return (
    <div className="flex flex-col gap-6 lg:gap-8 p-4 lg:p-6 overflow-auto">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h1 className="text-xl lg:text-2xl font-bold text-gray-900">Overview</h1>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => portfolioScan()}
              disabled={isScanning}
              className="flex-1 sm:flex-none"
            >
              Scan
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => marketScreening()}
              disabled={isScanning}
              className="flex-1 sm:flex-none"
            >
              Screen
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Grid - Responsive */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Available Cash"
          value={portfolio?.cash.free || 0}
          format="currency"
        />
        <MetricCard
          label="Total Exposure"
          value={portfolio?.exposure_total || 0}
          format="currency"
        />
        <MetricCard
          label="Active Positions"
          value={portfolio?.holdings.length || 0}
          format="number"
        />
        <MetricCard
          label="Risk Score"
          value={analytics?.portfolio?.concentration_risk || 0}
          format="percent"
          changeLabel={analytics?.portfolio?.dominant_sector}
        />
      </div>

      {/* Charts Grid - Responsive */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Performance" type="line" data={chartData} />
        <ChartCard title="Allocation" type="pie" data={allocationData} showLegend />
      </div>

      {/* Widgets Grid - Responsive */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <AIInsights status={dashboardData?.ai_status} />
        <AlertCenter />
        <QuickTradeForm />
      </div>

      {/* Holdings Table - Responsive */}
      {portfolio && portfolio.holdings.length > 0 && (
        <div className="overflow-x-auto">
          <HoldingsTable holdings={portfolio.holdings} totalExposure={portfolio.exposure_total} />
        </div>
      )}
    </div>
  )
}
