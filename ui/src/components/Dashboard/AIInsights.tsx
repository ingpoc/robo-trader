import type { AIStatus } from '@/types/api'

interface AIInsightsProps {
  status?: AIStatus
}

export function AIInsights({ status }: AIInsightsProps) {
  return (
    <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
      <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <div className="text-sm font-medium text-gray-700">Portfolio Health</div>
          <div className="text-sm text-gray-600">
            {status?.portfolio_health || 'Analyzing market conditions...'}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <div className="text-sm font-medium text-gray-700">Current Task</div>
          <div className="text-sm text-gray-600">
            {status?.current_task || 'Planning analysis...'}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <div className="text-sm font-medium text-gray-700">API Usage</div>
          <div className="text-sm text-gray-600">
            {status?.api_budget_used || 0}/{status?.daily_api_limit || 25} calls today
          </div>
          {status && (
            <div className="mt-1 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent transition-all duration-300"
                style={{
                  width: `${Math.min(
                    (status.api_budget_used / status.daily_api_limit) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
          )}
        </div>

        {status?.next_planned_task && (
          <div className="flex flex-col gap-1">
            <div className="text-sm font-medium text-gray-700">Next Task</div>
            <div className="text-sm text-gray-600">{status.next_planned_task}</div>
          </div>
        )}
      </div>
    </div>
  )
}
