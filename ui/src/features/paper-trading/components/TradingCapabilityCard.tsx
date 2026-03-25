import React from 'react'
import { Activity, Bot, Radio, ShieldAlert, Wallet } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'

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
  claude_runtime: Bot,
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
      <Card>
        <CardHeader>
          <CardTitle>Automation Readiness</CardTitle>
          <CardDescription>Checking automation and position-monitoring prerequisites.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <div
                key={index}
                className="h-24 animate-pulse rounded-xl border border-warmgray-200 bg-warmgray-100/70 dark:border-warmgray-700 dark:bg-warmgray-800/60"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!snapshot) {
    return null
  }

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Automation Readiness</CardTitle>
            <CardDescription>
              This card tracks automation and position mark-to-market readiness. Discovery and single-candidate research can
              still work without live ticks, but automated monitoring depends on fresh quotes, Claude availability, and
              explicit account state.
            </CardDescription>
          </div>
          <Badge variant={statusVariantMap[snapshot.overall_status]} size="sm" className="uppercase">
            {snapshot.overall_status}
          </Badge>
        </div>

        {snapshot.blockers.length > 0 && (
          <Alert variant="destructive">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Automation intervention required</AlertTitle>
            <AlertDescription>
              {snapshot.blockers[0]}
            </AlertDescription>
          </Alert>
        )}
      </CardHeader>

      <CardContent className="grid gap-3 md:grid-cols-2">
        {snapshot.checks.map((check) => {
          const Icon = iconMap[check.key as keyof typeof iconMap] ?? ShieldAlert
          return (
            <div
              key={check.key}
              className="rounded-xl border border-warmgray-200 bg-white/70 p-4 dark:border-warmgray-700 dark:bg-warmgray-900/40"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Icon className="mt-0.5 h-4 w-4 text-copper-500" />
                  <div>
                    <p className="text-sm font-semibold text-warmgray-900 dark:text-warmgray-100">
                      {check.label}
                    </p>
                    <p className="mt-1 text-sm text-warmgray-700 dark:text-warmgray-300">
                      {check.summary}
                    </p>
                  </div>
                </div>
                <Badge variant={statusVariantMap[check.status]} size="xs" className="uppercase">
                  {check.status}
                </Badge>
              </div>

              {check.detail && (
                <p className="mt-3 text-xs leading-5 text-warmgray-600 dark:text-warmgray-400">
                  {check.detail}
                </p>
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
