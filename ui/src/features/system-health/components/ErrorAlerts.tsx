/**
 * Error Alerts Component
 * Displays recent system errors and alerts
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { AlertCircle, AlertTriangle, Info } from 'lucide-react'

export interface ErrorAlertsProps {
  errors: any[] | null
  isLoading: boolean
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

  return (
    <div className="grid grid-cols-1 gap-4">
      {errors.map((error, index) => (
        <Card key={index} className="border-l-4 border-l-red-500">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              {error.severity === 'critical' ? (
                <AlertCircle className="w-5 h-5 text-red-600" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              )}
              {error.component}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-warmgray-600">{error.message}</p>
            <div className="flex justify-between items-center text-sm">
              <span className="text-warmgray-600">
                {new Date(error.timestamp).toLocaleTimeString()}
              </span>
              <span className={`px-3 py-1 rounded-full font-semibold text-xs ${
                error.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
              }`}>
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
