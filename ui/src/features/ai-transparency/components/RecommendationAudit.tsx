/**
 * Recommendation Audit Component
 * Shows Claude analysis for portfolio stocks, prioritized by data quality.
 * Priority 1: All three data quality params (earnings, news, fundamentals)
 * Priority 2: Two or more data quality params
 * Priority 3: Newly analyzed stocks
 */

import React, { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useClaudeTransparency } from '@/hooks/useClaudeTransparency'
import { Badge } from '@/components/ui/Badge'

interface DataQuality {
  has_earnings?: boolean
  has_news?: boolean
  has_fundamentals?: boolean
}

interface Analysis {
  symbol: string
  timestamp: string
  analysis_type?: string
  confidence_score?: number
  analysis_summary?: string
  analysis_content?: string
  recommendations_count?: number
  data_quality?: DataQuality
}

const getDataQualityScore = (dq?: DataQuality): number => {
  if (!dq) return 0
  let score = 0
  if (dq.has_earnings) score++
  if (dq.has_news) score++
  if (dq.has_fundamentals) score++
  return score
}

const getDataQualityBadge = (dq?: DataQuality) => {
  const score = getDataQualityScore(dq)
  if (score === 3) return { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'Complete Data ✓✓✓' }
  if (score === 2) return { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Partial Data ✓✓' }
  if (score === 1) return { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Limited Data ✓' }
  return { bg: 'bg-warmgray-100', text: 'text-warmgray-600', label: 'No Data' }
}

export const RecommendationAudit: React.FC = () => {
  const { tradeLogs, isLoading } = useClaudeTransparency()

  // Sort by data quality score (descending)
  const sortedAnalyses = useMemo(() => {
    if (!tradeLogs) return []
    return [...tradeLogs].sort((a, b) => {
      const scoreA = getDataQualityScore(a.data_quality)
      const scoreB = getDataQualityScore(b.data_quality)
      if (scoreB !== scoreA) return scoreB - scoreA
      // Secondary sort by timestamp (newest first)
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    })
  }, [tradeLogs])

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">Loading recommendations...</p>
        </CardContent>
      </Card>
    )
  }

  if (!sortedAnalyses || sortedAnalyses.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">No analysis recommendations available yet</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {sortedAnalyses.map((analysis: Analysis, index: number) => {
        const dqBadge = getDataQualityBadge(analysis.data_quality)
        const content = analysis.analysis_content || analysis.analysis_summary || 'No analysis content available'

        return (
          <Card key={`${analysis.symbol}-${index}`}>
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg">{analysis.symbol}</CardTitle>
                  <p className="text-sm text-warmgray-500 mt-1">
                    {new Date(analysis.timestamp).toLocaleDateString()} {new Date(analysis.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Badge className={`${dqBadge.bg} ${dqBadge.text} text-xs`}>
                    {dqBadge.label}
                  </Badge>
                  {analysis.recommendations_count && analysis.recommendations_count > 0 && (
                    <Badge className="bg-green-100 text-green-800 text-xs">
                      {analysis.recommendations_count} Recs
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {analysis.analysis_type && (
                <div>
                  <p className="text-sm font-semibold text-warmgray-700">Analysis Type</p>
                  <p className="text-sm text-warmgray-600 capitalize">{analysis.analysis_type.replace(/_/g, ' ')}</p>
                </div>
              )}

              {analysis.confidence_score !== undefined && (
                <div>
                  <p className="text-sm font-semibold text-warmgray-700">Confidence Score</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-warmgray-200 rounded-full h-2">
                      <div
                        className="bg-copper-600 h-2 rounded-full"
                        style={{ width: `${(analysis.confidence_score || 0) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold">{((analysis.confidence_score || 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              )}

              {content && (
                <div>
                  <p className="text-sm font-semibold text-warmgray-700">Claude Analysis</p>
                  <p className="text-sm text-warmgray-600 whitespace-pre-wrap break-words max-h-48 overflow-y-auto bg-warmgray-50 p-3 rounded">
                    {content}
                  </p>
                </div>
              )}

              {analysis.data_quality && (
                <div>
                  <p className="text-sm font-semibold text-warmgray-700 mb-2">Data Quality Details</p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className={`p-3 rounded border ${analysis.data_quality.has_earnings ? 'border-green-300 bg-green-50' : 'border-warmgray-200 bg-warmgray-50'}`}>
                      <p className="font-semibold">{analysis.data_quality.has_earnings ? '✓' : '✗'} Earnings</p>
                      <p className="text-warmgray-600">Data available</p>
                    </div>
                    <div className={`p-3 rounded border ${analysis.data_quality.has_news ? 'border-green-300 bg-green-50' : 'border-warmgray-200 bg-warmgray-50'}`}>
                      <p className="font-semibold">{analysis.data_quality.has_news ? '✓' : '✗'} News</p>
                      <p className="text-warmgray-600">Data available</p>
                    </div>
                    <div className={`p-3 rounded border ${analysis.data_quality.has_fundamentals ? 'border-green-300 bg-green-50' : 'border-warmgray-200 bg-warmgray-50'}`}>
                      <p className="font-semibold">{analysis.data_quality.has_fundamentals ? '✓' : '✗'} Fundamentals</p>
                      <p className="text-warmgray-600">Data available</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export default RecommendationAudit
