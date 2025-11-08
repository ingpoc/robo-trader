/**
 * Error Alerts Component
 * Displays recent system errors and alerts from queue failures and system issues
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { AlertCircle, AlertTriangle, Info } from 'lucide-react'

export interface FormattedError {
  component: string
  message: string
  severity: 'critical' | 'warning' | 'info'
  timestamp: string
}

export interface ErrorAlertsProps {
  errors: (string | FormattedError)[] | null
  isLoading: boolean
}

/**
 * Format string errors into structured error objects
 * Detects failed tasks and maps them to appropriate severity
 */
const formatError = (error: string | FormattedError): FormattedError => {
  // Already formatted
  if (typeof error === 'object') {
    return error
  }

  // Parse failed_tasks errors
  const failedTasksMatch = error.match(/Queue "([^"]+)" has (\d+) failed task\(s\)/)
  if (failedTasksMatch) {
    const [, queueName, taskCount] = failedTasksMatch
    return {
      component: `Queue: ${queueName}`,
      message: `${taskCount} task(s) failed in the ${queueName} queue`,
      severity: 'critical',
      timestamp: new Date().toISOString()
    }
  }

  // Parse total failed tasks
  const totalFailedMatch = error.match(/System has (\d+) total failed task\(s\)/)
  if (totalFailedMatch) {
    const [, taskCount] = totalFailedMatch
    return {
      component: 'System Queue Status',
      message: `${taskCount} total task(s) have failed across all queues`,
      severity: 'critical',
      timestamp: new Date().toISOString()
    }
  }

  // WebSocket errors
  if (error.includes('WebSocket')) {
    return {
      component: 'WebSocket Connection',
      message: error,
      severity: 'warning',
      timestamp: new Date().toISOString()
    }
  }

  // Server shutdown
  if (error.includes('shutdown')) {
    return {
      component: 'Server',
      message: error,
      severity: 'critical',
      timestamp: new Date().toISOString()
    }
  }

  // Default error formatting
  return {
    component: 'System',
    message: error,
    severity: 'warning',
    timestamp: new Date().toISOString()
  }
}

export const ErrorAlerts: React.FC<ErrorAlertsProps> = ({ errors, isLoading }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading error logs...</p>
        </CardContent>
      </Card>
    )
  }

  if (!errors || errors.length === 0) {
    return (
      <Card className="border-l-4 border-l-emerald-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-emerald-600">
            <AlertCircle className="w-5 h-5" />
            All Systems Healthy
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-warmgray-600">No recent errors or alerts detected</p>
        </CardContent>
      </Card>
    )
  }

  // Format all errors for display
  const formattedErrors = errors.map(formatError)

  // Sort by severity (critical first)
  const severityOrder = { critical: 0, warning: 1, info: 2 }
  const sortedErrors = [...formattedErrors].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  )

  return (
    <div className="grid grid-cols-1 gap-4">
      {sortedErrors.map((error, index) => (
        <Card
          key={index}
          className={`border-l-4 ${
            error.severity === 'critical'
              ? 'border-l-red-500'
              : error.severity === 'warning'
              ? 'border-l-amber-500'
              : 'border-l-blue-500'
          }`}
        >
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              {error.severity === 'critical' ? (
                <AlertCircle className="w-5 h-5 text-red-600" />
              ) : error.severity === 'warning' ? (
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              ) : (
                <Info className="w-5 h-5 text-blue-600" />
              )}
              {error.component}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-warmgray-700 dark:text-warmgray-300">
              {error.message}
            </p>
            <div className="flex justify-between items-center text-sm">
              <span className="text-warmgray-600 dark:text-warmgray-400">
                {new Date(error.timestamp).toLocaleTimeString()}
              </span>
              <span
                className={`px-3 py-1 rounded-full font-semibold text-xs ${
                  error.severity === 'critical'
                    ? 'bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-200'
                    : error.severity === 'warning'
                    ? 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200'
                    : 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-200'
                }`}
              >
                {error.severity?.toUpperCase()}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default ErrorAlerts
