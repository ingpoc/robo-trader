/**
 * Stock Discovery Feature Component
 * PT-002: Autonomous Stock Discovery
 * Displays discovered stocks and allows triggering discovery sessions
 */

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Search,
  TrendingUp,
  Clock,
  Target,
  RefreshCw,
  Play,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { DiscoveryWatchlist } from './DiscoveryWatchlist'
import { DiscoverySessions } from './DiscoverySessions'
import { DiscoveryControlPanel } from './DiscoveryControlPanel'
import type {
  DiscoveryStatus,
  DiscoveryWatchlistResponse,
  DiscoverySessionsResponse
} from './types'

export interface StockDiscoveryFeatureProps {
  className?: string
}

export const StockDiscoveryFeature: React.FC<StockDiscoveryFeatureProps> = ({
  className = ''
}) => {
  const [status, setStatus] = useState<DiscoveryStatus | null>(null)
  const [watchlist, setWatchlist] = useState<DiscoveryWatchlistResponse | null>(null)
  const [sessions, setSessions] = useState<DiscoverySessionsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDiscoveryStatus = async () => {
    try {
      const response = await fetch('/api/paper-trading/discovery/status')
      const data = await response.json()
      if (data.success) {
        setStatus(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch discovery status:', err)
      setError('Failed to fetch discovery status')
    }
  }

  const fetchWatchlist = async (limit: number = 50) => {
    try {
      const response = await fetch(`/api/paper-trading/discovery/watchlist?limit=${limit}`)
      const data = await response.json()
      if (data.success) {
        setWatchlist(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch watchlist:', err)
      setError('Failed to fetch watchlist')
    }
  }

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/paper-trading/discovery/sessions')
      const data = await response.json()
      if (data.success) {
        setSessions(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
      setError('Failed to fetch discovery sessions')
    }
  }

  const refreshAll = async () => {
    setIsLoading(true)
    setError(null)
    try {
      await Promise.all([
        fetchDiscoveryStatus(),
        fetchWatchlist(),
        fetchSessions()
      ])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshAll()
  }, [])

  const getStatusIcon = (running: boolean) => {
    if (running) {
      return <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
    }
    return status?.current_session?.session_status === 'COMPLETED'
      ? <CheckCircle className="w-4 h-4 text-green-500" />
      : <XCircle className="w-4 h-4 text-gray-400" />
  }

  const getStatusText = () => {
    if (status?.discovery_running) {
      return `Discovery in progress... (${status.current_session?.stocks_discovered || 0} stocks found)`
    }
    if (status?.current_session?.session_status === 'COMPLETED') {
      return `Last discovery: ${status.current_session.stocks_discovered} stocks found`
    }
    return 'No discovery sessions run yet'
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <Search className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Stock Discovery
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              AI-powered stock screening and watchlist management
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          onClick={refreshAll}
          disabled={isLoading}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Status Overview */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Discovery Status</h3>
          {getStatusIcon(status?.discovery_running || false)}
        </div>
        <p className="text-gray-600 dark:text-gray-400 mb-4">{getStatusText()}</p>

        {status && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {status.total_sessions}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Sessions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {status.total_stocks_scanned}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Stocks Scanned</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {status.total_stocks_discovered}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Stocks Found</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {watchlist?.total_stocks || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Watchlisted</div>
            </div>
          </div>
        )}
      </Card>

      {/* Control Panel */}
      <DiscoveryControlPanel
        onDiscoveryTriggered={refreshAll}
        isDiscoveryRunning={status?.discovery_running || false}
      />

      {/* Tabs */}
      <Tabs defaultValue="watchlist" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="watchlist" className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            <span>Watchlist</span>
            <Badge variant="secondary" className="ml-1">
              {watchlist?.total_stocks || 0}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="sessions" className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>Sessions</span>
            <Badge variant="secondary" className="ml-1">
              {sessions?.total_sessions || 0}
            </Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="watchlist">
          <DiscoveryWatchlist
            watchlist={watchlist}
            isLoading={isLoading}
            onRefresh={fetchWatchlist}
          />
        </TabsContent>

        <TabsContent value="sessions">
          <DiscoverySessions
            sessions={sessions}
            isLoading={isLoading}
            onRefresh={fetchSessions}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default StockDiscoveryFeature