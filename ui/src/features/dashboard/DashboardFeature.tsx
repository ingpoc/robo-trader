/**
 * Dashboard Feature
 * Thin operator summary aligned to the paper-trading workflow.
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAccount } from '@/contexts/AccountContext'

import { AlertsSummary } from './components/AlertsSummary'
import { ArtifactSummaryGrid } from './components/ArtifactSummaryGrid'
import { MetricsGrid } from './components/MetricsGrid'
import { PortfolioOverview } from './components/PortfolioOverview'
import { useDashboardData } from './hooks/useDashboardData'
import { useOverviewArtifacts } from './hooks/useOverviewArtifacts'

export interface DashboardFeatureProps {
  onNavigate?: (path: string) => void
}

export const DashboardFeature: React.FC<DashboardFeatureProps> = ({ onNavigate }) => {
  const navigate = useNavigate()
  const { selectedAccount } = useAccount()
  const { portfolio, analytics, isLoading } = useDashboardData()
  const {
    discovery,
    research,
    decisions,
    review,
    isLoading: artifactsLoading,
    error: artifactsError,
  } = useOverviewArtifacts(selectedAccount?.account_id ?? null)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-6">
        <SkeletonLoader className="h-8 w-48" />
        <SkeletonCard className="h-32" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonCard key={index} className="h-28" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonCard key={index} className="h-44" />
          ))}
        </div>
        <SkeletonCard className="h-72" />
      </div>
    )
  }

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-6">
        <Breadcrumb />

        <PageHeader
          title="Overview"
          description="A thin operator summary for paper-trading capital, active blockers, and the latest agent artifacts."
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Selected Paper Account</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Account</p>
            <p className="text-sm font-medium text-foreground">
              {selectedAccount?.account_name || 'No account selected'}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Strategy</p>
            <p className="text-sm font-medium text-foreground">
              {selectedAccount?.strategy_type || 'Unassigned'}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Account ID</p>
            <p className="text-sm font-medium text-foreground">
              {selectedAccount?.account_id || 'Select an account in Paper Trading'}
            </p>
          </div>
        </CardContent>
      </Card>

      <MetricsGrid portfolio={portfolio} analytics={analytics} />

      <ArtifactSummaryGrid
        accountLabel={selectedAccount?.account_name}
        discovery={discovery}
        research={research}
        decisions={decisions}
        review={review}
        isLoading={artifactsLoading}
        error={artifactsError}
        onOpenPaperTrading={() => (onNavigate || navigate)('/paper-trading')}
      />

      <AlertsSummary />

      <PortfolioOverview portfolio={portfolio} />
    </div>
  )
}

export default DashboardFeature
