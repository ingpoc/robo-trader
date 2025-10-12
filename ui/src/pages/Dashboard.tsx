import { usePortfolio } from '@/hooks/usePortfolio'
import { useAnalytics } from '@/hooks/useAnalytics'
import { useAgents } from '@/hooks/useAgents'
import { useDashboardStore } from '@/store/dashboardStore'
import { MetricCard } from '@/components/Dashboard/MetricCard'
import { ChartCard } from '@/components/Dashboard/ChartCard'
import { HoldingsTable } from '@/components/Dashboard/HoldingsTable'
import { QuickTradeForm } from '@/components/Dashboard/QuickTradeForm'
import { AIInsights } from '@/components/Dashboard/AIInsights'
import { AlertCenter } from '@/components/Dashboard/AlertCenter'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SkeletonCard, SkeletonLoader, SkeletonGrid, SkeletonTable } from '@/components/common/SkeletonLoader'
import { LoadingChart } from '@/components/common/LoadingStates'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Activity, CheckCircle, XCircle, Clock, AlertTriangle, TrendingUp, DollarSign, PieChart, Users } from 'lucide-react'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

export function Dashboard() {
  const { portfolio, analytics, isLoading, portfolioScan, marketScreening, isScanning } =
    usePortfolio()
  const { data: performanceData, isLoading: isAnalyticsLoading } = useAnalytics('30d')
  const { agents, isLoading: isAgentsLoading } = useAgents()
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
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Monitor your portfolio performance and AI insights</p>
          </div>
          <div className="flex gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex-1 sm:flex-none">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => portfolioScan()}
                    disabled={isScanning}
                    className="w-full sm:w-auto"
                    aria-label="Scan portfolio for updates"
                  >
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Scan Portfolio
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh portfolio data and update current positions and values</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex-1 sm:flex-none">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => marketScreening()}
                    disabled={isScanning}
                    className="w-full sm:w-auto"
                    aria-label="Perform market screening"
                  >
                    <PieChart className="w-4 h-4 mr-2" />
                    Market Screen
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Analyze market data and identify potential investment opportunities</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-6">
          <TabsTrigger value="overview" className="text-sm">Overview</TabsTrigger>
          <TabsTrigger value="holdings" className="text-sm">Holdings</TabsTrigger>
          <TabsTrigger value="analytics" className="text-sm">Analytics</TabsTrigger>
          <TabsTrigger value="recommendations" className="text-sm">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Metrics Grid - Responsive */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Available Cash"
              value={portfolio?.cash.free || 0}
              format="currency"
              tooltip="The amount of cash available for trading and investments"
            />
            <MetricCard
              label="Total Exposure"
              value={portfolio?.exposure_total || 0}
              format="currency"
              tooltip="Total market value of all your current positions"
            />
            <MetricCard
              label="Active Positions"
              value={portfolio?.holdings.length || 0}
              format="number"
              tooltip="Number of different securities you currently hold"
            />
            <MetricCard
              label="Risk Score"
              value={analytics?.portfolio?.concentration_risk || 0}
              format="percent"
              changeLabel={analytics?.portfolio?.dominant_sector}
              tooltip="Portfolio concentration risk based on sector allocation"
            />
          </div>

          {/* Charts Grid - Responsive */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="Performance Trend" type="line" data={chartData} isLoading={isAnalyticsLoading} />
            <ChartCard title="Asset Allocation" type="pie" data={allocationData} showLegend isLoading={isAnalyticsLoading} />
          </div>

          {/* Widgets Grid - Responsive */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <AIInsights status={dashboardData?.ai_status} />
            <AlertCenter />
            <QuickTradeForm />

            {/* System Monitoring Status */}
            <Card className="shadow-lg border-0 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {isAgentsLoading ? (
                  <div className="space-y-2">
                    <SkeletonLoader className="h-4 w-full" />
                    <SkeletonLoader className="h-4 w-3/4" />
                    <SkeletonLoader className="h-4 w-1/2" />
                  </div>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(agents).map(([agentName, agent]) => (
                      <div key={agentName} className="flex items-center justify-between">
                        <span className="text-sm font-medium capitalize">
                          {agentName.replace('_', ' ')}
                        </span>
                        <div className="flex items-center gap-2">
                          {agent.active ? (
                            agent.status === 'running' ? (
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                            ) : agent.status === 'error' ? (
                              <XCircle className="w-4 h-4 text-red-600" />
                            ) : (
                              <Clock className="w-4 h-4 text-amber-600" />
                            )
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-slate-400" />
                          )}
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            agent.active
                              ? agent.status === 'running'
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
                                : agent.status === 'error'
                                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                  : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                              : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                          }`}>
                            {agent.active ? agent.status : 'inactive'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {Object.keys(agents).length === 0 && (
                      <div className="text-center text-slate-500 dark:text-slate-400 py-4">
                        <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No agents configured</p>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="holdings" className="space-y-6">
          {/* Holdings Table - Responsive */}
          {isLoading ? (
            <div className="bg-white/80 backdrop-blur-sm border border-gray-200/50 card-shadow rounded-lg overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b border-gray-200/50">
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-4 w-16" />
              </div>
              <SkeletonTable rows={5} columns={6} />
            </div>
          ) : portfolio && portfolio.holdings.length > 0 ? (
            <div className="overflow-x-auto">
              <HoldingsTable holdings={portfolio.holdings} totalExposure={portfolio.exposure_total} />
            </div>
          ) : (
            <Card className="shadow-lg border-0 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <PieChart className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Holdings Found</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                  You don't have any active positions in your portfolio yet.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {/* Analytics Charts and Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="Performance Trend" type="line" data={chartData} isLoading={isAnalyticsLoading} />
            <ChartCard title="Asset Allocation" type="pie" data={allocationData} showLegend isLoading={isAnalyticsLoading} />
          </div>

          {/* Additional Analytics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Portfolio Value"
              value={(portfolio?.cash.free || 0) + (portfolio?.exposure_total || 0)}
              format="currency"
              tooltip="Total value of your portfolio including cash and positions"
            />
            <MetricCard
              label="Concentration Risk"
              value={analytics?.portfolio?.concentration_risk || 0}
              format="percent"
              tooltip="Risk level based on how concentrated your investments are in specific sectors"
            />
            <MetricCard
              label="Dominant Sector"
              value={analytics?.portfolio?.dominant_sector || 'N/A'}
              format="text"
              tooltip="The sector with the largest portion of your portfolio"
            />
            <MetricCard
              label="Total Positions"
              value={portfolio?.holdings.length || 0}
              format="number"
              tooltip="Total number of different securities in your portfolio"
            />
          </div>
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-6">
          {/* AI Insights and Recommendations */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <AIInsights status={dashboardData?.ai_status} />
            <AlertCenter />
            <QuickTradeForm />
          </div>

          {/* Recommendations Section */}
          <Card className="shadow-lg border-0 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                AI Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                AI-powered recommendations will appear here based on your portfolio analysis and market conditions.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}