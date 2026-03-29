/**
 * Paper Trading Feature Component
 * Operator workflow for paper trading, research, and review artifacts.
 */

import React, { useEffect, useMemo, useState } from 'react'
import { Activity, Aperture, ArrowRightLeft, BookOpenText, CandlestickChart, Radar, ScanSearch, Wallet } from 'lucide-react'

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
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { TradingCapabilityCard } from './components/TradingCapabilityCard'
import { useAgentArtifacts } from './hooks/useAgentArtifacts'
import type {
  AccountOverviewResponse,
  AgentCandidate,
  ClosedTradeResponse,
  OpenPositionResponse,
  PerformanceMetricsResponse,
  TradingCapabilitySnapshot,
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

  const totalUnrealizedPnL = useMemo(
    () => openPositions.reduce((sum, position) => sum + position.unrealized_pnl, 0),
    [openPositions],
  )
  const totalUnrealizedPnLPct = accountOverview && accountOverview.balance > 0
    ? (totalUnrealizedPnL / accountOverview.balance) * 100
    : 0

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

      <TradingCapabilityCard snapshot={capabilitySnapshot} isLoading={isLoading} />

      <PaperTradingAccountBar
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        onSelectAccount={onSelectAccount}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

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
          value={formatSignedCurrency(totalUnrealizedPnL)}
          tone={totalUnrealizedPnL >= 0 ? 'positive' : 'negative'}
          detail={`${formatSignedPercent(totalUnrealizedPnLPct)} across ${openPositions.length} open position${openPositions.length === 1 ? '' : 's'}.`}
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

      <section className="grid gap-6 xl:grid-cols-[1.08fr_minmax(0,1fr)]">
        <AgentDiscoveryPanel
          envelope={discovery}
          isLoading={artifactsLoading && activeRequest === 'discovery'}
          error={artifactsError}
          canRun={Boolean(selectedAccountId)}
          onRun={() => { void runTab('discovery') }}
          selectedCandidateId={selectedCandidate?.candidate_id ?? null}
          onSelectCandidate={handleSelectCandidate}
        />

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
      </section>

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

        <div className="space-y-6">
          <DeskSectionHeader
            icon={BookOpenText}
            label="Decision Desk"
            title="Run bounded review only when needed"
            body="Decision review and daily review are explicit actions. They no longer hydrate when you visit the page or switch surfaces."
          />

          <AgentDecisionPanel
            envelope={decisions}
            isLoading={artifactsLoading && activeRequest === 'decisions'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('decisions') }}
          />

          <AgentReviewPanel
            envelope={review}
            isLoading={artifactsLoading && activeRequest === 'review'}
            error={artifactsError}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('review') }}
          />
        </div>
      </section>

      <section className="space-y-4">
        <DeskSectionHeader
          icon={Radar}
          label="Performance"
          title="Outcome statistics"
          body="Use these numbers to judge whether the research loop is improving expectancy, not just generating more text."
        />
        <PerformanceMetrics metrics={performanceMetrics} isLoading={isLoading} />
      </section>
    </div>
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
