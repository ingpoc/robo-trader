/**
 * Resource Usage Component
 * Displays system resource utilization metrics
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Cpu, HardDrive, Zap } from 'lucide-react'

export interface ResourceUsageProps {
  resources: any | null
  isLoading: boolean
}

const ProgressBar: React.FC<{ value: number; label: string; icon: React.ReactNode }> = ({ value, label, icon }) => {
  const percentage = Math.min(100, Math.max(0, value))
  const getColor = (val: number) => {
    if (val >= 85) return 'bg-red-500'
    if (val >= 70) return 'bg-amber-500'
    return 'bg-emerald-500'
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-warmgray-700">{label}</span>
        </div>
        <span className="font-semibold">{percentage.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-warmgray-200 rounded-full h-2 overflow-hidden">
        <div className={`h-full ${getColor(percentage)} transition-all duration-300`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

export const ResourceUsage: React.FC<ResourceUsageProps> = ({ resources, isLoading }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading resource metrics...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Resources</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <ProgressBar value={resources?.cpu || 0} label="CPU Usage" icon={<Cpu className="w-5 h-5 text-warmgray-600" />} />
        <ProgressBar value={resources?.memory || 0} label="Memory Usage" icon={<Zap className="w-5 h-5 text-warmgray-600" />} />
        <ProgressBar value={resources?.disk || 0} label="Disk Usage" icon={<HardDrive className="w-5 h-5 text-warmgray-600" />} />
      </CardContent>
    </Card>
  )
}

export default ResourceUsage
