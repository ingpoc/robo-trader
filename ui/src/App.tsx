import React, { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { Navigation } from '@/components/Sidebar/Navigation'
import { Toaster } from '@/components/common/Toaster'
import { GlobalErrorBoundary } from '@/components/common/GlobalErrorBoundary'
import { WebSocketErrorBoundary } from '@/components/common/WebSocketErrorBoundary'
import { DashboardErrorBoundary } from '@/components/common/DashboardErrorBoundary'
import { Button } from '@/components/ui/Button'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AccountProvider, useAccount, type Account } from '@/contexts/AccountContext'
import ConfigurationFeature from '@/features/configuration/ConfigurationFeature'
import { DashboardFeature } from '@/features/dashboard/DashboardFeature'
import { PaperTradingFeature } from '@/features/paper-trading/PaperTradingFeature'
import { usePaperTradingWebMCP } from '@/features/paper-trading/hooks/usePaperTradingWebMCP'
import { useTheme } from '@/hooks/useTheme'
import type {
  AccountOverviewResponse,
  ClosedTradeResponse,
  OpenPositionResponse,
  PaperTradingOperatorSnapshot,
  PerformanceMetricsResponse,
  RuntimeHealthResponse,
  RuntimeIdentity,
  TradingCapabilitySnapshot,
  WebMCPReadiness,
} from '@/features/paper-trading/types'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
})

type JsonRecord = Record<string, unknown>

interface FetchJsonResult<T = unknown> {
  ok: boolean
  status: number
  payload: T | null
  error: string | null
}

async function readResponsePayload(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return await response.json()
  }

  const text = await response.text()
  return text ? { message: text } : null
}

function extractResponseError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object') {
    const record = payload as JsonRecord
    if (typeof record.error === 'string' && record.error.trim()) return record.error
    if (typeof record.message === 'string' && record.message.trim()) return record.message
    if (typeof record.detail === 'string' && record.detail.trim()) return record.detail
  }
  return fallback
}

async function fetchJsonResult<T = unknown>(url: string, init?: RequestInit): Promise<FetchJsonResult<T>> {
  try {
    const response = await fetch(url, init)
    const payload = (await readResponsePayload(response)) as T | null
    return {
      ok: response.ok,
      status: response.status,
      payload,
      error: response.ok ? null : extractResponseError(payload, `Request failed with status ${response.status}`),
    }
  } catch (error) {
    return {
      ok: false,
      status: 0,
      payload: null,
      error: error instanceof Error ? error.message : 'Network request failed',
    }
  }
}

function normalizeOverviewPayload(data: unknown, fallbackAccountId = ''): AccountOverviewResponse | null {
  if (!data || typeof data !== 'object') return null
  const record = data as JsonRecord
  return {
    account_id: String(record.accountId ?? record.account_id ?? fallbackAccountId),
    balance: Number(record.balance ?? record.currentBalance ?? 0),
    deployed_capital: Number(record.deployedCapital ?? record.deployed_capital ?? 0),
    buying_power: Number(record.marginAvailable ?? record.buyingPower ?? record.buying_power ?? 0),
    cash_available: Number(record.cashAvailable ?? record.cash_available ?? 0),
    last_updated: String(record.lastUpdated ?? record.last_updated ?? new Date().toISOString()),
    valuation_status: typeof (record.valuationStatus ?? record.valuation_status) === 'string'
      ? String(record.valuationStatus ?? record.valuation_status) as AccountOverviewResponse['valuation_status']
      : undefined,
    valuation_detail: typeof (record.valuationDetail ?? record.valuation_detail) === 'string'
      ? String(record.valuationDetail ?? record.valuation_detail)
      : null,
  }
}

