/**
 * Paper Trading Feature Component
 * Operator workflow for paper trading, research, and review artifacts.
 */

import React, { useEffect, useState } from 'react'
import {
  BarChart3,
  ClipboardList,
  Eye,
  FileSearch,
  History,
  Newspaper,
  TrendingUp,
} from 'lucide-react'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { AccountStatusCard } from './components/AccountStatusCard'
import { AgentDecisionPanel } from './components/AgentDecisionPanel'
import { AgentDiscoveryPanel } from './components/AgentDiscoveryPanel'
import { AgentResearchPanel } from './components/AgentResearchPanel'
import { AgentReviewPanel } from './components/AgentReviewPanel'
import { PaperTradingAccountBar } from './components/PaperTradingAccountBar'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { RealTimePositionsTable } from './components/RealTimePositionsTable'
import { TradeHistoryTable } from './components/TradeHistoryTable'
import { TradingCapabilityCard } from './components/TradingCapabilityCard'
import { UnrealizedPnLCard } from './components/UnrealizedPnLCard'
import { useAgentArtifacts } from './hooks/useAgentArtifacts'
import type {
  AccountOverviewResponse,
  AgentCandidate,
  ClosedTradeResponse,
  OpenPositionResponse,
  PerformanceMetricsResponse,
  TradingCapabilitySnapshot,
} from './types'

type PaperTradingTab = 'overview' | 'discovery' | 'research' | 'decisions' | 'positions' | 'history' | 'review'

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
  const [activeTab, setActiveTab] = useState<PaperTradingTab>('overview')
  const [selectedCandidate, setSelectedCandidate] = useState<AgentCandidate | null>(null)
  const {
    discovery,
    research,
    decisions,
    review,
    isLoading: artifactsLoading,
    error: artifactsError,
    runTab,
  } = useAgentArtifacts(
    selectedAccountId ?? undefined,
    activeTab === 'discovery' || activeTab === 'research' || activeTab === 'decisions' || activeTab === 'review'
      ? activeTab
      : undefined,
    selectedCandidate,
  )

  useEffect(() => {
    setSelectedCandidate(null)
  }, [selectedAccountId])

  useEffect(() => {
    if (!selectedCandidate && discovery?.candidates.length) {
      setSelectedCandidate(discovery.candidates[0])
    }
  }, [discovery, selectedCandidate])

  const totalUnrealizedPnL = openPositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)
  const totalUnrealizedPnLPct = accountOverview && accountOverview.balance > 0
    ? (totalUnrealizedPnL / accountOverview.balance) * 100
    : 0

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
    setActiveTab('research')
    void runTab('research', {
      candidate_id: candidate.candidate_id,
      symbol: candidate.symbol,
    })
  }

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-6">
        <Breadcrumb />

        <PageHeader
          title="Paper Trading"
          description="Operate the full paper-trading loop with explicit account context, bounded research packets, and truthful capability blockers."
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

      {!isLoading && !selectedAccountId && (
        <Card className="p-6">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">No Paper Trading Account</h2>
            <p className="text-sm text-muted-foreground">
              Select a paper trading account before using discovery, research, decisions, or review workflows.
            </p>
          </div>
        </Card>
      )}

      <AccountStatusCard
        accountOverview={accountOverview}
        metrics={performanceMetrics}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as PaperTradingTab)} className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="discovery" className="flex items-center gap-2">
            <Newspaper className="h-4 w-4" />
            <span className="hidden sm:inline">Discovery</span>
          </TabsTrigger>
          <TabsTrigger value="research" className="flex items-center gap-2">
            <FileSearch className="h-4 w-4" />
            <span className="hidden sm:inline">Research</span>
          </TabsTrigger>
          <TabsTrigger value="decisions" className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4" />
            <span className="hidden sm:inline">Decisions</span>
          </TabsTrigger>
          <TabsTrigger value="positions" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            <span className="hidden sm:inline">Positions</span>
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            <span className="hidden sm:inline">History</span>
          </TabsTrigger>
          <TabsTrigger value="review" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            <span className="hidden sm:inline">Review</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <UnrealizedPnLCard
              totalUnrealizedPnL={totalUnrealizedPnL}
              unrealizedPnLPct={totalUnrealizedPnLPct}
              positions={openPositions}
            />
            <Card>
              <PerformanceMetrics metrics={performanceMetrics} isLoading={isLoading} />
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="discovery">
          <AgentDiscoveryPanel
            envelope={discovery}
            isLoading={activeTab === 'discovery' ? artifactsLoading : false}
            error={activeTab === 'discovery' ? artifactsError : null}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('discovery') }}
            selectedCandidateId={selectedCandidate?.candidate_id ?? null}
            onSelectCandidate={handleSelectCandidate}
          />
        </TabsContent>

        <TabsContent value="research">
          <AgentResearchPanel
            envelope={research}
            selectedCandidate={selectedCandidate}
            isLoading={activeTab === 'research' ? artifactsLoading : false}
            error={activeTab === 'research' ? artifactsError : null}
            canRun={Boolean(selectedAccountId && selectedCandidate)}
            onRun={() => {
              if (!selectedCandidate) return
              void runTab('research', {
                candidate_id: selectedCandidate.candidate_id,
                symbol: selectedCandidate.symbol,
              })
            }}
          />
        </TabsContent>

        <TabsContent value="decisions">
          <AgentDecisionPanel
            envelope={decisions}
            isLoading={activeTab === 'decisions' ? artifactsLoading : false}
            error={activeTab === 'decisions' ? artifactsError : null}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('decisions') }}
          />
        </TabsContent>

        <TabsContent value="positions">
          <RealTimePositionsTable positions={openPositions} isLoading={isLoading} />
        </TabsContent>

        <TabsContent value="history">
          <TradeHistoryTable trades={closedTrades} isLoading={isLoading} />
        </TabsContent>

        <TabsContent value="review">
          <AgentReviewPanel
            envelope={review}
            isLoading={activeTab === 'review' ? artifactsLoading : false}
            error={activeTab === 'review' ? artifactsError : null}
            canRun={Boolean(selectedAccountId)}
            onRun={() => { void runTab('review') }}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default PaperTradingFeature
