import type { AIStatus } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/progress'
import { Brain, Activity, Zap, Clock, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AIInsightsProps {
  status?: AIStatus
}

export function AIInsights({ status }: AIInsightsProps) {
  const apiUsagePercent = status ? (status.api_budget_used / status.daily_api_limit) * 100 : 0
  const isHighUsage = apiUsagePercent > 75
  const isLowUsage = apiUsagePercent < 25

  return (
    <Card className="shadow-professional border-0 bg-gradient-to-br from-white/95 to-blue-50/70 backdrop-blur-sm hover:shadow-professional-hover transition-all duration-300 animate-slide-in-up ring-1 ring-blue-100/50">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-3 font-bold">
          <div className="p-3 bg-gradient-to-br from-blue-100 to-blue-200 rounded-xl shadow-sm">
            <Brain className="w-6 h-6 text-blue-700" />
          </div>
          <span className="bg-gradient-to-r from-blue-700 to-blue-600 bg-clip-text text-transparent">
            AI Insights
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-4">
          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-green-50/80 to-emerald-50/80 rounded-xl border border-green-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-green-100 to-green-200 rounded-lg shadow-sm mt-0.5">
              <Activity className="w-5 h-5 text-green-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-green-800 mb-2 uppercase tracking-wide">Portfolio Health</div>
              <div className="text-sm text-green-700 leading-relaxed font-medium">
                {status?.portfolio_health || 'Analyzing market conditions and portfolio performance...'}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 rounded-xl border border-blue-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-blue-100 to-blue-200 rounded-lg shadow-sm mt-0.5">
              <TrendingUp className="w-5 h-5 text-blue-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-blue-800 mb-2 uppercase tracking-wide">Current Task</div>
              <div className="text-sm text-blue-700 leading-relaxed font-medium">
                {status?.current_task || 'AI is planning optimal trading strategies...'}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-amber-50/80 to-orange-50/80 rounded-xl border border-amber-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-amber-100 to-amber-200 rounded-lg shadow-sm mt-0.5">
              <Zap className="w-5 h-5 text-amber-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-amber-800 mb-3 uppercase tracking-wide">API Usage</div>
              <div className="text-sm text-amber-700 tabular-nums mb-3 font-semibold">
                {status?.api_budget_used || 0} / {status?.daily_api_limit || 25} calls today
              </div>
              {status && (
                <div className="space-y-3">
                  <Progress
                    value={Math.min(apiUsagePercent, 100)}
                    className={cn(
                      "h-3 rounded-full shadow-inner",
                      isHighUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-amber-500 [&>div]:to-red-500" :
                      isLowUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-green-500 [&>div]:to-blue-500" :
                      "[&>div]:bg-gradient-to-r [&>div]:from-blue-500 [&>div]:to-blue-600"
                    )}
                  />
                  <div className={cn("text-xs font-bold tabular-nums",
                    isHighUsage ? "text-red-600" :
                    isLowUsage ? "text-green-600" : "text-blue-600"
                  )}>
                    {apiUsagePercent.toFixed(1)}% of daily limit
                    {isHighUsage && " ⚠️ High usage"}
                    {isLowUsage && " ✅ Low usage"}
                  </div>
                </div>
              )}
            </div>
          </div>

          {status?.next_planned_task && (
            <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-purple-50/80 to-violet-50/80 rounded-xl border border-purple-200/50 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="p-2 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg shadow-sm mt-0.5">
                <Clock className="w-5 h-5 text-purple-700" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-bold text-purple-800 mb-2 uppercase tracking-wide">Next Task</div>
                <div className="text-sm text-purple-700 leading-relaxed font-medium">
                  {status.next_planned_task}
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
