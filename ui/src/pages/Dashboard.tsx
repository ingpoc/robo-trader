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

export function Dashboard() {
  const { portfolio, analytics, isLoading, portfolioScan, marketScreening, isScanning } =
    usePortfolio()
  const { data: performanceData, isLoading: isAnalyticsLoading } = useAnalytics('30d')
  const dashboardData = useDashboardStore((state) => state.dashboardData)

  if (isLoading || isAnalyticsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg text-gray-600">Loading dashboard...</div>
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
    <div className="flex flex-col gap-6 p-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Trading Dashboard</h1>
          <p className="text-sm text-gray-600">
            Here's what's happening with your portfolio today
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => portfolioScan()}
            disabled={isScanning}
          >
            Scan Portfolio
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => marketScreening()}
            disabled={isScanning}
          >
            Market Screening
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
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

      <div className="grid grid-cols-2 gap-4">
        <ChartCard title="Portfolio Performance" type="line" data={chartData} />
        <ChartCard title="Asset Allocation" type="pie" data={allocationData} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <AIInsights status={dashboardData?.ai_status} />
        <AlertCenter />
        <QuickTradeForm />
      </div>

      {portfolio && portfolio.holdings.length > 0 && (
        <HoldingsTable holdings={portfolio.holdings} totalExposure={portfolio.exposure_total} />
      )}
    </div>
  )
}
