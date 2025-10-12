import { QuickTradeForm } from '@/components/Dashboard/QuickTradeForm'
import { useRecommendations } from '@/hooks/useRecommendations'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonLoader, LoadingList } from '@/components/common/SkeletonLoader'
import { StepIndicator, type Step } from '@/components/ui/step-indicator'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { formatDateTime } from '@/utils/format'
import { TrendingUp, CheckCircle, XCircle, Clock, AlertCircle, DollarSign, Target } from 'lucide-react'
import { useState } from 'react'

export function Trading() {
  const { recommendations, approve, reject, isPending, isLoading } = useRecommendations()
  const [approvalSteps, setApprovalSteps] = useState<Step[]>([])

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">Trading Center</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Execute trades and review AI recommendations</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Quick Trade Form */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-600" />
              Quick Trade
            </CardTitle>
          </CardHeader>
          <CardContent>
            <QuickTradeForm />
          </CardContent>
        </Card>

        {/* AI Recommendations */}
        <Card className="shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-600" />
                AI Recommendations ({recommendations.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {recommendations.length === 0 ? (
              <div className="text-center py-8">
                <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Pending Recommendations</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  AI recommendations will appear here when available for review.
                </p>
              </div>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {recommendations.map((rec) => (
                  <Card key={rec.id} className="border border-gray-200 dark:border-gray-700">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                              {rec.recommendation.action} {rec.recommendation.symbol}
                            </h4>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              (rec.recommendation.confidence * 100) >= 80
                                ? 'bg-green-100 text-green-900 dark:bg-green-900 dark:text-green-200'
                                : (rec.recommendation.confidence * 100) >= 60
                                  ? 'bg-yellow-100 text-yellow-900 dark:bg-yellow-900 dark:text-yellow-200'
                                  : 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-200'
                            }`}>
                              {(rec.recommendation.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {rec.created_at && formatDateTime(rec.created_at)}
                          </div>
                        </div>
                      </div>

                      <div className="text-sm text-gray-700 dark:text-gray-300 mb-4">
                        {rec.recommendation.reasoning}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => approve(rec.id)}
                          disabled={isPending}
                          className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => reject(rec.id)}
                          disabled={isPending}
                          className="flex items-center gap-2 border-red-300 text-red-700 hover:bg-red-50 dark:border-red-600 dark:text-red-400 dark:hover:bg-red-900/20"
                        >
                          <XCircle className="w-4 h-4" />
                          Reject
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trading Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Today's Trades</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">0%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Pending Orders</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}