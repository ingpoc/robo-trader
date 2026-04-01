/**
 * Paper Trading Feature Component
 * Operator workflow for paper trading, research, and review artifacts.
 */

import React, { useEffect, useMemo, useState } from 'react'
import { Activity, Aperture, ArrowRightLeft, CandlestickChart, Radar, Wallet } from 'lucide-react'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent } from '@/components/ui/Card'

import { AgentDecisionPanel } from './components/AgentDecisionPanel'
import { AgentDiscoveryPanel } from './components/AgentDiscoveryPanel'
import { AgentResearchPanel } from './components/AgentResearchPanel'
import { AgentReviewPanel } from './components/AgentReviewPanel'
import { PaperTradingAccountBar } from './components/PaperTradingAccountBar'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { RealTimePositionsTable } from './components/RealTimePositionsTable'
import { StageCriteriaPanel } from './components/StageCriteriaPanel'
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { TradingCapabilityCard } from './components/TradingCapabilityCard'
import { useAgentArtifacts } from './hooks/useAgentArtifacts'
import type {
  AccountOverviewResponse,
  AgentCandidate,
  ClosedTradeResponse,
  OpenPositionResponse,
  PerformanceMetricsResponse,
  RuntimeHealthResponse,
  RuntimeIdentity,
  TradingCapabilitySnapshot,
  WebMCPReadiness,
} from './types'

export interface PaperTradingFeatureProps {
  accounts: Array<{ account_id: string; account_name: string; strategy_type: string }>
  selectedAccountId?: string | null
  onSelectAccount: (accountId: string) => void
  accountOverview: AccountOverviewResponse | null
  openPositions: OpenPositionResponse[]
  closedTrades: ClosedTradeResponse[]
  performanceMetrics: PerformanceMetricsResponse | null
  capabilitySnapshot: TradingCapabilitySnapshot | null
  runtimeHealth: RuntimeHealthResponse | null
  frontendRuntimeIdentity: RuntimeIdentity
  webmcpReadiness: WebMCPReadiness
  dataError?: string | null
  performanceError?: string | null
  onRefresh: () => Promise<void>
  isLoading?: boolean
}

