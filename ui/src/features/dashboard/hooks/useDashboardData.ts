/**
 * Dashboard Data Hook
 * Consolidates portfolio, analytics, and agent data for dashboard
 */

import { usePortfolio } from '@/hooks/usePortfolio'

export const useDashboardData = () => {
  const {
    portfolio,
    analytics,
    aiStatus,
    alerts,
    isLoading,
  } = usePortfolio()

  return {
    portfolio,
    analytics,
    aiStatus,
    alerts,
    isLoading,
  }
}
