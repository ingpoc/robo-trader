import React, { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Navigation } from '@/components/Sidebar/Navigation'
import { Toaster } from '@/components/common/Toaster'
import { GlobalErrorBoundary } from '@/components/common/GlobalErrorBoundary'
import { WebSocketErrorBoundary } from '@/components/common/WebSocketErrorBoundary'
import { DashboardErrorBoundary } from '@/components/common/DashboardErrorBoundary'
import { ClaudeStatusIndicator } from '@/components/ClaudeStatusIndicator'
import { useWebSocket } from '@/hooks/useWebSocket'
import { AccountProvider } from '@/contexts/AccountContext'
import { DashboardFeature } from '@/features/dashboard/DashboardFeature'
import { NewsEarningsFeature } from '@/features/news-earnings/NewsEarningsFeature'
import { AITransparencyFeature } from '@/features/ai-transparency/AITransparencyFeature'
import { SystemHealthFeature } from '@/features/system-health/SystemHealthFeature'
import { AgentsFeature } from '@/features/agents/AgentsFeature'
import { PaperTrading } from '@/pages/PaperTrading'
import { Config } from '@/pages/Config'
import { Logs } from '@/pages/Logs'
import { Button } from '@/components/ui/Button'
import { TooltipProvider } from '@/components/ui/tooltip'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
})

function AppContent() {
  useWebSocket()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Keyboard navigation for sidebar and global shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Sidebar shortcuts
      if (event.key === 'Escape' && sidebarOpen) {
        setSidebarOpen(false)
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
              const routes = ['/', '/news-earnings', '/agents', '/paper-trading', '/ai-transparency', '/system-health', '/config', '/logs']
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
  }, [sidebarOpen])

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

      <div className="flex h-screen overflow-hidden bg-warmgray-50">
        {/* Mobile sidebar backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-warmgray-900/50 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setSidebarOpen(false)
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
            <Navigation onClose={() => setSidebarOpen(false)} />
          </div>
        </aside>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Mobile header */}
          <header
            className="flex h-14 items-center gap-4 border-b border-warmgray-300 bg-white/80 backdrop-blur-sm px-4 lg:hidden"
            role="banner"
          >
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden"
              aria-label="Open navigation menu"
              aria-expanded={sidebarOpen}
              aria-controls="sidebar"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </Button>
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded bg-copper-500 flex items-center justify-center" aria-hidden="true">
                <span className="text-white text-xs font-bold">R</span>
              </div>
              <span className="text-sm font-semibold text-warmgray-900">Robo Trader</span>
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
              <Route path="/news-earnings" element={<NewsEarningsFeature />} />
              <Route path="/agents" element={<AgentsFeature />} />
              <Route path="/paper-trading" element={<PaperTrading />} />
              <Route path="/config" element={<Config />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/ai-transparency" element={<AITransparencyFeature />} />
              <Route path="/system-health" element={<SystemHealthFeature />} />
            </Routes>
          </main>
        </div>

        <Toaster />

        {/* Claude AI Status Indicator - Fixed bottom left */}
        <ClaudeStatusIndicator />
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
