import { useLogs } from '@/hooks/useLogs'
import { formatDateTime } from '@/utils/format'

export function Logs() {
  const { data: logsData, isLoading, error } = useLogs()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg text-gray-600">Loading logs...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg text-red-600">Failed to load logs</div>
      </div>
    )
  }

  const logs = logsData?.logs || []

  return (
    <div className="flex flex-col gap-6 p-6 overflow-auto">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Logs</h1>
        <p className="text-sm text-gray-600">System activity and events</p>
      </div>

      <div className="flex flex-col gap-2 p-4 bg-white border border-gray-200 rounded">
        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No logs available</div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              className="flex items-start gap-4 p-3 border-b border-gray-100 last:border-0"
            >
              <div className="text-xs text-gray-500 font-mono">
                {formatDateTime(log.timestamp)}
              </div>
              <div
                className={`px-2 py-0.5 text-xs rounded ${
                  log.level === 'INFO'
                    ? 'bg-blue-100 text-blue-900'
                    : log.level === 'WARNING'
                      ? 'bg-yellow-100 text-yellow-900'
                      : log.level === 'ERROR'
                        ? 'bg-red-100 text-red-900'
                        : 'bg-gray-100 text-gray-900'
                }`}
              >
                {log.level}
              </div>
              <div className="flex-1 text-sm text-gray-900">{log.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
