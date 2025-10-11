import type { AIStatus } from '@/types/api'

interface AIInsightsProps {
  status?: AIStatus
}

export function AIInsights({ status }: AIInsightsProps) {
  return (
    <div className="flex flex-col gap-2 p-4 bg-white border border-gray-200 card-shadow">
      <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">AI Insights</div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-0.5">
          <div className="text-11 font-medium text-gray-500 uppercase tracking-wider">Portfolio Health</div>
          <div className="text-13 text-gray-700">
            {status?.portfolio_health || 'Analyzing market conditions...'}
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <div className="text-11 font-medium text-gray-500 uppercase tracking-wider">Current Task</div>
          <div className="text-13 text-gray-700">
            {status?.current_task || 'Planning analysis...'}
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <div className="text-11 font-medium text-gray-500 uppercase tracking-wider">API Usage</div>
          <div className="text-13 text-gray-700 tabular-nums">
            {status?.api_budget_used || 0}/{status?.daily_api_limit || 25} calls today
          </div>
          {status && (
            <div className="mt-1 h-1 bg-gray-200 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  (status.api_budget_used / status.daily_api_limit) * 100 > 75
                    ? 'bg-gray-600'
                    : 'bg-success'
                }`}
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
          <div className="flex flex-col gap-0.5">
            <div className="text-11 font-medium text-gray-500 uppercase tracking-wider">Next Task</div>
            <div className="text-13 text-gray-700">{status.next_planned_task}</div>
          </div>
        )}
      </div>
    </div>
  )
}
