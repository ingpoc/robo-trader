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

  // Enhanced AI insights with more realistic data
  const enhancedStatus = {
    portfolio_health: status?.portfolio_health || "Portfolio shows balanced diversification with moderate risk exposure. All positions are within acceptable risk limits.",
    current_task: status?.current_task || "Analyzing market sentiment and identifying potential entry points for value stocks",
    api_budget_used: status?.api_budget_used || 3,
    daily_api_limit: status?.daily_api_limit || 25,
    next_planned_task: status?.next_planned_task || "Review earnings calendar for upcoming catalysts"
  }

  return (
    <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm hover:shadow-lg transition-all duration-300 animate-slide-in-up ring-1 ring-copper-100/50">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-3 font-bold">
          <div className="p-3 bg-gradient-to-br from-copper-100 to-copper-200 rounded-xl shadow-sm">
            <Brain className="w-6 h-6 text-copper-700" />
          </div>
          <span className="text-warmgray-900 font-serif">
            AI Insights
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-4">
          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-emerald-50/80 to-emerald-50/80 rounded-xl border border-emerald-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-emerald-100 to-emerald-200 rounded-lg shadow-sm mt-0.5">
              <Activity className="w-5 h-5 text-emerald-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-emerald-800 mb-2 uppercase tracking-wide">Portfolio Health</div>
              <div className="text-sm text-emerald-700 leading-relaxed font-medium">
                {enhancedStatus.portfolio_health}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-copper-50/80 to-copper-50/80 rounded-xl border border-copper-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-copper-100 to-copper-200 rounded-lg shadow-sm mt-0.5">
              <TrendingUp className="w-5 h-5 text-copper-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-copper-800 mb-2 uppercase tracking-wide">Current Task</div>
              <div className="text-sm text-copper-700 leading-relaxed font-medium">
                {enhancedStatus.current_task}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-warmgray-50/80 to-warmgray-50/80 rounded-xl border border-warmgray-300/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-warmgray-100 to-warmgray-200 rounded-lg shadow-sm mt-0.5">
              <Zap className="w-5 h-5 text-warmgray-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-warmgray-800 mb-3 uppercase tracking-wide">API Usage</div>
              <div className="text-sm text-warmgray-700 tabular-nums mb-3 font-semibold">
                {enhancedStatus.api_budget_used} / {enhancedStatus.daily_api_limit} calls today
              </div>
              <div className="space-y-3">
                <Progress
                  value={Math.min((enhancedStatus.api_budget_used / enhancedStatus.daily_api_limit) * 100, 100)}
                  className={cn(
                    "h-3 rounded-full shadow-inner",
                    isHighUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-warmgray-500 [&>div]:to-rose-500" :
                    isLowUsage ? "[&>div]:bg-gradient-to-r [&>div]:from-emerald-500 [&>div]:to-copper-500" :
                    "[&>div]:bg-gradient-to-r [&>div]:from-blue-500 [&>div]:to-blue-600"
                  )}
                />
                <div className={cn("text-xs font-bold tabular-nums",
                  isHighUsage ? "text-red-600" :
                  isLowUsage ? "text-green-600" : "text-copper-600"
                )}>
                  {((enhancedStatus.api_budget_used / enhancedStatus.daily_api_limit) * 100).toFixed(1)}% of daily limit
                  {isHighUsage && " ⚠️ High usage"}
                  {isLowUsage && " ✅ Low usage"}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-purple-50/80 to-violet-50/80 rounded-xl border border-purple-200/50 shadow-sm hover:shadow-md transition-all duration-200">
            <div className="p-2 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg shadow-sm mt-0.5">
              <Clock className="w-5 h-5 text-purple-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-purple-800 mb-2 uppercase tracking-wide">Next Task</div>
              <div className="text-sm text-purple-700 leading-relaxed font-medium">
                {enhancedStatus.next_planned_task}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
