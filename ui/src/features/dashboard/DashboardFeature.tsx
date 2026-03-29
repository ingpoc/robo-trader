/**
 * Dashboard Feature
 * Thin operator summary aligned to the paper-trading workflow.
 */

import React from 'react'
import { ArrowRight, Aperture, Compass, Wallet } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAccount } from '@/contexts/AccountContext'

import { AlertsSummary } from './components/AlertsSummary'
import { MetricsGrid } from './components/MetricsGrid'
import { PortfolioOverview } from './components/PortfolioOverview'
import { useDashboardData } from './hooks/useDashboardData'

export interface DashboardFeatureProps {
  onNavigate?: (path: string) => void
}

export const DashboardFeature: React.FC<DashboardFeatureProps> = ({ onNavigate }) => {
  const navigate = useNavigate()
  const { selectedAccount } = useAccount()
  const { portfolio, analytics, isLoading } = useDashboardData()

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
          description="A quiet operating summary for capital, active blockers, and the next manual actions. AI research no longer runs from the dashboard."
        />
      </div>

      <Card className="overflow-hidden border-border/70 bg-white/80 dark:bg-warmgray-800/80">
        <CardContent className="grid gap-0 p-0 md:grid-cols-[1.2fr_0.9fr_0.9fr_auto]">
          <WorkflowCell
            icon={Compass}
            label="Workflow"
            title="Manual by default"
            body="Discovery, focused research, decision review, and daily review now run only from explicit operator clicks in Paper Trading."
          />
          <WorkflowCell
            icon={Wallet}
            label="Selected Account"
            title={selectedAccount?.account_name || 'No account selected'}
            body={selectedAccount?.account_id || 'Choose an account in Paper Trading before running discovery or research.'}
          />
          <WorkflowCell
            icon={Aperture}
            label="Research Policy"
            title="No background artifacts"
            body="The overview page no longer hydrates discovery, research, decision, or review artifacts behind the scenes."
          />
          <div className="flex items-center justify-start border-t border-border/70 px-6 py-5 md:justify-end md:border-l md:border-t-0">
            <Button variant="primary" onClick={() => (onNavigate || navigate)('/paper-trading')}>
              Open Paper Trading
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <MetricsGrid portfolio={portfolio} analytics={analytics} />

      <AlertsSummary />

      <PortfolioOverview portfolio={portfolio} />
    </div>
  )
}

function WorkflowCell({
  icon: Icon,
  label,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  title: string
  body: string
}) {
  return (
    <div className="border-t border-border/70 px-6 py-5 first:border-t-0 md:border-l md:first:border-l-0 md:border-t-0">
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 text-primary" />
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
          <p className="text-base font-semibold text-foreground">{title}</p>
          <p className="text-sm leading-6 text-muted-foreground">{body}</p>
        </div>
      </div>
    </div>
  )
}

export default DashboardFeature
