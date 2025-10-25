/**
 * Scheduler Status Component
 * Displays status of all background schedulers
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { CheckCircle, AlertTriangle } from 'lucide-react'

export interface SchedulerStatusProps {
  status: any | null
  isLoading: boolean
}

export const SchedulerStatus: React.FC<SchedulerStatusProps> = ({ status, isLoading }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading scheduler status...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            {status?.healthy ? (
              <CheckCircle className="w-5 h-5 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-600" />
            )}
            Scheduler Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-warmgray-700">Status</span>
              <span className={`px-3 py-1 rounded-full font-semibold ${
                status?.healthy ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
              }`}>
                {status?.healthy ? 'Healthy' : 'Error'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-warmgray-700">Last Run</span>
              <span className="text-sm text-warmgray-600">
                {status?.lastRun ? new Date(status.lastRun).toLocaleTimeString() : 'N/A'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SchedulerStatus
