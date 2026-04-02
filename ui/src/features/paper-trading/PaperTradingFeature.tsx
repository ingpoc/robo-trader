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
import { AnalyzedWatchlistPanel } from './components/AnalyzedWatchlistPanel'
import { AgentReviewPanel } from './components/AgentReviewPanel'
import { PaperTradingAccountBar } from './components/PaperTradingAccountBar'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { RealTimePositionsTable } from './components/RealTimePositionsTable'
import { StageCriteriaPanel } from './components/StageCriteriaPanel'
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { useAgentArtifacts } from './hooks/useAgentArtifacts'
import { getAnalyzedCandidates, getDiscoveryQueueCandidates, getPreferredResearchCandidate } from './lib/candidateLifecycle'
import type {
  AccountOverviewResponse,
  AgentCandidate,
  ClosedTradeResponse,
  OpenPositionResponse,
  PerformanceMetricsResponse,
} from './types'

export interface PaperTradingFeatureProps {
  accounts: Array<{ account_id: string; account_name: string; strategy_type: string }>
  selectedAccountId?: string | null
  onSelectAccount: (accountId: string) => void
  accountOverview: AccountOverviewResponse | null
  openPositions: OpenPositionResponse[]
  closedTrades: ClosedTradeResponse[]
  performanceMetrics: PerformanceMetricsResponse | null
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

  const analyzedCandidates = useMemo(
    () => getAnalyzedCandidates(discovery?.candidates ?? []),
    [discovery?.candidates],
  )
  const discoveryQueueCandidates = useMemo(
    () => getDiscoveryQueueCandidates(discovery?.candidates ?? []),
    [discovery?.candidates],
  )
  const filteredDiscoveryEnvelope = useMemo(() => {
    if (!discovery) return null

    const analyzedSymbols = new Set(analyzedCandidates.map(candidate => candidate.symbol.toUpperCase()))
    const considered = (discovery.considered ?? []).filter(item => {
      const symbol = item.split('·')[0]?.trim().toUpperCase()
      return !analyzedSymbols.has(symbol)
    })

    return {
      ...discovery,
      artifact_count: discoveryQueueCandidates.length,
      candidates: discoveryQueueCandidates,
      considered,
    }
  }, [analyzedCandidates, discovery, discoveryQueueCandidates])

  useEffect(() => {
    const allCandidates = discovery?.candidates ?? []
    if (!allCandidates.length) {
      if (selectedCandidate) {
        setSelectedCandidate(null)
        clearTab('research')
      }
      return
    }

    const selectedFromLatest = selectedCandidate
      ? allCandidates.find(candidate => candidate.candidate_id === selectedCandidate.candidate_id) ?? null
      : null

    if (!selectedFromLatest) {
      const preferredCandidate = getPreferredResearchCandidate(discoveryQueueCandidates) ?? analyzedCandidates[0] ?? null
      if (preferredCandidate) {
        setSelectedCandidate(preferredCandidate)
        clearTab('research')
      }
      return
    }

    if (selectedFromLatest !== selectedCandidate) {
      setSelectedCandidate(selectedFromLatest)
    }
  }, [analyzedCandidates, clearTab, discovery?.candidates, discoveryQueueCandidates, selectedCandidate])

  useEffect(() => {
    if (!research?.loop_summary || !selectedCandidate) return

    const selectedStillFresh = discoveryQueueCandidates.some(
      candidate => candidate.candidate_id === selectedCandidate.candidate_id,
    )
    if (selectedStillFresh) return

    const nextCandidate = getPreferredResearchCandidate(discoveryQueueCandidates)
    if (nextCandidate && nextCandidate.candidate_id !== selectedCandidate.candidate_id) {
      setSelectedCandidate(nextCandidate)
    }
  }, [discoveryQueueCandidates, research?.generated_at, research?.loop_summary, selectedCandidate])

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
          envelope={filteredDiscoveryEnvelope}
          criteria={filteredDiscoveryEnvelope?.criteria ?? []}
          considered={filteredDiscoveryEnvelope?.considered ?? []}
          isActive={artifactsLoading && activeRequest === 'discovery'}
        >
          <AgentDiscoveryPanel
            envelope={filteredDiscoveryEnvelope}
            movedCandidateCount={analyzedCandidates.length}
            isLoading={artifactsLoading && activeRequest === 'discovery'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('discovery') }}
            selectedCandidateId={selectedCandidate?.candidate_id ?? null}
            onSelectCandidate={handleSelectCandidate}
          />
        </StageRow>

        <AnalyzedWatchlistPanel
          candidates={analyzedCandidates}
          selectedCandidateId={selectedCandidate?.candidate_id ?? null}
          onSelectCandidate={handleSelectCandidate}
        />

        <StageRow
          stageLabel="Focused Research"
          envelope={research}
          criteria={research?.criteria ?? []}
          considered={research?.considered ?? []}
          isActive={artifactsLoading && activeRequest === 'research'}
        >
          <AgentResearchPanel
            envelope={research}
            selectedCandidate={selectedCandidate}
            isLoading={artifactsLoading && activeRequest === 'research'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => {
              void runTab('research', selectedCandidate
                ? {
                    candidate_id: selectedCandidate.candidate_id,
                    symbol: selectedCandidate.symbol,
                  }
                : undefined)
            }}
          />
        </StageRow>

        <StageRow
          stageLabel="Decision Review"
          envelope={decisions}
          criteria={decisions?.criteria ?? []}
          considered={decisions?.considered ?? []}
          isActive={artifactsLoading && activeRequest === 'decisions'}
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
          isActive={artifactsLoading && activeRequest === 'review'}
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
  isActive = false,
  children,
}: {
  stageLabel: string
  envelope: {
    status?: string | null
    status_reason?: string | null
    freshness_state?: string | null
    empty_reason?: string | null
  } | null
  criteria: string[]
  considered: string[]
  isActive?: boolean
  children: React.ReactNode
}) {
  return (
    <section className={`desk-stage-row ${isActive ? 'desk-stage-row--active' : ''}`}>
      <div>{children}</div>
      <StageCriteriaPanel
        stageLabel={stageLabel}
        criteria={criteria}
        considered={considered}
        status={envelope?.status ?? null}
        statusReason={envelope?.status_reason ?? null}
        freshnessState={envelope?.freshness_state ?? null}
        emptyReason={envelope?.empty_reason ?? null}
      />
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

export default PaperTradingFeature
