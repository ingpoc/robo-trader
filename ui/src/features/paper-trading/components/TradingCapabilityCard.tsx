import { Activity, Bot, Radio, ShieldAlert, Wallet } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Card, CardContent } from '@/components/ui/Card'

import type { CapabilityStatus, TradingCapabilitySnapshot } from '../types'

interface TradingCapabilityCardProps {
  snapshot: TradingCapabilitySnapshot | null
  isLoading?: boolean
}

const statusVariantMap: Record<CapabilityStatus, 'success' | 'warning' | 'error'> = {
  ready: 'success',
  degraded: 'warning',
  blocked: 'error',
}

const iconMap = {
  ai_runtime: Bot,
  quote_stream: Radio,
  broker_auth: ShieldAlert,
  market_data: Activity,
  paper_account: Wallet,
} as const

export function TradingCapabilityCard({
  snapshot,
  isLoading = false,
}: TradingCapabilityCardProps) {
  if (isLoading && !snapshot) {
    return (
      <Card className="overflow-hidden border-border/70 bg-white/80 dark:bg-warmgray-800/80">
        <CardContent className="grid gap-0 p-0 md:grid-cols-[1.4fr_repeat(5,minmax(0,1fr))]">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse border-t border-border/70 bg-muted/30 first:border-t-0 md:border-l md:border-t-0 md:first:border-l-0" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (!snapshot) {
    return null
  }

  return (
    <Card className="overflow-hidden border-border/70 bg-white/80 dark:bg-warmgray-800/80">
      <CardContent className="grid gap-0 p-0 lg:grid-cols-[1.35fr_repeat(5,minmax(0,1fr))]">
        <div className="border-b border-border/70 px-6 py-5 lg:border-b-0 lg:border-r">
          <p className="desk-kicker">Automation Readiness</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold text-foreground">Mission status</h2>
            <Badge variant={statusVariantMap[snapshot.overall_status]} size="xs">
              {snapshot.overall_status}
            </Badge>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Discovery and focused research can run with fewer dependencies than automated monitoring. This strip shows what is actually green right now.
          </p>
          {snapshot.blockers.length ? (
            <p className="mt-3 text-sm leading-6 text-rose-700">{snapshot.blockers[0]}</p>
          ) : (
            <p className="mt-3 text-sm leading-6 text-emerald-700">All current automation gates are satisfied for the selected paper account.</p>
          )}
        </div>

        {snapshot.checks.map(check => {
          const Icon = iconMap[check.key as keyof typeof iconMap] ?? ShieldAlert
          return (
            <div key={check.key} className="border-b border-border/70 px-5 py-5 last:border-b-0 lg:border-b-0 lg:border-l">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    <span className="text-sm font-semibold text-foreground">{check.label}</span>
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">{check.summary}</p>
                </div>
                <Badge variant={statusVariantMap[check.status]} size="xs">
                  {check.status}
                </Badge>
              </div>
              {check.detail ? (
                <p className="mt-3 text-xs leading-5 text-muted-foreground">{check.detail}</p>
              ) : null}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
