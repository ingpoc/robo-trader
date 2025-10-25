/**
 * Dashboard Data Hook
 * Consolidates portfolio, analytics, and agent data for dashboard
 */

import { usePortfolio } from '@/hooks/usePortfolio'
import { useAnalytics } from '@/hooks/useAnalytics'
import { useAgents } from '@/hooks/useAgents'

export const useDashboardData = () => {
  const { portfolio, analytics: portfolioAnalytics, isLoading, portfolioScan, marketScreening, isScanning } = usePortfolio()
  const { data: performanceData, isLoading: isAnalyticsLoading } = useAnalytics('30d')
  const { agents, isLoading: isAgentsLoading } = useAgents()

  return {
    portfolio,
    analytics: { ...portfolioAnalytics, chart_data: performanceData?.chart_data },
    agents,
    isLoading: isLoading || isAnalyticsLoading || isAgentsLoading,
    portfolioScan,
    marketScreening,
    isScanning,
  }
}
