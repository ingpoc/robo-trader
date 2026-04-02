import React, { useCallback, useMemo, useState } from 'react'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent } from '@/components/ui/Card'
import { useAccount } from '@/contexts/AccountContext'
import { operatorAPI } from '@/api/endpoints'
import { PaperTradingAccountBar } from '@/features/paper-trading/components/PaperTradingAccountBar'
import { TradingCapabilityCard } from '@/features/paper-trading/components/TradingCapabilityCard'
import { usePaperTradingWebMCP } from '@/features/paper-trading/hooks/usePaperTradingWebMCP'
import type {
  RuntimeHealthResponse,
  RuntimeIdentity,
  TradingCapabilitySnapshot,
  WebMCPReadiness,
} from '@/features/paper-trading/types'
import { useDashboardData } from '@/features/dashboard/hooks/useDashboardData'

const frontendRuntimeIdentity: RuntimeIdentity = __APP_RUNTIME_IDENTITY__

export function HealthFeature() {
  const { accounts, selectedAccount, selectAccount, refreshAccounts } = useAccount()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const { snapshot, overviewSummary, runtimeHealth, isLoading, error, refetch } = useDashboardData({
    accountId: selectedAccount?.account_id ?? null,
  })

  const selectAccountById = useCallback(async (accountId: string) => {
    const account = accounts.find(item => item.account_id === accountId)
    if (!account) {
      throw new Error(`Paper trading account '${accountId}' is not available in the current session.`)
    }
    selectAccount(account)
  }, [accounts, selectAccount])

  const refreshOperatorView = useCallback(async (options?: { accountId?: string | null }) => {
    const accountId = options?.accountId ?? selectedAccount?.account_id ?? null
    if (accountId) {
      await fetch(`/api/paper-trading/accounts/${encodeURIComponent(accountId)}/operator/refresh-readiness`, {
        method: 'POST',
      })
    }
    await Promise.all([refreshAccounts(), refetch()])
  }, [refetch, refreshAccounts, selectedAccount?.account_id])

  const getOperatorSnapshot = useCallback(async (accountId?: string | null) => {
    const selectedId = accountId ?? selectedAccount?.account_id ?? null
    if (!selectedId) {
      throw new Error('Select a paper trading account first.')
    }
    return await operatorAPI.getOperatorSnapshot(selectedId)
  }, [selectedAccount?.account_id])

  const webmcpReadiness = usePaperTradingWebMCP({
    accounts,
    selectedAccountId: selectedAccount?.account_id ?? null,
    selectAccountById,
    refreshOperatorView,
    getOperatorSnapshot,
  })

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await refreshOperatorView()
    } finally {
      setIsRefreshing(false)
    }
  }, [refreshOperatorView])

  const selectedAccountOption = useMemo(() => accounts.map(account => ({
    account_id: account.account_id,
    account_name: account.account_name,
    strategy_type: account.strategy_type,
  })), [accounts])

  return (
    <div className="page-wrapper">
      <div className="space-y-4">
        <Breadcrumb items={[{ label: 'Health' }]} />
        <PageHeader
          title="Health"
          description="One place for readiness, runtime truth, broker state, and autonomy boundaries. No trade workflow lives here."
        />
      </div>

      <PaperTradingAccountBar
        accounts={selectedAccountOption}
        selectedAccountId={selectedAccount?.account_id ?? null}
        onSelectAccount={(accountId) => { void selectAccountById(accountId) }}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {error ? (
        <Card className="border-red-300 bg-red-50/80 text-red-900">
          <CardContent className="p-4 text-sm font-medium">
            Health data is unavailable. {error.message}
          </CardContent>
        </Card>
      ) : null}

      <TradingCapabilityCard
        snapshot={normalizeCapabilitySnapshot(snapshot?.capability_snapshot)}
        webmcpReadiness={webmcpReadiness as WebMCPReadiness}
        isLoading={isLoading}
      />

      <RuntimeIdentityPanel
        runtimeHealth={runtimeHealth}
        frontendRuntimeIdentity={frontendRuntimeIdentity}
        selectedAccountId={selectedAccount?.account_id ?? null}
        latestDiscoveryAt={snapshot?.discovery && typeof snapshot.discovery === 'object' && 'generated_at' in snapshot.discovery
          ? String(snapshot.discovery.generated_at ?? '')
          : null}
      />

      <OperatorContextPanel
        executionMode={overviewSummary?.execution_mode ?? snapshot?.execution_mode ?? null}
        nextAction={overviewSummary?.next_action?.summary ?? null}
        nextActionDetail={overviewSummary?.next_action?.detail ?? null}
        firstBlocker={overviewSummary?.readiness.first_blocker ?? null}
        runtimeHealth={runtimeHealth}
      />

      <AutonomyBoundaryPanel />
    </div>
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
    : 'The operator page is talking to the current backend revision, so readiness state should reflect current code.'
  const activeLane = runtimeHealth?.active_lane ?? null
  const callbackListener = runtimeHealth?.callback_listener ?? null

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
          <p className="desk-kicker">Canonical lane</p>
          <p className="text-muted-foreground">
            Backend lane: <span className="font-medium text-foreground">{activeLane?.base_url ?? 'unknown'}</span>
            {' · '}
            OAuth callback: <span className="font-medium text-foreground">
              {callbackListener ? `:${callbackListener.port} ${callbackListener.active ? 'active' : 'inactive'}` : 'unknown'}
            </span>
          </p>
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

function OperatorContextPanel({
  executionMode,
  nextAction,
  nextActionDetail,
  firstBlocker,
  runtimeHealth,
}: {
  executionMode: string | null
  nextAction: string | null
  nextActionDetail: string | null
  firstBlocker: string | null
  runtimeHealth: RuntimeHealthResponse | null
}) {
  const quota = runtimeHealth?.ai_runtime_quota ?? null
  return (
    <section className="grid gap-6 xl:grid-cols-[1.15fr_1fr]">
      <Card className="border-border/70 bg-white/85">
        <CardContent className="grid gap-6 p-5 md:grid-cols-2">
          <div className="space-y-3">
            <p className="desk-kicker">Blocking Issue</p>
            <p className="text-base font-semibold text-foreground">
              {firstBlocker ?? 'No blocking issue is active for the selected operator path.'}
            </p>
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="rounded-full border border-border/70 bg-background/80 px-3 py-1 font-medium text-foreground">
                Execution mode {executionMode ?? 'operator_confirmed_execution'}
              </span>
              <span className="rounded-full border border-border/70 bg-background/80 px-3 py-1 font-medium text-foreground">
                Autonomous entry disabled
              </span>
            </div>
          </div>
          <div className="space-y-3">
            <p className="desk-kicker">Next Action</p>
            <p className="text-base font-semibold text-foreground">
              {nextAction ?? 'Continue monitoring readiness and refresh the account snapshot before any mutation.'}
            </p>
            <p className="text-sm leading-6 text-muted-foreground">
              {nextActionDetail ?? 'This is the current operator recommendation derived from the live backend state.'}
            </p>
            {quota?.usage_limited ? (
              <p className="text-sm leading-6 text-amber-800">
                AI runtime quota is currently limited. Retry after {quota.retry_at ? formatRuntimeTimestamp(quota.retry_at) : 'the runtime resets'}.
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </section>
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

function formatRuntimeTimestamp(value?: string | null) {
  if (!value) return 'unknown'

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value

  return parsed.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function normalizeCapabilitySnapshot(value: unknown): TradingCapabilitySnapshot | null {
  if (!value || typeof value !== 'object') return null

  const record = value as Record<string, unknown>
  if (
    typeof record.mode === 'string'
    && typeof record.overall_status === 'string'
    && Array.isArray(record.checks)
    && Array.isArray(record.blockers)
  ) {
    return value as TradingCapabilitySnapshot
  }

  return null
}

export default HealthFeature
