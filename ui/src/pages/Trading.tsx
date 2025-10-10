import { QuickTradeForm } from '@/components/Dashboard/QuickTradeForm'
import { useRecommendations } from '@/hooks/useRecommendations'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'

export function Trading() {
  const { recommendations, approve, reject, isPending } = useRecommendations()

  return (
    <div className="flex flex-col gap-6 p-6 overflow-auto">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Trading</h1>
        <p className="text-sm text-gray-600">Execute trades and review recommendations</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <QuickTradeForm />

        <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
          <h3 className="text-lg font-semibold text-gray-900">AI Recommendations</h3>
          {recommendations.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-500">
              No pending recommendations
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {recommendations.map((rec) => (
                <div key={rec.id} className="p-3 border border-gray-200 rounded">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {rec.recommendation.action} {rec.recommendation.symbol}
                      </div>
                      <div className="text-xs text-gray-600">
                        Confidence: {(rec.recommendation.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">
                      {rec.created_at && formatDateTime(rec.created_at)}
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 mb-3">
                    {rec.recommendation.reasoning}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => approve(rec.id)}
                      disabled={isPending}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => reject(rec.id)}
                      disabled={isPending}
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
