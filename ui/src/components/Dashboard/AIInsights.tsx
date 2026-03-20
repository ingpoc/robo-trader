import type { AIStatus } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/progress'
import { Brain, Activity, Zap, Clock, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AIInsightsProps {
  status?: AIStatus
}

export function AIInsights({ status }: AIInsightsProps) {
  const apiUsagePercent =
    status && status.daily_api_limit > 0
      ? (status.api_budget_used / status.daily_api_limit) * 100
      : 0
  const isHighUsage = apiUsagePercent > 75
  const isLowUsage = apiUsagePercent < 25

  const enhancedStatus = {
    portfolio_health:
      status?.portfolio_health || 'Operator health is unavailable until the backend dashboard payload loads.',
    current_task:
      status?.current_task || 'Claude runtime status is unavailable.',
    api_budget_used: status?.api_budget_used ?? 0,
    daily_api_limit: status?.daily_api_limit ?? 0,
    next_planned_task:
      status?.next_planned_task || 'Clear current blockers before queuing new automation.',
  }

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-3 font-bold">
          <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
            <Brain className="w-6 h-6" />
          </div>
          <span className="font-serif text-card-foreground">
            AI Insights
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-4">
          <div className="flex items-start gap-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="mt-0.5 rounded-lg bg-emerald-100 p-2">
              <Activity className="w-5 h-5 text-emerald-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="mb-2 text-sm font-bold uppercase tracking-wide text-emerald-800">Portfolio Health</div>
              <div className="text-sm font-medium leading-relaxed text-emerald-700">
                {enhancedStatus.portfolio_health}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 rounded-xl border border-border bg-muted/40 p-4">
            <div className="mt-0.5 rounded-lg bg-muted p-2">
              <TrendingUp className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="mb-2 text-sm font-bold uppercase tracking-wide text-foreground">Current Task</div>
              <div className="text-sm font-medium leading-relaxed text-muted-foreground">
                {enhancedStatus.current_task}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 rounded-xl border border-border bg-background p-4">
            <div className="mt-0.5 rounded-lg bg-muted p-2">
              <Zap className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="mb-3 text-sm font-bold uppercase tracking-wide text-foreground">API Usage</div>
              <div className="mb-3 text-sm font-semibold tabular-nums text-muted-foreground">
                {enhancedStatus.daily_api_limit > 0
                  ? `${enhancedStatus.api_budget_used} / ${enhancedStatus.daily_api_limit} calls today`
                  : 'Usage telemetry unavailable'}
              </div>
              <div className="space-y-3">
                <Progress
                  value={Math.min(apiUsagePercent, 100)}
                  className={cn(
                    "h-3 rounded-full shadow-inner",
                    isHighUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-slate-500 [&>div]:to-rose-500" :
                    isLowUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-emerald-500 [&>div]:to-teal-600" :
                    "[&>div]:bg-gradient-to-r [&>div]:from-blue-500 [&>div]:to-blue-600"
                  )}
                />
                <div className={cn("text-xs font-bold tabular-nums",
                  isHighUsage ? "text-red-600" :
                  isLowUsage ? "text-green-600" : "text-muted-foreground"
                )}>
                  {enhancedStatus.daily_api_limit > 0
                    ? `${apiUsagePercent.toFixed(1)}% of daily limit`
                    : 'No quota data reported'}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
            <div className="mt-0.5 rounded-lg bg-blue-100 p-2">
              <Clock className="w-5 h-5 text-blue-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="mb-2 text-sm font-bold uppercase tracking-wide text-blue-800">Next Task</div>
              <div className="text-sm font-medium leading-relaxed text-blue-700">
                {enhancedStatus.next_planned_task}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