export const PaperTradingFeature: React.FC<PaperTradingFeatureProps> = ({
  accounts,
  selectedAccountId,
  onSelectAccount,
  accountOverview,
  openPositions,
  closedTrades,
  performanceMetrics,
  capabilitySnapshot,
  runtimeHealth,
  frontendRuntimeIdentity,
  webmcpReadiness,
  dataError = null,
  performanceError = null,
  onRefresh,
  isLoading = false,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState<AgentCandidate | null>(null)
  const artifactHookOptions = useMemo(() => ({ onRunComplete: onRefresh }), [onRefresh])

  const {
    discovery,
    research,
    decisions,
    review,
    isLoading: artifactsLoading,
    activeRequest,
    error: artifactsError,
    clearTab,
    runTab,
  } = useAgentArtifacts(selectedAccountId ?? undefined, selectedCandidate, artifactHookOptions)

  useEffect(() => {
    setSelectedCandidate(null)
    clearTab('research')
  }, [selectedAccountId, clearTab])

  useEffect(() => {
    if (!selectedCandidate && discovery?.candidates.length) {
      setSelectedCandidate(discovery.candidates[0])
      clearTab('research')
    }
  }, [clearTab, discovery, selectedCandidate])

  const valuedPositions = useMemo(
    () => openPositions.filter((position) => position.unrealized_pnl != null),
    [openPositions],
  )
  const totalUnrealizedPnL = useMemo(
    () => valuedPositions.reduce((sum, position) => sum + (position.unrealized_pnl ?? 0), 0),
    [valuedPositions],
  )
  const hasUnavailableValuation = valuedPositions.length !== openPositions.length
  const livePnlValue = valuedPositions.length > 0 ? formatSignedCurrency(totalUnrealizedPnL) : 'Unavailable'
  const livePnlDetail = hasUnavailableValuation
    ? (
      accountOverview?.valuation_detail
      ?? `${valuedPositions.length} of ${openPositions.length} open position${openPositions.length === 1 ? '' : 's'} currently have live valuation.`
    )
    : (
      accountOverview && accountOverview.balance > 0
        ? `${formatSignedPercent((totalUnrealizedPnL / accountOverview.balance) * 100)} across ${openPositions.length} open position${openPositions.length === 1 ? '' : 's'}.`
        : `Across ${openPositions.length} open position${openPositions.length === 1 ? '' : 's'}.`
    )

  const strategyLabel = accounts.find(account => account.account_id === selectedAccountId)?.strategy_type || 'paper'

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleSelectCandidate = (candidate: AgentCandidate) => {
    setSelectedCandidate(candidate)
    clearTab('research')
  }

  return (
    <div className="page-wrapper paper-trading-shell">
      <div className="flex flex-col gap-5">
        <Breadcrumb />

        <PageHeader
          title="Paper Trading"
          description="Run the loop deliberately: verify readiness, stage dark-horse candidates, then spend tokens only on explicit research and review actions."
        />
      </div>

      <TradingCapabilityCard snapshot={capabilitySnapshot} webmcpReadiness={webmcpReadiness} isLoading={isLoading} />

      <RuntimeIdentityPanel
        runtimeHealth={runtimeHealth}
        frontendRuntimeIdentity={frontendRuntimeIdentity}
        selectedAccountId={selectedAccountId ?? null}
        latestDiscoveryAt={discovery?.generated_at ?? null}
      />

      <AutonomyBoundaryPanel />

      <PaperTradingAccountBar
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        onSelectAccount={onSelectAccount}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {dataError ? (
        <Card className="border-red-300 bg-red-50/80 text-red-900">
          <CardContent className="p-4 text-sm font-medium">
            Live paper-trading data is unavailable. {dataError}
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !selectedAccountId ? (
        <div className="desk-panel p-6">
          <p className="desk-kicker">Operator Gate</p>
          <h2 className="desk-heading mt-2">No paper-trading account selected</h2>
          <p className="desk-copy mt-3 max-w-2xl">
            Select an account before running discovery, research, decisions, or review. The workflow is explicit by design so every artifact stays tied to one account state.
          </p>
        </div>
      ) : null}

      <section className="desk-strip">
        <MetricCell
          icon={Wallet}
          label="Balance"
          value={formatCurrency(accountOverview?.balance)}
          detail={accountOverview ? 'Capital in play for the selected paper account.' : 'Awaiting account data.'}
        />
        <MetricCell
          icon={ArrowRightLeft}
          label="Deployed"
          value={formatCurrency(accountOverview?.deployed_capital)}
          detail={accountOverview ? 'Capital currently committed to open paper positions.' : 'Awaiting position ledger.'}
        />
        <MetricCell
          icon={Activity}
          label="Live P&L"
          value={livePnlValue}
          tone={hasUnavailableValuation ? 'neutral' : totalUnrealizedPnL >= 0 ? 'positive' : 'negative'}
          detail={livePnlDetail}
        />
        <MetricCell
          icon={CandlestickChart}
          label="Closed Trades"
          value={closedTrades.length.toString()}
          detail={
            typeof performanceMetrics?.win_rate === 'number'
              ? `${performanceMetrics.win_rate.toFixed(1)}% win rate · ${strategyLabel}`
              : `Strategy: ${strategyLabel}`
          }
        />
      </section>

      <div className="space-y-6">
        <StageRow
          stageLabel="Discovery"
          envelope={discovery}
          criteria={discovery?.criteria ?? []}
          considered={discovery?.considered ?? []}
        >
          <AgentDiscoveryPanel
            envelope={discovery}
            isLoading={artifactsLoading && activeRequest === 'discovery'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('discovery') }}
            selectedCandidateId={selectedCandidate?.candidate_id ?? null}
            onSelectCandidate={handleSelectCandidate}
          />
        </StageRow>

        <StageRow
          stageLabel="Focused Research"
          envelope={research}
          criteria={research?.criteria ?? []}
          considered={research?.considered ?? []}
        >
          <AgentResearchPanel
            envelope={research}
            selectedCandidate={selectedCandidate}
            isLoading={artifactsLoading && activeRequest === 'research'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId && selectedCandidate)}
            onRun={() => {
              if (!selectedCandidate) return
              void runTab('research', {
                candidate_id: selectedCandidate.candidate_id,
                symbol: selectedCandidate.symbol,
              })
            }}
          />
        </StageRow>

        <StageRow
          stageLabel="Decision Review"
          envelope={decisions}
          criteria={decisions?.criteria ?? []}
          considered={decisions?.considered ?? []}
        >
          <AgentDecisionPanel
            envelope={decisions}
            isLoading={artifactsLoading && activeRequest === 'decisions'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('decisions') }}
          />
        </StageRow>

        <StageRow
          stageLabel="Daily Review"
          envelope={review}
          criteria={review?.criteria ?? []}
          considered={review?.considered ?? []}
        >
          <AgentReviewPanel
            envelope={review}
            isLoading={artifactsLoading && activeRequest === 'review'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('review') }}
          />
        </StageRow>
      </div>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="space-y-6">
          <DeskSectionHeader
            icon={Aperture}
            label="Position Desk"
            title="Live exposure and mark-to-market"
            body="Execution remains deterministic. This surface is for operator truth: open exposure, stale marks, and realized history."
          />
          <RealTimePositionsTable positions={openPositions} isLoading={isLoading} />
          <TradeHistoryTable trades={closedTrades} isLoading={isLoading} />
        </div>

        <section className="space-y-4">
          <DeskSectionHeader
            icon={Radar}
            label="Performance"
            title="Outcome statistics"
            body="Use these numbers to judge whether the research loop is improving expectancy, not just generating more text."
          />
          <PerformanceMetrics metrics={performanceMetrics} error={performanceError} isLoading={isLoading} />
        </section>
      </section>
    </div>
  )
}

