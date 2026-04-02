import React, { useMemo } from 'react'
import { ArrowRight, Clock3, Wallet } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { SkeletonCard, SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAccount } from '@/contexts/AccountContext'

import { useDashboardData } from './hooks/useDashboardData'

export interface DashboardFeatureProps {
  onNavigate?: (path: string) => void
}

type BadgeVariant = 'success' | 'warning' | 'error' | 'secondary'

const statusVariantMap: Record<string, BadgeVariant> = {
  ready: 'success',
  degraded: 'warning',
  blocked: 'error',
  empty: 'warning',
}

export const DashboardFeature: React.FC<DashboardFeatureProps> = ({ onNavigate }) => {
  const navigate = useNavigate()
  const { selectedAccount, accounts, isLoading: isAccountsLoading } = useAccount()
  const { overviewSummary, accountPolicy, error, isLoading, refetch } = useDashboardData({
    accountId: selectedAccount?.account_id ?? null,
  })

  const stageOutputs = overviewSummary?.recent_stage_outputs ?? []
  const workQueueRows = useMemo(() => ([
    { label: 'Unevaluated closed trades', value: String(overviewSummary?.queue.unevaluated_closed_trades ?? 0) },
    { label: 'Queued improvements', value: String(overviewSummary?.queue.queued_promotable_improvements ?? 0) },
    { label: 'Pending decisions', value: String(overviewSummary?.queue.decision_pending_improvements ?? 0) },
    { label: 'Ready-now promotions', value: String(overviewSummary?.queue.ready_now_promotions ?? 0) },
    { label: 'Recent runs', value: String(overviewSummary?.queue.recent_runs ?? 0) },
  ]), [overviewSummary])

  if (isLoading || isAccountsLoading) {
    return (
      <div className="page-wrapper">
        <div className="space-y-4">
          <Breadcrumb items={[{ label: 'Overview' }]} />
          <PageHeader
            title="Overview"
            description="Operator summary for the selected paper account."
          />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
      </div>
    )
  }

  if (!selectedAccount && accounts.length === 0) {
    return (
      <div className="page-wrapper">
        <div className="space-y-4">
          <Breadcrumb items={[{ label: 'Overview' }]} />
          <PageHeader
            title="Overview"
            description="Create or select a paper account to see the operator summary."
          />
        </div>
        <Card className="border-border/70 bg-white/85">
          <CardContent className="space-y-4 p-6">
            <p className="desk-kicker">No account selected</p>
            <p className="text-base font-semibold text-foreground">A paper-trading account is required before the dashboard can show operator state.</p>
            <Button variant="primary" onClick={() => (onNavigate || navigate)('/configuration')}>
              Open Configuration
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="page-wrapper">
      <div className="space-y-4">
        <Breadcrumb items={[{ label: 'Overview' }]} />
        <PageHeader
          title="Overview"
          description="Operating summary only. Runtime truth and readiness live in Health, and policy lives in Configuration."
        />
      </div>

      {error ? (
        <Card className="border-red-300 bg-red-50/80 text-red-900">
          <CardContent className="space-y-4 p-5">
            <p className="text-base font-semibold">Operator overview unavailable</p>
            <p className="text-sm leading-6">{error.message}</p>
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => void refetch()}>Retry overview</Button>
              <Button variant="primary" onClick={() => (onNavigate || navigate)('/health')}>
                Open Health
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
        <Card className="border-border/70 bg-white/85">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-foreground">Immediate blockers and next action</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <p className="desk-kicker">Blocking Issue</p>
              <p className="text-base font-semibold text-foreground">
                {overviewSummary?.readiness.first_blocker ?? 'No blocking issue is active for the selected operator path.'}
              </p>
              <p className="text-sm leading-6 text-muted-foreground">
                Execution mode: {accountPolicy?.execution_mode ?? overviewSummary?.execution_mode ?? 'operator_confirmed_execution'}
              </p>
            </div>
            <div className="space-y-3">
              <p className="desk-kicker">Next Action</p>
              <p className="text-base font-semibold text-foreground">
                {overviewSummary?.next_action.summary ?? 'Continue monitoring readiness and refresh the account snapshot before any mutation.'}
              </p>
              <p className="text-sm leading-6 text-muted-foreground">
                {overviewSummary?.next_action.detail ?? 'The dashboard is showing the current operator recommendation from the live backend state.'}
              </p>
              <Button variant="primary" onClick={() => (onNavigate || navigate)('/paper-trading')}>
                Open Paper Trading
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-white/85">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-foreground">Selected account snapshot</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <DataRow label="Account" value={selectedAccount?.account_name ?? 'None'} />
            <DataRow label="Account ID" value={selectedAccount?.account_id ?? 'None'} />
            <DataRow label="Buying power" value={formatCurrency(overviewSummary?.selected_account.buying_power)} />
            <DataRow label="Deployed capital" value={formatCurrency(overviewSummary?.selected_account.deployed_capital)} />
            <DataRow label="Open positions" value={String(overviewSummary?.selected_account.position_count ?? 0)} />
            <DataRow
              label="Valuation freshness"
              value={overviewSummary?.selected_account.valuation_status ?? 'unknown'}
              detail={overviewSummary?.selected_account.valuation_detail ?? undefined}
            />
            <DataRow label="Mark freshness" value={overviewSummary?.selected_account.mark_freshness ?? 'unknown'} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_1fr]">
        <Card className="border-border/70 bg-white/85">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-foreground">Act now</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(overviewSummary?.act_now?.length ?? 0) > 0 ? (
              overviewSummary?.act_now?.map(item => (
                <div key={`${item.label}-${item.detail}`} className="rounded-2xl border border-border/70 bg-background/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-base font-semibold text-foreground">{item.label}</p>
                    <Badge variant={item.priority === 'high' ? 'error' : 'warning'} size="xs">
                      {item.priority}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.detail}</p>
                </div>
              ))
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                No urgent operator obligation is active for the selected account.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-white/85">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-foreground">Work queue and performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <MetricTile label="Portfolio value" value={formatCurrency(overviewSummary?.performance.portfolio_value)} />
              <MetricTile label="Unrealized P&L" value={formatCurrency(overviewSummary?.performance.unrealized_pnl)} />
              <MetricTile label="Win rate" value={formatPercent(overviewSummary?.performance.win_rate)} />
              <MetricTile label="Closed trades" value={String(overviewSummary?.performance.closed_trades ?? 0)} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {workQueueRows.map(row => (
                <DataRow key={row.label} label={row.label} value={row.value} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-white/85">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-foreground">Guardrails in force</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <DataRow label="Execution mode" value={accountPolicy?.execution_mode ?? overviewSummary?.execution_mode ?? 'operator_confirmed_execution'} />
            <DataRow label="Per-trade exposure" value={`${overviewSummary?.guardrails.per_trade_exposure_pct ?? 0}%`} />
            <DataRow label="Max portfolio risk" value={`${overviewSummary?.guardrails.max_portfolio_risk_pct ?? 0}%`} />
            <DataRow label="Max open positions" value={String(overviewSummary?.guardrails.max_open_positions ?? 0)} />
            <DataRow label="Max new entries / day" value={String(overviewSummary?.guardrails.max_new_entries_per_day ?? 0)} />
            <DataRow label="Max deployed capital" value={`${overviewSummary?.guardrails.max_deployed_capital_pct ?? 0}%`} />
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 bg-white/85">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold text-foreground">Stage outputs in flight</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {stageOutputs.length ? (
            stageOutputs.map(stage => (
              <div key={stage.label} className="rounded-2xl border border-border/70 bg-background/70 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-foreground">{stage.label}</h3>
                  <Badge variant={statusVariantMap[stage.status] ?? 'secondary'} size="xs">
                    {stage.status}
                  </Badge>
                </div>
                <div className="mt-3 grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
                  <div>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {stage.status_reason ?? 'The stage is active for the current account context.'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      Considered {stage.considered_count} candidate{stage.considered_count === 1 ? '' : 's'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock3 className="h-4 w-4" />
                    <span>{formatTimestamp(stage.generated_at ?? null)}</span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm leading-6 text-muted-foreground">No stage output is in flight for the selected paper account.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DataRow({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail?: string
}) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold text-foreground">{value}</p>
      {detail ? <p className="text-sm leading-6 text-muted-foreground">{detail}</p> : null}
    </div>
  )
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{value}</p>
    </div>
  )
}

function formatCurrency(value: number | null | undefined) {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatPercent(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0.0%'
  return `${value.toFixed(1)}%`
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return 'Unavailable'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export default DashboardFeature
