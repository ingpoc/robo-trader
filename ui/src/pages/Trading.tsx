import { QuickTradeForm } from '@/components/Dashboard/QuickTradeForm'
import { useRecommendations } from '@/hooks/useRecommendations'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { SkeletonLoader, LoadingList } from '@/components/common/SkeletonLoader'
import { StepIndicator, type Step } from '@/components/ui/step-indicator'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { formatDateTime } from '@/utils/format'
import { TrendingUp, CheckCircle, XCircle, Clock, AlertCircle, DollarSign, Target, Activity } from 'lucide-react'
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function Trading() {
  const { recommendations, approve, reject, isPending, isLoading } = useRecommendations()
  const [approvalSteps, setApprovalSteps] = useState<Step[]>([])

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div>
          <h1 className="text-4xl lg:text-5xl font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">Trading Center</h1>
          <p className="text-lg text-warmgray-600 dark:text-warmgray-400 mt-2">Execute trades and review AI recommendations</p>
        </div>
      </div>

      <Tabs defaultValue="live" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="live">Live Trading</TabsTrigger>
          <TabsTrigger value="paper">Paper Trading</TabsTrigger>
        </TabsList>

        <TabsContent value="live">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* Quick Trade Form */}
            <Card variant="featured">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100 font-serif">
                  <DollarSign className="w-5 h-5 text-copper-500" />
                  Quick Trade
                </CardTitle>
              </CardHeader>
              <CardContent>
                <QuickTradeForm />
              </CardContent>
            </Card>

        {/* AI Recommendations */}
        <Card variant="featured">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100 font-serif">
                <Target className="w-5 h-5 text-copper-500" />
                AI Recommendations ({recommendations.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {recommendations.length === 0 ? (
              <div className="text-center py-8">
                <Target className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-warmgray-900 mb-2">No Pending Recommendations</h3>
                <p className="text-sm text-warmgray-600">
                  AI recommendations will appear here when available for review.
                </p>
              </div>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {recommendations.map((rec) => (
                  <Card key={rec.id} className="border border-warmgray-300/50 bg-white/70 backdrop-blur-sm">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-warmgray-900">
                              {rec.recommendation.action} {rec.recommendation.symbol}
                            </h4>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              (rec.recommendation.confidence * 100) >= 80
                                ? 'bg-emerald-100 text-emerald-900'
                                : (rec.recommendation.confidence * 100) >= 60
                                  ? 'bg-copper-100 text-copper-900'
                                  : 'bg-rose-100 text-rose-900'
                            }`}>
                              {(rec.recommendation.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                          <div className="text-xs text-warmgray-500">
                            {rec.created_at && formatDateTime(rec.created_at)}
                          </div>
                        </div>
                      </div>

                      <div className="text-sm text-warmgray-700 mb-4">
                        {rec.recommendation.reasoning}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => approve(rec.id)}
                          disabled={isPending}
                          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => reject(rec.id)}
                          disabled={isPending}
                          className="flex items-center gap-2 border-rose-300 text-rose-700 hover:bg-rose-50"
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
        </TabsContent>

        <TabsContent value="paper">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* Paper Trading Recommendations */}
            <Card variant="featured">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100 font-serif">
                  <Target className="w-5 h-5 text-copper-500" />
                  Claude Paper Trading Suggestions
                </CardTitle>
                <CardDescription>
                  AI-generated trading recommendations for paper account practice
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <CheckCircle className="w-5 h-5 text-emerald-600 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="font-medium text-emerald-800">RELIANCE - Breakout Strategy</h4>
                        <p className="text-sm text-emerald-700 mt-1">
                          RSI divergence at support level. Strong volume confirmation expected.
                        </p>
                        <div className="flex gap-2 mt-3">
                          <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                            Execute BUY
                          </Button>
                          <Button size="sm" variant="outline">
                            View Analysis
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <Clock className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="font-medium text-blue-800">INFY - Mean Reversion Setup</h4>
                        <p className="text-sm text-blue-700 mt-1">
                          Oversold condition with decreasing volatility. Potential bounce expected.
                        </p>
                        <div className="flex gap-2 mt-3">
                          <Button size="sm" variant="outline" className="border-blue-300 text-blue-700">
                            Monitor Setup
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Paper Trading Performance */}
            <Card variant="featured">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100 font-serif">
                  <Activity className="w-5 h-5 text-copper-500" />
                  Paper Trading Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-emerald-50 rounded-lg">
                      <p className="text-2xl font-bold text-emerald-600">65.2%</p>
                      <p className="text-sm text-emerald-700">Win Rate</p>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">₹+12,450</p>
                      <p className="text-sm text-blue-700">Total P&L</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Today's Token Usage</span>
                      <span className="font-medium">2,450 / 10,000</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div className="bg-copper-500 h-2 rounded-full" style={{ width: '24.5%' }}></div>
                    </div>
                  </div>

                  <div className="pt-4 border-t">
                    <h4 className="font-medium mb-3">Strategy Effectiveness</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Breakout Trading</span>
                        <span className="text-emerald-600 font-medium">68% Win Rate</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>RSI Divergence</span>
                        <span className="text-emerald-600 font-medium">72% Win Rate</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Mean Reversion</span>
                        <span className="text-rose-600 font-medium">45% Win Rate</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Trading Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-copper-100 rounded-lg">
                <TrendingUp className="w-5 h-5 text-copper-600" />
              </div>
              <div>
                <p className="text-sm text-warmgray-600">Today's Trades</p>
                <p className="text-2xl font-bold text-warmgray-900">0</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-100 rounded-lg">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-warmgray-600">Success Rate</p>
                <p className="text-2xl font-bold text-warmgray-900">0%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-md border-warmgray-300/50 bg-gradient-to-br from-white/95 to-copper-50/70 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-copper-100 rounded-lg">
                <Clock className="w-5 h-5 text-copper-600" />
              </div>
              <div>
                <p className="text-sm text-warmgray-600">Pending Orders</p>
                <p className="text-2xl font-bold text-warmgray-900">0</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}