/**
 * Dashboard Feature
 * Main trading dashboard with portfolio overview, metrics, and performance analytics
 */

import React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/Button'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { TrendingUp, PieChart } from 'lucide-react'
import { useDashboardData } from './hooks/useDashboardData'
import { MetricsGrid } from './components/MetricsGrid'
import { PerformanceCharts } from './components/PerformanceCharts'
import { PortfolioOverview } from './components/PortfolioOverview'
import { AIInsightsSummary } from './components/AIInsightsSummary'
import { AlertsSummary } from './components/AlertsSummary'

export interface DashboardFeatureProps {
  onNavigate?: (path: string) => void
}

export const DashboardFeature: React.FC<DashboardFeatureProps> = ({ onNavigate }) => {
  const { portfolio, analytics, isLoading, portfolioScan, marketScreening, isScanning } = useDashboardData()

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 lg:gap-8 p-4 lg:p-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <SkeletonLoader className="h-8 w-48" />
          <div className="flex gap-2">
            <SkeletonLoader className="h-8 w-16" />
            <SkeletonLoader className="h-8 w-20" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} className="h-24" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SkeletonCard className="h-64" />
          <SkeletonCard className="h-64" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-48" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4 animate-fade-in-luxury">
        <Breadcrumb />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 px-4 lg:px-6">
          <div className="space-y-2">
            <h1 className="text-4xl lg:text-5xl font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">
              Trading Dashboard
            </h1>
            <p className="text-lg text-warmgray-600 dark:text-warmgray-400">
              Professional portfolio management with AI-powered insights
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => portfolioScan()}
                  disabled={isScanning}
                  className="font-semibold"
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
                  className="font-semibold"
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
        <TabsList className="grid w-full grid-cols-4 mb-6 p-1.5 bg-warmgray-100 dark:bg-warmgray-800 rounded-lg border border-warmgray-300 dark:border-warmgray-700 shadow-sm">
          <TabsTrigger value="overview" className="text-sm font-semibold rounded-md">
            Overview
          </TabsTrigger>
          <TabsTrigger value="holdings" className="text-sm font-semibold rounded-md">
            Holdings
          </TabsTrigger>
          <TabsTrigger value="analytics" className="text-sm font-semibold rounded-md">
            Analytics
          </TabsTrigger>
          <TabsTrigger value="insights" className="text-sm font-semibold rounded-md">
            AI Insights
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <MetricsGrid portfolio={portfolio} analytics={analytics} />
          <PerformanceCharts analytics={analytics} portfolio={portfolio} />
          <PortfolioOverview portfolio={portfolio} />
          <AlertsSummary />
        </TabsContent>

        <TabsContent value="holdings" className="space-y-6">
          <PortfolioOverview portfolio={portfolio} detailed />
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <PerformanceCharts analytics={analytics} portfolio={portfolio} detailed />
        </TabsContent>

        <TabsContent value="insights" className="space-y-6">
          <AIInsightsSummary onNavigate={onNavigate} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default DashboardFeature
