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
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Activity, CheckCircle, XCircle, Clock, AlertTriangle, TrendingUp, PieChart } from 'lucide-react'
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
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto bg-warmgray-50 min-h-screen">
      <div className="flex flex-col gap-4 animate-fade-in-luxury">
        <Breadcrumb />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl lg:text-4xl font-bold text-warmgray-900 font-serif">
              Trading Dashboard
            </h1>
            <p className="text-lg text-warmgray-600">Professional portfolio management with AI-powered insights</p>
          </div>
          <div className="flex gap-4">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => portfolioScan()}
                  disabled={isScanning}
                  className="btn-professional-secondary hover:scale-105 transition-all duration-200 font-semibold"
                  aria-label="Scan portfolio for updates"
                >
                  <TrendingUp className="w-5 h-5 mr-2" />
                  Scan Portfolio
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh portfolio data and update current positions and values</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => marketScreening()}
                  disabled={isScanning}
                  className="btn-professional-secondary hover:scale-105 transition-all duration-200 font-semibold"
                  aria-label="Perform market screening"
                >
                  <PieChart className="w-5 h-5 mr-2" />
                  Market Screen
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Analyze market data and identify potential investment opportunities</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-6 p-1 bg-warmgray-200 rounded-xl border border-warmgray-300/50 shadow-sm">
          <TabsTrigger value="overview" className="text-sm font-medium rounded-lg data-[state=active]:bg-white/90 data-[state=active]:text-warmgray-900 data-[state=active]:shadow-md transition-all duration-200 text-warmgray-600 hover:text-warmgray-900">Overview</TabsTrigger>
          <TabsTrigger value="holdings" className="text-sm font-medium rounded-lg data-[state=active]:bg-white/90 data-[state=active]:text-warmgray-900 data-[state=active]:shadow-md transition-all duration-200 text-warmgray-600 hover:text-warmgray-900">Holdings</TabsTrigger>
          <TabsTrigger value="analytics" className="text-sm font-medium rounded-lg data-[state=active]:bg-white/90 data-[state=active]:text-warmgray-900 data-[state=active]:shadow-md transition-all duration-200 text-warmgray-600 hover:text-warmgray-900">Analytics</TabsTrigger>
          <TabsTrigger value="recommendations" className="text-sm font-medium rounded-lg data-[state=active]:bg-white/90 data-[state=active]:text-warmgray-900 data-[state=active]:shadow-md transition-all duration-200 text-warmgray-600 hover:text-warmgray-900">AI Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Hero Metrics - Professional Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-in-up">
            <MetricCard
              label="Available Cash"
              value={portfolio?.cash.free || 0}
              format="currency"
              icon="dollar"
              variant="hero"
              tooltip="The amount of cash available for trading and investments"
            />
            <MetricCard
              label="Total Exposure"
              value={portfolio?.exposure_total || 0}
              format="currency"
              icon="pie"
              variant="hero"
              tooltip="Total market value of all your current positions"
            />
            <MetricCard
              label="Active Positions"
              value={portfolio?.holdings.length || 0}
              format="number"
              icon="users"
              variant="hero"
              tooltip="Number of different securities you currently hold"
            />
            <MetricCard
              label="Risk Score"
              value={analytics?.portfolio?.concentration_risk || 0}
              format="percent"
              icon="alert"
              variant="hero"
              changeLabel={analytics?.portfolio?.dominant_sector}
              tooltip="Portfolio concentration risk based on sector allocation"
            />
          </div>

          {/* Charts Grid - Responsive */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="Performance Trend" type="line" data={chartData} isLoading={isAnalyticsLoading} />
            <ChartCard title="Asset Allocation" type="pie" data={allocationData} showLegend isLoading={isAnalyticsLoading} />
          </div>

          {/* Professional Widgets Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4 animate-slide-in-right">
            <AIInsights status={dashboardData?.ai_status} />
            <AlertCenter />
            <QuickTradeForm />

            {/* System Monitoring Status - Professional */}
            <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm hover:shadow-professional-hover transition-all duration-300 ring-1 ring-copper-100/50">
              <CardHeader className="pb-4">
                <CardTitle className="text-xl flex items-center gap-3 font-bold">
                  <div className="p-3 bg-gradient-to-br from-copper-100 to-copper-200 rounded-xl shadow-sm">
                    <Activity className="w-6 h-6 text-copper-700" />
                  </div>
                  <span className="bg-gradient-to-r from-copper-700 to-copper-600 bg-clip-text text-transparent">
                    System Status
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {isAgentsLoading ? (
                  <div className="space-y-3">
                    <SkeletonLoader className="h-4 w-full" />
                    <SkeletonLoader className="h-4 w-3/4" />
                    <SkeletonLoader className="h-4 w-1/2" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(agents).map(([agentName, agent]) => (
                      <div key={agentName} className="flex items-center justify-between p-4 bg-gradient-to-r from-warmgray-50/80 to-warmgray-100/60 rounded-xl border border-warmgray-300/50 hover:shadow-md transition-all duration-200">
                        <span className="text-sm font-bold capitalize text-warmgray-800">
                          {agentName.replace('_', ' ')}
                        </span>
                        <div className="flex items-center gap-3">
                          {agent.active ? (
                            agent.status === 'running' ? (
                              <CheckCircle className="w-5 h-5 text-emerald-600 animate-pulse" />
                            ) : agent.status === 'error' ? (
                              <XCircle className="w-5 h-5 text-rose-600" />
                            ) : (
                              <Clock className="w-5 h-5 text-amber-600 animate-pulse" />
                            )
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-warmgray-400" />
                          )}
                          <span className={`text-xs px-3 py-1.5 rounded-full font-bold ${
                            agent.active
                              ? agent.status === 'running'
                                ? 'status-online'
                                : agent.status === 'error'
                                  ? 'status-error'
                                  : 'status-warning'
                                : 'status-offline'
                          }`}>
                            {agent.active ? agent.status : 'inactive'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {Object.keys(agents).length === 0 && (
                      <div className="text-center text-slate-500 py-8">
                        <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p className="text-sm font-bold">No agents configured</p>
                        <p className="text-xs text-slate-400 mt-1">Configure agents to get started</p>
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
            <div className="bg-white/80 backdrop-blur-sm border border-warmgray-300/50 card-shadow rounded-lg overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b border-warmgray-300/50">
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-4 w-16" />
              </div>
              <SkeletonTable rows={5} columns={6} />
            </div>
          ) : portfolio && portfolio.holdings.length > 0 ? (
            <div className="overflow-x-auto animate-scale-in">
              <HoldingsTable holdings={portfolio.holdings} totalExposure={portfolio.exposure_total} />
            </div>
          ) : (
            <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-warmgray-50/70 backdrop-blur-sm ring-1 ring-warmgray-300/50 animate-scale-in">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="p-4 bg-gradient-to-br from-warmgray-100 to-warmgray-200 rounded-full mb-6">
                  <PieChart className="w-12 h-12 text-warmgray-600" />
                </div>
                <h3 className="text-xl font-bold text-warmgray-900 mb-3">No Holdings Found</h3>
                <p className="text-sm text-warmgray-600 text-center max-w-md leading-relaxed">
                  You don't have any active positions in your portfolio yet. Start trading to see your holdings here.
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

          {/* AI Recommendations Section */}
          <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm ring-1 ring-copper-100/50 animate-scale-in">
            <CardHeader>
              <CardTitle className="text-xl flex items-center gap-3 font-bold">
                <div className="p-2 bg-gradient-to-br from-copper-100 to-copper-200 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-copper-700" />
                </div>
                <span className="bg-gradient-to-r from-copper-700 to-copper-600 bg-clip-text text-transparent">
                  AI Recommendations
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-warmgray-600 leading-relaxed">
                  AI-powered recommendations will appear here based on your portfolio analysis and market conditions.
                </p>
                <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-emerald-50/80 to-emerald-50/80 rounded-xl border border-emerald-200/50">
                  <div className="p-2 bg-gradient-to-br from-emerald-100 to-emerald-200 rounded-lg">
                    <Activity className="w-4 h-4 text-emerald-700" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-bold text-emerald-800">AI Analysis Active</div>
                    <div className="text-xs text-emerald-600">Monitoring market conditions and portfolio performance</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}