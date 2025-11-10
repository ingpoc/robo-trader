/**
 * Trade Decision Log Component
 * Displays detailed trade execution history with Claude's reasoning
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonCard } from '@/components/common/SkeletonLoader'

export interface TradeDecisionLogProps {
  trades: any[]
  isLoading: boolean
}

export const TradeDecisionLog: React.FC<TradeDecisionLogProps> = ({ trades, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4">
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} className="h-48" />
        ))}
      </div>
    )
  }

  if (!trades || trades.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">No analysis data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {trades.map((analysis, index) => (
        <Card key={index}>
          <CardHeader className="pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg">{analysis.symbol}</CardTitle>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                analysis.confidence_score >= 0.7 ? 'bg-emerald-100 text-emerald-800' :
                analysis.confidence_score >= 0.5 ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {Math.round(analysis.confidence_score * 100)}% Confidence
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-warmgray-600">Analysis Type</p>
                <p className="font-semibold">{analysis.analysis_type}</p>
              </div>
              <div>
                <p className="text-warmgray-600">Recommendations</p>
                <p className="font-semibold">{analysis.recommendations_count || 0}</p>
              </div>
              {analysis.data_quality && (
                <>
                  <div>
                    <p className="text-warmgray-600">Data Quality</p>
                    <div className="flex gap-2 mt-1">
                      <span className={`text-xs px-2 py-1 rounded ${
                        analysis.data_quality.has_earnings ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {analysis.data_quality.has_earnings ? 'Earnings ✓' : 'Earnings ✗'}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        analysis.data_quality.has_news ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {analysis.data_quality.has_news ? 'News ✓' : 'News ✗'}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        analysis.data_quality.has_fundamentals ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {analysis.data_quality.has_fundamentals ? 'Fundamentals ✓' : 'Fundamentals ✗'}
                      </span>
                    </div>
                  </div>
                  {analysis.created_at && (
                    <div>
                      <p className="text-warmgray-600">Analyzed</p>
                      <p className="font-semibold text-xs">
                        {new Date(analysis.created_at).toLocaleDateString()} {new Date(analysis.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
            {analysis.analysis_summary && (
              <div className="border-t pt-3">
                <p className="text-sm font-semibold text-warmgray-700">Analysis Summary:</p>
                <div className="text-sm text-warmgray-600 mt-2 max-h-32 overflow-y-auto">
                  {analysis.analysis_summary.length > 300
                    ? `${analysis.analysis_summary.substring(0, 300)}...`
                    : analysis.analysis_summary
                  }
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default TradeDecisionLog
