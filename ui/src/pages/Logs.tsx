import { useState } from 'react'
import { useLogs } from '@/hooks/useLogs'
import { formatDateTime } from '@/utils/format'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { FileText, Filter, RefreshCw, AlertCircle, Info, AlertTriangle, XCircle } from 'lucide-react'

export function Logs() {
  const { data: logsData, isLoading, error, refetch } = useLogs()
  const [filterLevel, setFilterLevel] = useState<string>('all')

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-6 animate-fade-in-luxury bg-warmgray-50 min-h-screen">
        <Breadcrumb />
        <div className="flex flex-col gap-4">
          <SkeletonLoader className="h-8 w-48" />
          <SkeletonLoader className="h-4 w-64" />
        </div>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <SkeletonLoader className="h-6 w-32" />
              <SkeletonLoader className="h-8 w-24" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-start gap-4 p-3 border border-warmgray-200 rounded">
                <SkeletonLoader className="h-4 w-16" />
                <SkeletonLoader className="h-4 w-12" />
                <SkeletonLoader className="h-4 flex-1" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-6 animate-fade-in-luxury bg-warmgray-50 min-h-screen">
        <Breadcrumb />
        <Card className="shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-12 h-12 text-rose-600 mb-4" />
            <h3 className="text-lg font-medium text-warmgray-900 dark:text-white mb-2">Failed to Load Logs</h3>
            <p className="text-sm text-warmgray-600 dark:text-warmgray-400 text-center mb-4">
              There was an error loading the system logs. Please try again.
            </p>
            <Button onClick={() => refetch()} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const logs = logsData?.logs || []
  const filteredLogs = filterLevel === 'all'
    ? logs
    : logs.filter(log => log.level.toLowerCase() === filterLevel.toLowerCase())

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'ERROR':
        return <XCircle className="w-4 h-4 text-rose-500" />
      case 'WARNING':
        return <AlertTriangle className="w-4 h-4 text-copper-500" />
      case 'INFO':
        return <Info className="w-4 h-4 text-emerald-500" />
      default:
        return <Info className="w-4 h-4 text-warmgray-500" />
    }
  }

  const getLogBadgeColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'bg-rose-50 text-rose-900 dark:bg-rose-900 dark:text-rose-200'
      case 'WARNING':
        return 'bg-copper-50 text-copper-900 dark:bg-copper-900 dark:text-copper-200'
      case 'INFO':
        return 'bg-emerald-50 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-200'
      default:
        return 'bg-warmgray-100 text-warmgray-900 dark:bg-warmgray-800 dark:text-warmgray-200'
    }
  }

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto bg-warmgray-50 min-h-screen">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-warmgray-900 font-serif">System Logs</h1>
            <p className="text-lg text-warmgray-600 mt-1">Monitor system activity and events</p>
          </div>
          <Button
            onClick={() => refetch()}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-copper-500" />
              Log Entries ({filteredLogs.length})
            </CardTitle>
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
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-warmgray-900 dark:text-white mb-2">No Logs Found</h3>
              <p className="text-sm text-warmgray-600 dark:text-warmgray-400">
                {filterLevel === 'all'
                  ? 'No log entries are available at this time.'
                  : `No ${filterLevel} level logs found.`
                }
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredLogs.map((log, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-3 border border-warmgray-300 dark:border-warmgray-700 rounded-lg hover:bg-warmgray-50 dark:hover:bg-warmgray-800 transition-colors"
                >
                  <div className="text-xs text-warmgray-500 dark:text-warmgray-400 font-mono min-w-0 flex-shrink-0 mt-0.5">
                    {formatDateTime(log.timestamp)}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {getLogIcon(log.level)}
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${getLogBadgeColor(log.level)}`}>
                      {log.level}
                    </span>
                  </div>
                  <div className="flex-1 text-sm text-warmgray-900 dark:text-warmgray-100 break-words min-w-0">
                    {log.message}
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