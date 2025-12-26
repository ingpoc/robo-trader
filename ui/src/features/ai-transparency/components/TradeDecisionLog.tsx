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
          <p className="text-warmgray-500">No trade decisions available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {trades.map((decision, index) => {
        // Handle both trade decisions (morning session) and portfolio analyses
        const isTradeDecision = decision.decision_type !== undefined
        const symbol = decision.symbol || 'N/A'
        const confidence = decision.confidence || decision.confidence_score || 0
        const timestamp = decision.logged_at || decision.created_at || decision.timestamp

        return (
          <Card key={index}>
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg">{symbol}</CardTitle>
                  {isTradeDecision && decision.context?.action && (
                    <span className={`text-xs px-2 py-1 rounded font-semibold ${
                      decision.context.action === 'BUY'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {decision.context.action}
                    </span>
                  )}
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  confidence >= 0.7 ? 'bg-emerald-100 text-emerald-800' :
                  confidence >= 0.5 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {Math.round(confidence * 100)}% Confidence
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-warmgray-600">Type</p>
                  <p className="font-semibold">
                    {isTradeDecision ? decision.decision_type : (decision.analysis_type || 'Analysis')}
                  </p>
                </div>
                {isTradeDecision && decision.context?.quantity && (
                  <div>
                    <p className="text-warmgray-600">Quantity</p>
                    <p className="font-semibold">{decision.context.quantity}</p>
                  </div>
                )}
                {isTradeDecision && decision.context?.price && (
                  <div>
                    <p className="text-warmgray-600">Price</p>
                    <p className="font-semibold">₹{decision.context.price}</p>
                  </div>
                )}
                {!isTradeDecision && decision.recommendations_count !== undefined && (
                  <div>
                    <p className="text-warmgray-600">Recommendations</p>
                    <p className="font-semibold">{decision.recommendations_count}</p>
                  </div>
                )}
                {timestamp && (
                  <div>
                    <p className="text-warmgray-600">Time</p>
                    <p className="font-semibold text-xs">
                      {new Date(timestamp).toLocaleDateString()} {new Date(timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
              {(decision.reasoning || decision.analysis_summary) && (
                <div className="border-t pt-3">
                  <p className="text-sm font-semibold text-warmgray-700">
                    {isTradeDecision ? 'Reasoning' : 'Analysis Summary'}:
                  </p>
                  <div className="text-sm text-warmgray-600 mt-2 max-h-32 overflow-y-auto">
                    {(decision.reasoning || decision.analysis_summary)?.length > 300
                      ? `${(decision.reasoning || decision.analysis_summary).substring(0, 300)}...`
                      : (decision.reasoning || decision.analysis_summary)
                    }
                  </div>
                </div>
              )}
              {isTradeDecision && decision.context?.session_id && (
                <div className="border-t pt-3">
                  <p className="text-xs text-warmgray-500">
                    Session: {decision.context.session_id}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export default TradeDecisionLog
