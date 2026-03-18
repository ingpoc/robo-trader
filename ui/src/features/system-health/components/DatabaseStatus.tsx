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
      <Card className="border-border bg-card shadow-sm">
        <CardContent className="pt-6">
          <p className="text-muted-foreground">Loading database status...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border bg-card shadow-sm">
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
          <span className="text-muted-foreground">Connection</span>
          <span className={`px-3 py-1 rounded-full font-semibold text-sm ${
            health?.healthy ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
          }`}>
            {health?.healthy ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Active Connections</span>
          <span className="font-semibold text-foreground">{health?.activeConnections || 0}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Status Detail</span>
          <span className="text-sm text-muted-foreground text-right">
            {health?.error || health?.summary || 'No additional detail'}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default DatabaseStatus
