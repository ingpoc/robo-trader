/**
 * System Health Logs Component
 * Displays system logs filtered for system health context
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { cn } from '@/utils/cn'
import { FileText, Filter, RefreshCw, AlertCircle, Info, AlertTriangle, XCircle, Activity } from 'lucide-react'

interface LogEntry {
  timestamp: string
  level: 'ERROR' | 'WARNING' | 'INFO' | 'DEBUG'
  message: string
  source?: string
  component?: string
}

interface SystemHealthLogsProps {
  isLoading?: boolean
}

export const SystemHealthLogs: React.FC<SystemHealthLogsProps> = ({ isLoading = false }) => {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filterLevel, setFilterLevel] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch system health logs
  const fetchLogs = async () => {
    try {
      setLoading(true)
      setError(null)

      // For now, use the same logs endpoint as the main Logs page
      // In the future, this could be enhanced to filter for system-health specific logs
      const response = await fetch('/api/logs')

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setLogs(data.logs || [])
    } catch (err) {
      console.error('Failed to fetch system health logs:', err)
      setError(err instanceof Error ? err.message : 'Failed to load logs')
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()

    // Set up polling for real-time updates (every 30 seconds for logs)
    const interval = setInterval(fetchLogs, 30000)

    return () => {
      clearInterval(interval)
    }
  }, [])

  const filteredLogs = filterLevel === 'all'
    ? logs
    : logs.filter(log => log.level.toLowerCase() === filterLevel.toLowerCase())

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'ERROR':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'WARNING':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />
      case 'INFO':
        return <Info className="w-4 h-4 text-emerald-600" />
      default:
        return <Activity className="w-4 h-4 text-warmgray-400" />
    }
  }

  const getLogBadgeColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'WARNING':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'INFO':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'
      default:
        return 'bg-warmgray-100 text-warmgray-800 border-warmgray-200'
    }
  }

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString()
    } catch {
      return timestamp
    }
  }

  const getSystemHealthLogs = () => {
    // Filter logs that are most relevant to system health
    return logs.filter(log =>
      log.message.toLowerCase().includes('system') ||
      log.message.toLowerCase().includes('queue') ||
      log.message.toLowerCase().includes('scheduler') ||
      log.message.toLowerCase().includes('database') ||
      log.message.toLowerCase().includes('coordinator') ||
      log.message.toLowerCase().includes('websocket') ||
      log.level === 'ERROR' ||
      log.level === 'WARNING'
    ).slice(0, 50) // Limit to most recent 50 relevant logs
  }

  const displayLogs = filterLevel === 'all' ? getSystemHealthLogs() : filteredLogs

  if (isLoading || loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-warmgray-200 rounded w-1/4"></div>
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-3 bg-warmgray-100 rounded"></div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-400" />
            <p className="text-red-600 font-medium mb-2">Failed to load system logs</p>
            <p className="text-sm text-warmgray-500 mb-4">{error}</p>
            <Button onClick={fetchLogs} variant="tertiary" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Logs Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-600" />
              System Health Logs
            </span>
            <span className={`text-sm font-normal ${
              displayLogs.filter(log => log.level === 'ERROR').length > 0
                ? 'text-red-600'
                : displayLogs.filter(log => log.level === 'WARNING').length > 0
                  ? 'text-amber-600'
                  : 'text-emerald-600'
            }`}>
              {displayLogs.filter(log => log.level === 'ERROR').length > 0 &&
                `${displayLogs.filter(log => log.level === 'ERROR').length} errors • `
              }
              {displayLogs.filter(log => log.level === 'WARNING').length > 0 &&
                `${displayLogs.filter(log => log.level === 'WARNING').length} warnings • `
              }
              {displayLogs.length} relevant entries
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <p className="text-sm text-warmgray-600">
              System logs filtered for health monitoring events, errors, and warnings
            </p>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-warmgray-500" />
              <Select
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value)}
                className="w-32"
                options={[
                  { value: 'all', label: 'All Levels' },
                  { value: 'error', label: 'Errors' },
                  { value: 'warning', label: 'Warnings' },
                  { value: 'info', label: 'Info' },
                ]}
              />
              <Button
                onClick={fetchLogs}
                variant="tertiary"
                size="sm"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Display */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-warmgray-600" />
            Recent System Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {displayLogs.length === 0 ? (
            <div className="text-center py-8">
              <Activity className="w-8 h-8 mx-auto mb-2 text-warmgray-400" />
              <p className="text-warmgray-500">
                {filterLevel === 'all'
                  ? 'No system health events found. System is running smoothly.'
                  : `No ${filterLevel} level events found.`
                }
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {displayLogs.map((log, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-3 bg-warmgray-50/50 dark:bg-warmgray-900/50 rounded-lg border border-warmgray-200 dark:border-warmgray-700"
                >
                  <div className="text-xs text-warmgray-500 font-mono min-w-0 flex-shrink-0 mt-0.5">
                    {formatTime(log.timestamp)}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {getLogIcon(log.level)}
                    <span className={cn(
                      "text-xs px-2 py-1 rounded-full font-medium border",
                      getLogBadgeColor(log.level)
                    )}>
                      {log.level}
                    </span>
                  </div>
                  <div className="flex-1 text-sm text-warmgray-900 dark:text-warmgray-100 break-words min-w-0">
                    {log.message}
                    {log.component && (
                      <span className="text-xs text-warmgray-500 ml-2">
                        ({log.component})
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default SystemHealthLogs