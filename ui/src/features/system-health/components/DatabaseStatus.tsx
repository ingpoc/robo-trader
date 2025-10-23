/**
 * Database Status Component
 * Displays database connection and health metrics
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { CheckCircle, AlertTriangle } from 'lucide-react'

export interface DatabaseStatusProps {
  health: any | null
  isLoading: boolean
}

export const DatabaseStatus: React.FC<DatabaseStatusProps> = ({ health, isLoading }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading database status...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          {health?.healthy ? (
            <CheckCircle className="w-5 h-5 text-emerald-600" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-red-600" />
          )}
          Database Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Connection</span>
          <span className={`px-3 py-1 rounded-full font-semibold text-sm ${
            health?.healthy ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
          }`}>
            {health?.healthy ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Active Connections</span>
          <span className="font-semibold">{health?.activeConnections || 0}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-warmgray-700">Query Latency</span>
          <span className="text-sm text-warmgray-600">{health?.latency || 'N/A'}ms</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default DatabaseStatus
