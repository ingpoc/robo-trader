import React from 'react'
import { Activity, AlertTriangle, Database, ServerCog, Wifi, Zap } from 'lucide-react'

import { Breadcrumb } from '@/components/common/Breadcrumb'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

import { useSystemHealth } from './hooks/useSystemHealth'

type StatusTone = 'healthy' | 'degraded' | 'error' | 'idle' | 'inactive' | 'unknown'

const toneClasses: Record<StatusTone, string> = {
  healthy: 'bg-emerald-100 text-emerald-800',
  degraded: 'bg-amber-100 text-amber-800',
  error: 'bg-red-100 text-red-800',
  idle: 'bg-blue-100 text-blue-800',
  inactive: 'bg-slate-100 text-slate-800',
  unknown: 'bg-slate-100 text-slate-800',
}

function normalizeTone(status?: string | null): StatusTone {
  const value = String(status || 'unknown').toLowerCase()
  if (value === 'healthy') return 'healthy'
  if (value === 'degraded') return 'degraded'
  if (value === 'error') return 'error'
  if (value === 'idle') return 'idle'
  if (value === 'inactive') return 'inactive'
  return 'unknown'
}

function StatusBadge({ status }: { status?: string | null }) {
  const tone = normalizeTone(status)
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${toneClasses[tone]}`}>
      {tone}
    </span>
  )
}

function HealthCard({
  title,
  value,
  summary,
  status,
  icon,
}: {
  title: string
  value: string
  summary: string
  status?: string | null
  icon: React.ReactNode
}) {
  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between gap-3 text-base">
          <span className="flex items-center gap-2">
            {icon}
            {title}
          </span>
          <StatusBadge status={status} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-2xl font-semibold text-foreground">{value}</div>
        <p className="text-sm text-muted-foreground">{summary}</p>
      </CardContent>
    </Card>
  )
}

export const SystemHealthFeature: React.FC = () => {
  const {
    overallHealth,
    errors,
    isLoading,
    lastUpdate,
    dbHealth,
    websocketHealth,
    eventBusHealth,
    rawSystemStatus,
  } = useSystemHealth()

  const orchestrator = rawSystemStatus?.components?.orchestrator
  const blockers = rawSystemStatus?.blockers || []

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-6">
        <Breadcrumb />

        <PageHeader
          title="System Health"
          description="Only the components that affect whether Robo Trader is trustworthy and usable are shown here."
          icon={<Activity className="h-5 w-5" />}
        />

        <Card className="border-border bg-card shadow-sm">
          <CardContent className="flex flex-col gap-3 p-6 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <div className="text-sm font-medium text-muted-foreground">Operator Status</div>
              <div className="text-2xl font-semibold text-foreground capitalize">{overallHealth}</div>
              <div className="text-sm text-muted-foreground">
                {lastUpdate ? `Last updated ${new Date(lastUpdate).toLocaleTimeString()}` : 'Waiting for first health update.'}
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <StatusBadge status={overallHealth} />
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {blockers.length} blocker{blockers.length === 1 ? '' : 's'}
              </span>
            </div>
          </CardContent>
        </Card>

        {blockers.length > 0 ? (
          <Card className="border-amber-200 bg-amber-50/80 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-amber-900">
                <AlertTriangle className="h-5 w-5" />
                Active Blockers
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {blockers.map((blocker) => (
                <div key={blocker} className="rounded-md border border-amber-200 bg-white/70 px-3 py-2 text-sm text-amber-950">
                  {blocker}
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HealthCard
            title="Orchestrator"
            value={orchestrator?.initialized ? 'Ready' : 'Starting'}
            summary={orchestrator?.summary || 'Core runtime status unavailable.'}
            status={orchestrator?.status}
            icon={<ServerCog className="h-5 w-5" />}
          />
          <HealthCard
            title="Database"
            value={dbHealth?.healthy ? 'Connected' : 'Unavailable'}
            summary={dbHealth?.summary || dbHealth?.error || 'Database status unavailable.'}
            status={dbHealth?.status}
            icon={<Database className="h-5 w-5" />}
          />
          <HealthCard
            title="Event Bus"
            value={eventBusHealth?.status === 'healthy' ? 'Active' : 'Unavailable'}
            summary={eventBusHealth?.summary || 'Event bus status unavailable.'}
            status={eventBusHealth?.status}
            icon={<Zap className="h-5 w-5" />}
          />
          <HealthCard
            title="WebSocket"
            value={websocketHealth ? `${websocketHealth.clients} client${websocketHealth.clients === 1 ? '' : 's'}` : 'Unknown'}
            summary={websocketHealth?.summary || 'WebSocket status unavailable.'}
            status={websocketHealth?.status}
            icon={<Wifi className="h-5 w-5" />}
          />
        </div>

        <Card className="border-border bg-card shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Runtime Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div>
                <div className="font-medium text-foreground">Errors</div>
                <div>
                  {errors.length === 0
                    ? 'No current operator-facing errors.'
                    : `${errors.length} current issue${errors.length === 1 ? '' : 's'} are being tracked.`}
                </div>
              </div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {errors.length}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div>
                <div className="font-medium text-foreground">Transport</div>
                <div>
                  {websocketHealth?.summary || 'No transport status available.'}
                </div>
              </div>
              <StatusBadge status={websocketHealth?.status} />
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="text-sm text-muted-foreground">Refreshing health data...</div>
        ) : null}
      </div>
    </div>
  )
}

export default SystemHealthFeature
