import React, { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Navigation } from '@/components/Sidebar/Navigation'
import { Toaster } from '@/components/common/Toaster'
import { GlobalErrorBoundary } from '@/components/common/GlobalErrorBoundary'
import { WebSocketErrorBoundary } from '@/components/common/WebSocketErrorBoundary'
import { DashboardErrorBoundary } from '@/components/common/DashboardErrorBoundary'
import { useSystemStatusStore } from '@/stores/systemStatusStore'
import { AccountProvider } from '@/contexts/AccountContext'
import { DashboardFeature } from '@/features/dashboard/DashboardFeature'
import { SystemHealthFeature } from '@/features/system-health/SystemHealthFeature'
import ConfigurationFeature from '@/features/configuration/ConfigurationFeature'
import { PaperTradingFeature } from '@/features/paper-trading/PaperTradingFeature'
import type {
  AccountOverviewResponse,
  ClosedTradeResponse,
  OpenPositionResponse,
  PerformanceMetricsResponse,
  TradingCapabilitySnapshot,
} from '@/features/paper-trading/types'
import { useAccount } from '@/contexts/AccountContext'
import { Button } from '@/components/ui/Button'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useTheme } from '@/hooks/useTheme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
})

// Wrapper for PaperTradingFeature - READ-ONLY observatory
function PaperTradingFeatureWrapper() {
  const { accounts, selectedAccount, selectAccount, isLoading: isAccountsLoading, refreshAccounts } = useAccount()
  const [accountOverview, setAccountOverview] = useState<AccountOverviewResponse | null>(null)
  const [openPositions, setOpenPositions] = useState<OpenPositionResponse[]>([])
  const [closedTrades, setClosedTrades] = useState<ClosedTradeResponse[]>([])
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetricsResponse | null>(null)
  const [capabilitySnapshot, setCapabilitySnapshot] = useState<TradingCapabilitySnapshot | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchData = async () => {
    const accountId = selectedAccount?.account_id
    if (!selectedAccount?.account_id) {
      setAccountOverview(null)
      setOpenPositions([])
      setClosedTrades([])
      setPerformanceMetrics(null)
    }

    setIsLoading(true)
    try {
      const capabilityUrl = accountId
        ? `/api/paper-trading/capabilities?account_id=${encodeURIComponent(accountId)}`
        : '/api/paper-trading/capabilities'

      const responses = await Promise.all([
        fetch(capabilityUrl),
        ...(accountId
          ? [
              fetch(`/api/paper-trading/accounts/${accountId}/overview`),
              fetch(`/api/paper-trading/accounts/${accountId}/positions`),
              fetch(`/api/paper-trading/accounts/${accountId}/trades`),
              fetch(`/api/paper-trading/accounts/${accountId}/performance?period=month`),
            ]
          : []),
      ])

      const capabilityRes = responses[0]
      if (capabilityRes.ok) {
        setCapabilitySnapshot(await capabilityRes.json())
      } else {
        setCapabilitySnapshot(null)
      }

      if (accountId) {
        const [overviewRes, positionsRes, tradesRes, performanceRes] = responses.slice(1)

        if (overviewRes?.ok) {
          const data = await overviewRes.json()
          setAccountOverview({
            account_id: data.accountId || accountId,
            balance: data.balance || data.currentBalance || 0,
            deployed_capital: data.deployedCapital || data.deployed_capital || 0,
            buying_power: data.marginAvailable || data.buyingPower || 0,
            cash_available: data.cashAvailable || data.cash_available || 0,
            last_updated: data.lastUpdated || new Date().toISOString(),
          })
        }
        if (positionsRes?.ok) {
          const data = await positionsRes.json()
          setOpenPositions(data.positions || data || [])
        }
        if (tradesRes?.ok) {
          const data = await tradesRes.json()
          setClosedTrades(data.trades || data || [])
        }
        if (performanceRes?.ok) {
          const data = await performanceRes.json()
          setPerformanceMetrics(data.performance || data.metrics || null)
        } else {
          setPerformanceMetrics(null)
        }
      }
    } catch (error) {
      console.error('Error fetching paper trading data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  React.useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [selectedAccount?.account_id, isAccountsLoading])

  const handleRefresh = async () => {
    await refreshAccounts()
    await fetchData()
  }

  return (
    <PaperTradingFeature
      accounts={accounts.map(account => ({
        account_id: account.account_id,
        account_name: account.account_name,
        strategy_type: account.strategy_type,
      }))}
      selectedAccountId={selectedAccount?.account_id ?? null}
      onSelectAccount={(accountId) => {
        const account = accounts.find(item => item.account_id === accountId)
        if (account) {
          selectAccount(account)
        }
      }}
      accountOverview={accountOverview}
      openPositions={openPositions}
      closedTrades={closedTrades}
      performanceMetrics={performanceMetrics}
      capabilitySnapshot={capabilitySnapshot}
      onRefresh={handleRefresh}
      isLoading={isLoading || isAccountsLoading}
    />
  )
}

function AppContent() {
  useTheme()

  // Initialize WebSocket connection globally for the entire app
  const initializeWebSocket = useSystemStatusStore((state) => state.initializeWebSocket)

  React.useEffect(() => {
    // Add a small delay to ensure proper cleanup on page refresh
    const timeoutId = setTimeout(() => {
      const cleanup = initializeWebSocket()

      // Add page unload cleanup
      const handleBeforeUnload = () => {
        if (cleanup) cleanup()
      }

      window.addEventListener('beforeunload', handleBeforeUnload)

      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload)
        if (cleanup) cleanup()
      }
    }, 100) // 100ms delay

    return () => {
      clearTimeout(timeoutId)
    }
  }, [initializeWebSocket])

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

  // Keyboard navigation for sidebar and global shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Sidebar shortcuts
      if (event.key === 'Escape' && sidebarOpen) {
        closeSidebar()
      }

      // Global shortcuts (only when not typing in inputs)
      const target = event.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true'

      if (!isInput) {
        switch (event.key) {
          case 'b':
            if (event.ctrlKey || event.metaKey) {
              event.preventDefault()
              setSidebarOpen(prev => !prev)
            }
            break
          case 'f':
            if (event.ctrlKey || event.metaKey) {
              event.preventDefault()
              // Focus search input if available
              const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
              if (searchInput) {
                searchInput.focus()
              }
            }
            break
          case '1':
          case '2':
          case '3':
          case '4':
          case '5':
          case '6':
          case '7':
          case '8':
          case '9':
            if (event.altKey) {
              event.preventDefault()
              // Navigate to different sections based on number
              const routes = ['/', '/paper-trading', '/system-health', '/configuration']
              const index = parseInt(event.key) - 1
              if (routes[index]) {
                window.location.href = routes[index]
              }
            }
            break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [closeSidebar, sidebarOpen])

  return (
    <WebSocketErrorBoundary>
      {/* Skip links for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-accent focus:text-white focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>
      <a
        href="#navigation"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-32 focus:z-50 focus:px-4 focus:py-2 focus:bg-accent focus:text-white focus:rounded-md focus:shadow-lg"
      >
        Skip to navigation
      </a>

      <div className="flex h-screen overflow-hidden bg-transparent">
        {/* Mobile sidebar backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-slate-950/30 backdrop-blur-sm lg:hidden"
            onClick={closeSidebar}
            onKeyDown={(e) => {
              if (e.key === 'Escape') closeSidebar()
            }}
            aria-hidden="true"
            tabIndex={-1}
          />
        )}

        {/* Sidebar */}
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

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Mobile header */}
          <header
            className="flex h-14 items-center gap-4 border-b border-border/80 bg-card/85 px-4 backdrop-blur-sm lg:hidden"
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

          {/* Page content */}
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
              <Route path="/system-health" element={<SystemHealthFeature />} />
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
        <BrowserRouter>
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
