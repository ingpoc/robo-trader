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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <SkeletonCard key={i} className="h-28" style={{ animationDelay: `${i * 50}ms` }} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard className="h-72" />
          <SkeletonCard className="h-72" />
        </div>
        <SkeletonCard className="h-48" />
      </div>
    )
  }

  return (
    <div className="page-wrapper">
      {/* Header Section with Staggered Animation */}
      <div className="flex flex-col gap-6 animate-fade-in-luxury" style={{ animationDelay: '0ms' }}>
        <Breadcrumb />

        {/* Title with Luxury Styling */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div className="flex-1 space-y-3">
            <h1 className="text-5xl lg:text-6xl font-bold text-warmgray-900 dark:text-warmgray-50 font-serif tracking-tight"
                style={{ letterSpacing: '-0.02em' }}>
              Trading Dashboard
            </h1>
            <p className="text-lg text-warmgray-600 dark:text-warmgray-300 font-normal max-w-xl">
              Professional portfolio management powered by AI insights and real-time market data
            </p>
          </div>

          {/* Action Buttons with Luxury Effects */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 lg:pt-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => portfolioScan()}
                  disabled={isScanning}
                  className="font-semibold transition-all duration-300 hover:shadow-lg hover:shadow-copper-500/20 active:scale-95"
                  aria-label="Scan portfolio for updates"
                >
                  <TrendingUp className={`w-5 h-5 mr-2 ${isScanning ? 'animate-spin' : ''}`} />
                  {isScanning ? 'Scanning...' : 'Scan Portfolio'}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh portfolio data and update current positions</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => marketScreening()}
                  disabled={isScanning}
                  className="font-semibold transition-all duration-300 hover:shadow-md"
                  aria-label="Perform market screening"
                >
                  <PieChart className={`w-5 h-5 mr-2 ${isScanning ? 'animate-spin' : ''}`} />
                  Market Screen
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Analyze market data and find opportunities</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Divider with Copper Accent */}
      <div className="h-px bg-gradient-to-r from-transparent via-copper-500/20 to-transparent" />

      {/* Tabs with Refined Styling */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-8 p-1.5 bg-warmgray-100 dark:bg-warmgray-800/50 rounded-xl border border-warmgray-200 dark:border-warmgray-700/50 shadow-sm backdrop-blur-sm">
          <TabsTrigger
            value="overview"
            className="text-sm font-semibold rounded-lg transition-all duration-300 data-[state=active]:bg-white dark:data-[state=active]:bg-warmgray-700 data-[state=active]:shadow-sm data-[state=active]:text-copper-600"
          >
            Overview
          </TabsTrigger>
          <TabsTrigger
            value="holdings"
            className="text-sm font-semibold rounded-lg transition-all duration-300 data-[state=active]:bg-white dark:data-[state=active]:bg-warmgray-700 data-[state=active]:shadow-sm data-[state=active]:text-copper-600"
          >
            Holdings
          </TabsTrigger>
          <TabsTrigger
            value="analytics"
            className="text-sm font-semibold rounded-lg transition-all duration-300 data-[state=active]:bg-white dark:data-[state=active]:bg-warmgray-700 data-[state=active]:shadow-sm data-[state=active]:text-copper-600"
          >
            Analytics
          </TabsTrigger>
          <TabsTrigger
            value="insights"
            className="text-sm font-semibold rounded-lg transition-all duration-300 data-[state=active]:bg-white dark:data-[state=active]:bg-warmgray-700 data-[state=active]:shadow-sm data-[state=active]:text-copper-600"
          >
            AI Insights
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-8 animate-slide-in-up-luxury">
          <div style={{ animationDelay: '100ms' }}>
            <MetricsGrid portfolio={portfolio} analytics={analytics} />
          </div>
          <div style={{ animationDelay: '200ms' }}>
            <PerformanceCharts analytics={analytics} portfolio={portfolio} />
          </div>
          <div style={{ animationDelay: '300ms' }}>
            <AlertsSummary />
          </div>
        </TabsContent>

        {/* Holdings Tab */}
        <TabsContent value="holdings" className="space-y-8 animate-slide-in-up-luxury">
          <div style={{ animationDelay: '100ms' }}>
            <PortfolioOverview portfolio={portfolio} detailed />
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-8 animate-slide-in-up-luxury">
          <div style={{ animationDelay: '100ms' }}>
            <PerformanceCharts analytics={analytics} portfolio={portfolio} detailed />
          </div>
        </TabsContent>

        {/* Insights Tab */}
        <TabsContent value="insights" className="space-y-8 animate-slide-in-up-luxury">
          <div style={{ animationDelay: '100ms' }}>
            <AIInsightsSummary onNavigate={onNavigate} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default DashboardFeature
