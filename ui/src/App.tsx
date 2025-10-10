import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Navigation } from '@/components/Sidebar/Navigation'
import { Toaster } from '@/components/common/Toaster'
import { GlobalErrorBoundary } from '@/components/common/GlobalErrorBoundary'
import { WebSocketErrorBoundary } from '@/components/common/WebSocketErrorBoundary'
import { DashboardErrorBoundary } from '@/components/common/DashboardErrorBoundary'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Dashboard } from '@/pages/Dashboard'
import { Agents } from '@/pages/Agents'
import { Trading } from '@/pages/Trading'
import { Config } from '@/pages/Config'
import { Logs } from '@/pages/Logs'
import { AgentConfig } from '@/pages/AgentConfig'

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

  return (
    <WebSocketErrorBoundary>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        <aside className="w-64 flex-shrink-0">
          <Navigation />
        </aside>
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardErrorBoundary><Dashboard /></DashboardErrorBoundary>} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/trading" element={<Trading />} />
            <Route path="/config" element={<Config />} />
            <Route path="/agent-config" element={<AgentConfig />} />
            <Route path="/logs" element={<Logs />} />
          </Routes>
        </main>
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
          <AppContent />
        </BrowserRouter>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  )
}
