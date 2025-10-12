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

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-white to-blue-50/50 backdrop-blur-sm hover:shadow-xl transition-all duration-300">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="w-5 h-5 text-blue-600" />
          </div>
          AI Insights
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-100">
            <div className="p-1.5 bg-green-100 rounded-md mt-0.5">
              <Activity className="w-4 h-4 text-green-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-green-800 mb-1">Portfolio Health</div>
              <div className="text-sm text-green-700 leading-relaxed">
                {status?.portfolio_health || 'Analyzing market conditions...'}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
            <div className="p-1.5 bg-blue-100 rounded-md mt-0.5">
              <TrendingUp className="w-4 h-4 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-blue-800 mb-1">Current Task</div>
              <div className="text-sm text-blue-700 leading-relaxed">
                {status?.current_task || 'Planning analysis...'}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-100">
            <div className="p-1.5 bg-amber-100 rounded-md mt-0.5">
              <Zap className="w-4 h-4 text-amber-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-amber-800 mb-2">API Usage</div>
              <div className="text-sm text-amber-700 tabular-nums mb-2">
                {status?.api_budget_used || 0}/{status?.daily_api_limit || 25} calls today
              </div>
              {status && (
                <div className="space-y-2">
                  <Progress
                    value={Math.min(apiUsagePercent, 100)}
                    className={cn(
                      "h-2",
                      isHighUsage ? "[&>div]:bg-amber-500" : "[&>div]:bg-green-500"
                    )}
                  />
                  <div className="text-xs text-amber-600">
                    {apiUsagePercent.toFixed(1)}% of daily limit
                  </div>
                </div>
              )}
            </div>
          </div>

          {status?.next_planned_task && (
            <div className="flex items-start gap-3 p-3 bg-gradient-to-r from-purple-50 to-violet-50 rounded-lg border border-purple-100">
              <div className="p-1.5 bg-purple-100 rounded-md mt-0.5">
                <Clock className="w-4 h-4 text-purple-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-purple-800 mb-1">Next Task</div>
                <div className="text-sm text-purple-700 leading-relaxed">
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