function StageRow({
  stageLabel,
  envelope,
  criteria,
  considered,
  children,
}: {
  stageLabel: string
  envelope: { status?: string | null; status_reason?: string | null } | null
  criteria: string[]
  considered: string[]
  children: React.ReactNode
}) {
  return (
    <section className="desk-stage-row">
      <div>{children}</div>
      <StageCriteriaPanel
        stageLabel={stageLabel}
        criteria={criteria}
        considered={considered}
        status={envelope?.status ?? null}
        statusReason={envelope?.status_reason ?? null}
      />
    </section>
  )
}

function RuntimeIdentityPanel({
  runtimeHealth,
  frontendRuntimeIdentity,
  selectedAccountId,
  latestDiscoveryAt,
}: {
  runtimeHealth: RuntimeHealthResponse | null
  frontendRuntimeIdentity: RuntimeIdentity
  selectedAccountId: string | null
  latestDiscoveryAt: string | null
}) {
  const backendRuntimeIdentity = runtimeHealth?.runtime_identity ?? null
  const isStaleBackend = Boolean(
    backendRuntimeIdentity?.git_sha
    && frontendRuntimeIdentity.git_sha
    && backendRuntimeIdentity.git_sha !== frontendRuntimeIdentity.git_sha,
  )
  const bannerTone = isStaleBackend
    ? 'border-amber-300 bg-amber-50/80 text-amber-950'
    : 'border-emerald-200 bg-emerald-50/70 text-emerald-950'
  const heading = isStaleBackend ? 'Stale runtime detected' : 'Runtime identity in sync'
  const summary = isStaleBackend
    ? 'The frontend and backend are serving different git revisions. Refreshing data may still hit an older backend lane until it is restarted.'
    : 'The operator page is talking to the current backend revision, so discovery and readiness state should reflect current code.'

  return (
    <Card className={bannerTone}>
      <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.2fr_0.8fr_0.8fr]">
        <div className="space-y-2">
          <p className="desk-kicker">Runtime Truth</p>
          <h2 className="desk-heading">{heading}</h2>
          <p className="desk-copy max-w-2xl">{summary}</p>
        </div>

        <div className="space-y-2 text-sm">
          <p className="desk-kicker">Frontend</p>
          <p className="font-semibold">
            {frontendRuntimeIdentity.git_short_sha ?? 'unknown'} · {formatRuntimeTimestamp(frontendRuntimeIdentity.started_at)}
          </p>
          <p className="text-muted-foreground">{frontendRuntimeIdentity.build_id}</p>
        </div>

        <div className="space-y-2 text-sm">
          <p className="desk-kicker">Backend</p>
          {backendRuntimeIdentity ? (
            <>
              <p className="font-semibold">
                {backendRuntimeIdentity.git_short_sha ?? 'unknown'} · {formatRuntimeTimestamp(backendRuntimeIdentity.started_at)}
              </p>
              <p className="text-muted-foreground">{backendRuntimeIdentity.build_id}</p>
            </>
          ) : (
            <p className="text-muted-foreground">Health endpoint unavailable. Refresh runtime truth before trusting the dashboard.</p>
          )}
        </div>

        <div className="space-y-2 text-sm lg:col-span-3">
          <p className="desk-kicker">Operator Context</p>
          <p className="text-muted-foreground">
            Account: <span className="font-medium text-foreground">{selectedAccountId ?? 'none selected'}</span>
            {' · '}
            Discovery envelope: <span className="font-medium text-foreground">{latestDiscoveryAt ? formatRuntimeTimestamp(latestDiscoveryAt) : 'not loaded yet'}</span>
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

function AutonomyBoundaryPanel() {
  return (
    <section className="desk-autonomy-panel">
      <div className="space-y-2">
        <p className="desk-kicker">Autonomy Boundary</p>
        <h2 className="desk-heading">What I can run end to end right now</h2>
        <p className="desk-copy max-w-4xl">
          The dashboard is agent-operator ready for discovery, focused research, decision review, daily review, and dry-run proposal work. Autonomous paper entry is still blocked until the repo-local go-live checklist evidence window is satisfied and the execution posture is explicitly promoted in code.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Autonomous Now</p>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-emerald-900">
            <li>Operate the dashboard through WebMCP.</li>
            <li>Run discovery and stage candidates for research.</li>
            <li>Generate focused research, decision packets, and daily reviews.</li>
            <li>Run dry-run proposal and preflight checks before any paper order.</li>
          </ul>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Still Blocked</p>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-900">
            <li>Unattended autonomous paper entries.</li>
            <li>Any execution path that bypasses proposal, preflight, or operator confirmation.</li>
            <li>Strategy promotion based only on intuition instead of outcome or benchmark evidence.</li>
            <li>Claiming a `GO` posture before the evidence window in the go-live checklist is met.</li>
          </ul>
        </div>
      </div>
    </section>
  )
}

function DeskSectionHeader({
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
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <p className="desk-kicker">{label}</p>
      </div>
      <h2 className="desk-heading">{title}</h2>
      <p className="desk-copy max-w-3xl">{body}</p>
    </div>
  )
}

function MetricCell({
  icon: Icon,
  label,
  value,
  detail,
  tone = 'neutral',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  detail: string
  tone?: 'positive' | 'negative' | 'neutral'
}) {
  return (
    <div className="desk-strip-cell">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="desk-kicker">{label}</p>
          <p className={`desk-metric ${tone === 'positive' ? 'text-emerald-700' : tone === 'negative' ? 'text-rose-700' : ''}`}>
            {value}
          </p>
          <p className="text-sm leading-6 text-muted-foreground">{detail}</p>
        </div>
        <Icon className="mt-1 h-4 w-4 text-primary" />
      </div>
    </div>
  )
}

function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function formatSignedCurrency(value?: number | null) {
  const amount = value ?? 0
  return `${amount >= 0 ? '+' : '-'}${formatCurrency(Math.abs(amount)).replace('₹', '₹')}`
}

function formatSignedPercent(value?: number | null) {
  const amount = value ?? 0
  return `${amount >= 0 ? '+' : ''}${amount.toFixed(2)}%`
}

function formatRuntimeTimestamp(value?: string | null) {
  if (!value) return 'unknown'

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value

  return parsed.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default PaperTradingFeature
