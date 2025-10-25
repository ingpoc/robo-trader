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
          <p className="text-warmgray-500">No trade decision logs available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {trades.map((trade, index) => (
        <Card key={index}>
          <CardHeader className="pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg">{trade.symbol}</CardTitle>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                trade.action === 'BUY' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
              }`}>
                {trade.action}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-warmgray-600">Entry Price</p>
                <p className="font-semibold">₹{trade.entry_price?.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-warmgray-600">Quantity</p>
                <p className="font-semibold">{trade.quantity}</p>
              </div>
              {trade.exit_price && (
                <>
                  <div>
                    <p className="text-warmgray-600">Exit Price</p>
                    <p className="font-semibold">₹{trade.exit_price.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-warmgray-600">P&L</p>
                    <p className={`font-semibold ${trade.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      ₹{trade.pnl?.toFixed(2)}
                    </p>
                  </div>
                </>
              )}
            </div>
            {trade.reasoning && (
              <div className="border-t pt-3">
                <p className="text-sm font-semibold text-warmgray-700">Claude's Reasoning:</p>
                <p className="text-sm text-warmgray-600 mt-2">{trade.reasoning}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default TradeDecisionLog
