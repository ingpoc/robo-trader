/**
 * Unrealized P&L Card Component
 * Displays total unrealized profit/loss and top positions
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'
import type { OpenPositionResponse } from '../types'

export interface UnrealizedPnLCardProps {
  totalUnrealizedPnL: number
  unrealizedPnLPct: number
  positions: OpenPositionResponse[]
}

export const UnrealizedPnLCard: React.FC<UnrealizedPnLCardProps> = ({
  totalUnrealizedPnL,
  unrealizedPnLPct,
  positions
}) => {
  const isPositive = totalUnrealizedPnL >= 0
  const topPositions = positions
    .sort((a, b) => Math.abs(b.unrealized_pnl) - Math.abs(a.unrealized_pnl))
    .slice(0, 3)

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            Unrealized P&L
          </CardTitle>
          <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 dark:bg-blue-950 rounded-full">
            <div className={`w-2 h-2 rounded-full ${isPositive ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs font-medium">Live</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Total P&L Display */}
        <div className="space-y-2">
          <div
            className={`text-4xl font-bold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}
          >
            {isPositive ? '+' : ''}₹{Math.abs(totalUnrealizedPnL).toLocaleString('en-IN')}
          </div>
          <div className="flex items-center gap-2">
            {isPositive ? (
              <TrendingUp className="w-4 h-4 text-emerald-600" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-600" />
            )}
            <span className={`text-sm font-semibold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}{unrealizedPnLPct.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Top Positions */}
        {topPositions.length > 0 && (
          <div className="border-t pt-3 space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase">Top Positions</h4>
            {topPositions.map((position) => (
              <div key={position.trade_id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{position.symbol}</span>
                  <span className="text-xs text-muted-foreground">×{position.quantity}</span>
                </div>
                <span
                  className={`font-semibold ${
                    position.unrealized_pnl >= 0 ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {position.unrealized_pnl >= 0 ? '+' : ''}₹
                  {Math.abs(position.unrealized_pnl).toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default UnrealizedPnLCard
