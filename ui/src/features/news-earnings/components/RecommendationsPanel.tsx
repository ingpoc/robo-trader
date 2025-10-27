import { memo, useCallback } from 'react'
import { CheckCircle, XCircle, Clock, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { RecommendationBadge } from '@/components/ui/RecommendationBadge'
import { formatRelativeTime } from '@/utils/format'
import { useRecommendations } from '@/hooks/useRecommendations'
import type { Recommendation } from '@/types/domain'

interface RecommendationsPanelProps {
  recommendations: Recommendation[]
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
}

export const RecommendationsPanel = memo<RecommendationsPanelProps>(({
  recommendations,
  isLoading,
  error,
  onRetry,
}) => {
  const { approve, reject, discuss } = useRecommendations()

  const handleApprove = useCallback(async (id: string) => {
    try {
      await approve(id)
    } catch (error) {
      console.error('Failed to approve recommendation:', error)
    }
  }, [approve])

  const handleReject = useCallback(async (id: string) => {
    try {
      await reject(id)
    } catch (error) {
      console.error('Failed to reject recommendation:', error)
    }
  }, [reject])

  const handleDiscuss = useCallback(async (id: string) => {
    try {
      await discuss(id)
    } catch (error) {
      console.error('Failed to discuss recommendation:', error)
    }
  }, [discuss])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-emerald-600" />
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'discussing':
        return <Clock className="w-4 h-4 text-amber-600" />
      default:
        return <Clock className="w-4 h-4 text-warmgray-400" />
    }
  }

  const normalizeConfidence = (confidence: number) => {
    // Handle both decimal (0.70) and percentage (70 or 7000) formats
    if (confidence > 100) {
      return confidence / 10000 // 7000 -> 0.70
    }
    if (confidence > 1) {
      return confidence / 100 // 70 -> 0.70
    }
    return confidence // 0.70 -> 0.70
  }

  const getConfidenceColor = (confidence: number) => {
    const normalized = normalizeConfidence(confidence)
    if (normalized >= 0.8) return 'text-emerald-600'
    if (normalized >= 0.6) return 'text-amber-600'
    return 'text-red-600'
  }

  if (isLoading) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-warmgray-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100">
            🤖 AI Trading Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-copper-600 mx-auto"></div>
              <p className="text-warmgray-600 dark:text-warmgray-400">Loading AI recommendations...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-warmgray-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100">
            🤖 AI Trading Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md mx-auto">
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Unable to load recommendations</h3>
              <p className="text-red-700 dark:text-red-300 text-sm mb-4">{error}</p>
              {onRetry && (
                <Button onClick={onRetry} variant="outline" className="border-red-300 text-red-700 hover:bg-red-50">
                  Retry
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-warmgray-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100">
            🤖 AI Trading Recommendations
          </CardTitle>
          <p className="text-warmgray-600 dark:text-warmgray-400">
            Real-time AI-powered buy/sell/hold recommendations based on fundamental and technical analysis
          </p>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-warmgray-100 dark:bg-warmgray-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">🤖</span>
            </div>
            <h3 className="text-lg font-semibold text-warmgray-900 dark:text-warmgray-100 mb-2">No Active Recommendations</h3>
            <p className="text-warmgray-600 dark:text-warmgray-400 mb-6">
              AI recommendations will appear here when the system analyzes market conditions and generates trading signals.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
              {[
                { icon: '📰', title: 'News Analysis', desc: 'Sentiment and relevance scoring' },
                { icon: '📊', title: 'Earnings Data', desc: 'Fundamental analysis integration' },
                { icon: '📈', title: 'Technical Signals', desc: 'Chart patterns and indicators' }
              ].map((feature, index) => (
                <div key={index} className="bg-warmgray-50 dark:bg-warmgray-800/50 rounded-lg p-4 border border-warmgray-200 dark:border-warmgray-700">
                  <div className="text-2xl mb-2">{feature.icon}</div>
                  <h4 className="font-semibold text-warmgray-900 dark:text-warmgray-100 mb-1">{feature.title}</h4>
                  <p className="text-sm text-warmgray-600 dark:text-warmgray-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Recommendations Overview */}
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-warmgray-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-warmgray-900 dark:text-warmgray-100">
            🤖 AI Trading Recommendations
          </CardTitle>
          <p className="text-warmgray-600 dark:text-warmgray-400">
            Real-time AI-powered buy/sell/hold recommendations based on fundamental and technical analysis
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recommendations.map((rec) => (
              <article
                key={rec.id}
                className="border border-warmgray-200 dark:border-warmgray-700 rounded-xl p-6 bg-gradient-to-br from-white to-warmgray-50 dark:from-warmgray-800 dark:to-warmgray-800/50 hover:shadow-lg transition-all duration-300"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-xl text-warmgray-900 dark:text-warmgray-100 mb-1">
                      {rec.symbol}
                    </h3>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(rec.status)}
                      <span className="text-sm text-warmgray-600 dark:text-warmgray-400 capitalize">
                        {rec.status}
                      </span>
                    </div>
                  </div>
                  <RecommendationBadge action={rec.action} />
                </div>

                {/* Confidence & Reasoning */}
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-warmgray-700 dark:text-warmgray-300">Confidence</span>
                      <span className={`text-sm font-bold ${getConfidenceColor(rec.confidence)}`}>
                        {(normalizeConfidence(rec.confidence) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-warmgray-200 dark:bg-warmgray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          normalizeConfidence(rec.confidence) >= 0.8 ? 'bg-emerald-500' :
                          normalizeConfidence(rec.confidence) >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${normalizeConfidence(rec.confidence) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-warmgray-900 dark:text-warmgray-100 mb-2">Analysis</h4>
                    <p className="text-sm text-warmgray-700 dark:text-warmgray-300 leading-relaxed">
                      {rec.thesis}
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                {rec.status === 'pending' && (
                  <div className="flex gap-2 mt-6 pt-4 border-t border-warmgray-200 dark:border-warmgray-700">
                    <Button
                      onClick={() => handleApprove(rec.id)}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                      size="sm"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleReject(rec.id)}
                      variant="outline"
                      className="flex-1 border-red-300 text-red-700 hover:bg-red-50"
                      size="sm"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                    <Button
                      onClick={() => handleDiscuss(rec.id)}
                      variant="outline"
                      className="flex-1 border-amber-300 text-amber-700 hover:bg-amber-50"
                      size="sm"
                    >
                      <Clock className="w-4 h-4 mr-2" />
                      Discuss
                    </Button>
                  </div>
                )}

                {/* Timestamp */}
                <div className="mt-4 pt-4 border-t border-warmgray-200 dark:border-warmgray-700">
                  <p className="text-xs text-warmgray-500 dark:text-warmgray-400">
                    Generated {rec.created_at ? formatRelativeTime(rec.created_at) : 'recently'}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      {recommendations && recommendations.length > 0 && (
        <Card className="shadow-xl border-0 bg-white/90 dark:bg-warmgray-800/90 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2 text-warmgray-900 dark:text-warmgray-100">
              <BarChart3 className="w-5 h-5" />
              Recommendation Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-600 mb-1">
                  {recommendations.filter(r => r.status === 'approved').length}
                </div>
                <div className="text-sm text-warmgray-600 dark:text-warmgray-400">Approved</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-600 mb-1">
                  {recommendations.filter(r => r.status === 'discussing').length}
                </div>
                <div className="text-sm text-warmgray-600 dark:text-warmgray-400">Under Discussion</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600 mb-1">
                  {recommendations.filter(r => r.status === 'rejected').length}
                </div>
                <div className="text-sm text-warmgray-600 dark:text-warmgray-400">Rejected</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-copper-600 mb-1">
                  {recommendations.filter(r => r.status === 'pending').length}
                </div>
                <div className="text-sm text-warmgray-600 dark:text-warmgray-400">Pending</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
})

RecommendationsPanel.displayName = 'RecommendationsPanel'