function toNullableNumber(value: unknown): number | null {
  if (value == null || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizePositionsPayload(data: unknown): OpenPositionResponse[] {
  const positions = Array.isArray((data as JsonRecord | null)?.positions)
    ? ((data as JsonRecord).positions as Array<Record<string, unknown>>)
    : Array.isArray(data)
      ? (data as Array<Record<string, unknown>>)
      : []

  return positions.map(position => ({
    trade_id: String(position.trade_id ?? position.tradeId ?? position.id ?? ''),
    symbol: String(position.symbol ?? ''),
    quantity: Number(position.quantity ?? 0),
    entry_price: Number(position.entry_price ?? position.entryPrice ?? position.avgPrice ?? 0),
    current_price: toNullableNumber(position.current_price ?? position.currentPrice ?? position.ltp),
    stop_loss: position.stop_loss == null ? Number(position.stopLoss ?? NaN) || undefined : Number(position.stop_loss),
    target: position.target == null ? Number(position.target_price ?? position.target ?? NaN) || undefined : Number(position.target),
    unrealized_pnl: toNullableNumber(position.unrealized_pnl ?? position.pnl),
    unrealized_pnl_pct: toNullableNumber(position.unrealized_pnl_pct ?? position.pnlPercent),
    entry_time: String(position.entry_time ?? position.entryDate ?? position.entry_date ?? ''),
    strategy: typeof position.strategy === 'string' ? position.strategy : typeof position.strategy_rationale === 'string' ? position.strategy_rationale : undefined,
    tradeType: typeof position.tradeType === 'string' ? position.tradeType : typeof position.trade_type === 'string' ? position.trade_type : undefined,
    currentValue: toNullableNumber(position.currentValue ?? position.current_value),
    daysHeld: Number(position.daysHeld ?? position.days_held ?? 0),
    markStatus: (position.markStatus ?? position.market_price_status ?? null) as OpenPositionResponse['markStatus'],
    markDetail: (position.markDetail ?? position.market_price_detail ?? null) as string | null,
    markTimestamp: (position.markTimestamp ?? position.market_price_timestamp ?? null) as string | null,
  }))
}

function normalizeTradesPayload(data: unknown): ClosedTradeResponse[] {
  if (Array.isArray((data as JsonRecord | null)?.trades)) {
    return ((data as JsonRecord).trades as ClosedTradeResponse[]) ?? []
  }
  return Array.isArray(data) ? (data as ClosedTradeResponse[]) : []
}

function normalizePerformancePayload(data: unknown): PerformanceMetricsResponse | null {
  if (!data || typeof data !== 'object') return null
  const record = data as JsonRecord
  return (record.performance ?? record.metrics ?? record) as PerformanceMetricsResponse
}

function serializeAccounts(accounts: Account[]) {
  return accounts.map(account => ({
    account_id: account.account_id,
    account_name: account.account_name,
    strategy_type: account.strategy_type,
  }))
}

function PaperTradingFeatureWrapper() {
  const { accounts, selectedAccount, selectAccount, isLoading: isAccountsLoading, refreshAccounts } = useAccount()
  const [accountOverview, setAccountOverview] = useState<AccountOverviewResponse | null>(null)
  const [openPositions, setOpenPositions] = useState<OpenPositionResponse[]>([])
  const [closedTrades, setClosedTrades] = useState<ClosedTradeResponse[]>([])
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetricsResponse | null>(null)
  const [capabilitySnapshot, setCapabilitySnapshot] = useState<TradingCapabilitySnapshot | null>(null)
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealthResponse | null>(null)
  const [paperTradingError, setPaperTradingError] = useState<string | null>(null)
  const [performanceError, setPerformanceError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const requestSequenceRef = useRef(0)
  const lastLoadedAccountRef = useRef<string | null>(null)
  const frontendRuntimeIdentity: RuntimeIdentity = __APP_RUNTIME_IDENTITY__

  const fetchRuntimeHealth = React.useCallback(async () => {
    const healthResult = await fetchJsonResult<RuntimeHealthResponse>('/api/health')
    if (healthResult.ok && healthResult.payload) {
      setRuntimeHealth(healthResult.payload)
      return
    }

    setRuntimeHealth(null)
  }, [])

  const fetchData = React.useCallback(async (options?: { preserveContent?: boolean; accountIdOverride?: string | null }) => {
    const accountId = options?.accountIdOverride ?? selectedAccount?.account_id ?? null
    const shouldWaitForSelection = accounts.length > 0 && !accountId
    if (isAccountsLoading || shouldWaitForSelection) {
      return
    }

    const preserveContent = options?.preserveContent ?? false
    const isColdStart = !preserveContent && lastLoadedAccountRef.current !== accountId

    if (isColdStart) {
      setIsLoading(true)
    }

    if (!accountId) {
      setCapabilitySnapshot(null)
      setAccountOverview(null)
      setOpenPositions([])
      setClosedTrades([])
      setPerformanceMetrics(null)
      setPaperTradingError(null)
      setPerformanceError(null)
      setIsLoading(false)
      lastLoadedAccountRef.current = null
      return
    }

    const requestId = requestSequenceRef.current + 1
    requestSequenceRef.current = requestId

    try {
      void (async () => {
        try {
          const capabilityResponse = await fetch(`/api/paper-trading/capabilities?account_id=${encodeURIComponent(accountId)}`)
          if (requestSequenceRef.current !== requestId) {
            return
          }
          if (capabilityResponse.ok) {
            setCapabilitySnapshot(await capabilityResponse.json())
          } else {
            setCapabilitySnapshot(null)
          }
        } catch {
          if (requestSequenceRef.current === requestId) {
            setCapabilitySnapshot(null)
          }
        }
      })()

      const [overviewResult, positionsResult, tradesResult, performanceResult] = await Promise.all([
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/overview`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/positions`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/trades`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/performance?period=month`),
      ])

      if (requestSequenceRef.current !== requestId) {
        return
      }

      const dataErrors = [
        overviewResult.ok ? null : `Overview: ${overviewResult.error ?? 'Request failed'}`,
        positionsResult.ok ? null : `Positions: ${positionsResult.error ?? 'Request failed'}`,
      ].filter(Boolean) as string[]

      setPaperTradingError(dataErrors.length ? dataErrors.join(' | ') : null)
      setPerformanceError(performanceResult.ok ? null : `Performance: ${performanceResult.error ?? 'Request failed'}`)

      if (overviewResult.ok) {
        setAccountOverview(normalizeOverviewPayload(overviewResult.payload, accountId))
      } else {
        setAccountOverview(null)
      }

      if (positionsResult.ok) {
        setOpenPositions(normalizePositionsPayload(positionsResult.payload))
      } else {
        setOpenPositions([])
      }

      if (tradesResult.ok) {
        setClosedTrades(normalizeTradesPayload(tradesResult.payload))
      } else {
        setClosedTrades([])
      }

      if (performanceResult.ok) {
        setPerformanceMetrics(normalizePerformancePayload(performanceResult.payload))
      } else {
        setPerformanceMetrics(null)
      }

      lastLoadedAccountRef.current = accountId
    } catch (error) {
      console.error('Error fetching paper trading data:', error)
    } finally {
      if (requestSequenceRef.current === requestId) {
        setIsLoading(false)
      }
    }
  }, [accounts.length, isAccountsLoading, selectedAccount?.account_id])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  useEffect(() => {
    void fetchRuntimeHealth()
  }, [fetchRuntimeHealth])

  const handleRefresh = async () => {
    await refreshAccounts()
    await Promise.all([
      fetchRuntimeHealth(),
      fetchData({ preserveContent: true }),
    ])
  }

  const refreshOperatorView = React.useCallback(
    async (options?: { accountId?: string | null; preserveContent?: boolean }) => {
      await refreshAccounts()
      await Promise.all([
        fetchRuntimeHealth(),
        fetchData({
          preserveContent: options?.preserveContent ?? true,
          accountIdOverride: options?.accountId ?? selectedAccount?.account_id ?? null,
        }),
      ])
    },
    [fetchData, fetchRuntimeHealth, refreshAccounts, selectedAccount?.account_id],
  )

  const selectAccountById = React.useCallback(
    async (accountId: string) => {
      const account = accounts.find(item => item.account_id === accountId)
      if (!account) {
        throw new Error(`Paper trading account '${accountId}' is not available in the current session.`)
      }
      selectAccount(account)
      await fetchData({ preserveContent: false, accountIdOverride: accountId })
    },
    [accounts, fetchData, selectAccount],
  )

  const getOperatorSnapshot = React.useCallback(
    async (accountIdOverride?: string | null): Promise<PaperTradingOperatorSnapshot> => {
      const accountId = accountIdOverride ?? selectedAccount?.account_id ?? null
      const serializedAccounts = serializeAccounts(accounts)

      if (!accountId) {
        return {
          generated_at: new Date().toISOString(),
          selected_account_id: null,
          execution_mode: 'operator_confirmed_execution',
          accounts: serializedAccounts,
          health: null,
          configuration_status: null,
          queue_status: null,
          capability_snapshot: null,
          overview: null,
          positions: [],
          trades: [],
          performance: null,
          discovery: null,
          decisions: null,
          review: null,
          learning_summary: null,
          improvement_report: null,
          run_history: null,
          latest_retrospective: null,
          learning_readiness: null,
          latest_improvement_decisions: [],
          promotion_report: null,
          staleness: null,
          operator_recommendation: null,
          positions_health: null,
          recent_trade_outcomes: [],
          promotable_improvements: [],
          incidents: [],
        }
      }

      const operatorSnapshotResult = await fetchJsonResult<PaperTradingOperatorSnapshot>(
        `/api/paper-trading/accounts/${encodeURIComponent(accountId)}/operator-snapshot`,
      )
      if (operatorSnapshotResult.ok && operatorSnapshotResult.payload) {
        const payload = operatorSnapshotResult.payload as PaperTradingOperatorSnapshot
        return {
          ...payload,
          accounts: serializedAccounts,
          selected_account_id: payload.selected_account_id ?? accountId,
          overview: normalizeOverviewPayload(payload.overview, accountId),
          positions: normalizePositionsPayload({ positions: payload.positions ?? [] }),
          trades: normalizeTradesPayload({ trades: payload.trades ?? [] }),
          performance: normalizePerformancePayload(payload.performance),
          incidents: Array.isArray(payload.incidents) ? payload.incidents : [],
        }
      }

      const [
        healthResult,
        configurationResult,
        queueResult,
        capabilityResult,
        overviewResult,
        positionsResult,
        tradesResult,
        performanceResult,
        discoveryResult,
        decisionsResult,
        reviewResult,
        learningResult,
        improvementResult,
        runHistoryResult,
        incidentsResult,
      ] = await Promise.all([
        fetchJsonResult('/api/health'),
        fetchJsonResult('/api/configuration/status'),
        fetchJsonResult('/api/queues/status'),
        fetchJsonResult(`/api/paper-trading/capabilities?account_id=${encodeURIComponent(accountId)}`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/overview`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/positions`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/trades`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/performance?period=month`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/discovery`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/decisions`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/review`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/learning-summary`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/improvement-report`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/runs/history?limit=20`),
        fetchJsonResult(`/api/paper-trading/accounts/${accountId}/operator-incidents`),
      ])

      return {
        generated_at: new Date().toISOString(),
        selected_account_id: accountId,
        accounts: serializedAccounts,
        health: healthResult.payload as Record<string, unknown> | null,
        configuration_status: ((configurationResult.payload as JsonRecord | null)?.configuration_status as Record<string, unknown> | undefined) ?? null,
        queue_status: queueResult.payload as Record<string, unknown> | null,
        capability_snapshot: capabilityResult.payload as TradingCapabilitySnapshot | Record<string, unknown> | null,
        overview: normalizeOverviewPayload(overviewResult.payload, accountId),
        positions: normalizePositionsPayload(positionsResult.payload),
        trades: normalizeTradesPayload(tradesResult.payload),
        performance: normalizePerformancePayload(performanceResult.payload),
        discovery: discoveryResult.payload as Record<string, unknown> | null,
        decisions: decisionsResult.payload as Record<string, unknown> | null,
        review: reviewResult.payload as Record<string, unknown> | null,
        learning_summary: learningResult.payload as Record<string, unknown> | null,
        improvement_report: improvementResult.payload as Record<string, unknown> | null,
        run_history: runHistoryResult.payload as Record<string, unknown> | null,
        latest_retrospective: null,
        learning_readiness: null,
        latest_improvement_decisions: [],
        promotion_report: null,
        staleness: null,
        operator_recommendation: null,
        positions_health: null,
        recent_trade_outcomes: [],
        promotable_improvements: [],
        incidents: (((incidentsResult.payload as JsonRecord | null)?.incidents as Array<Record<string, unknown>> | undefined) ?? []),
      }
    },
    [accounts, selectedAccount?.account_id],
  )

  const webmcpReadiness: WebMCPReadiness = usePaperTradingWebMCP({
    accounts,
    selectedAccountId: selectedAccount?.account_id ?? null,
    selectAccountById,
    refreshOperatorView,
    getOperatorSnapshot,
  })

  return (
    <PaperTradingFeature
      accounts={serializeAccounts(accounts)}
      selectedAccountId={selectedAccount?.account_id ?? null}
      onSelectAccount={(accountId) => {
        void selectAccountById(accountId)
      }}
      accountOverview={accountOverview}
      openPositions={openPositions}
      closedTrades={closedTrades}
      performanceMetrics={performanceMetrics}
      capabilitySnapshot={capabilitySnapshot}
      runtimeHealth={runtimeHealth}
      frontendRuntimeIdentity={frontendRuntimeIdentity}
      webmcpReadiness={webmcpReadiness}
      dataError={paperTradingError}
      performanceError={performanceError}
      onRefresh={handleRefresh}
      isLoading={isLoading || isAccountsLoading}
    />
  )
}

function AppContent() {
  useTheme()

  const [sidebarOpen, setSidebarOpen] = useState(false)

  const closeSidebar = React.useCallback(() => {
    const activeElement = document.activeElement
    if (activeElement instanceof HTMLElement) {
      const navigationRoot = document.getElementById('navigation')
      if (navigationRoot?.contains(activeElement)) {
        activeElement.blur()
      }
    }
    setSidebarOpen(false)
  }, [])

  return (
    <WebSocketErrorBoundary>
      <div className="flex min-h-screen bg-background text-foreground">
        {sidebarOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-[1px] lg:hidden"
            aria-label="Close navigation overlay"
            onClick={closeSidebar}
          />
        ) : null}

        <aside
          id="navigation"
          className={`
            fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
          aria-hidden={!sidebarOpen && window.innerWidth < 1024}
        >
          <div className="flex h-full flex-col">
            <Navigation onClose={closeSidebar} />
          </div>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <header
            className="flex h-14 items-center gap-4 border-b border-border/80 bg-white/85 px-4 backdrop-blur-sm dark:bg-warmgray-800/85 lg:hidden"
            role="banner"
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden"
              aria-label="Open navigation menu"
              aria-expanded={sidebarOpen}
              aria-controls="navigation"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </Button>
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded border border-border bg-muted text-foreground" aria-hidden="true">
                <span className="text-xs font-bold">R</span>
              </div>
              <span className="text-sm font-semibold text-foreground">Robo Trader</span>
            </div>
          </header>

          <main
            id="main-content"
            className="flex-1 overflow-y-auto"
            role="main"
            aria-label="Main content"
          >
            <Routes>
              <Route path="/" element={<DashboardErrorBoundary><DashboardFeature /></DashboardErrorBoundary>} />
              <Route path="/configuration" element={<ConfigurationFeature />} />
              <Route path="/paper-trading" element={<PaperTradingFeatureWrapper />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>

        <Toaster />
      </div>
    </WebSocketErrorBoundary>
  )
}

export function App() {
  return (
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <TooltipProvider>
            <AccountProvider>
              <AppContent />
            </AccountProvider>
          </TooltipProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  )
}
