/**
 * Positions Table Component
 * Displays all open trading positions
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { TrendingUp, TrendingDown, Edit2, X } from 'lucide-react'
import { SkeletonCard } from '@/components/common/SkeletonLoader'
import type { OpenPositionResponse } from '../types'

export interface PositionsTableProps {
  positions: OpenPositionResponse[]
  onClosePosition: (tradeId: string, exitPrice: number) => void
  onModifyLevels: (position: OpenPositionResponse) => void
  isLoading?: boolean
}

export const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  onClosePosition,
  onModifyLevels,
  isLoading = false
}) => {
  if (isLoading) {
    return <SkeletonCard className="h-96" />
  }

  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-muted-foreground">No open positions</p>
            <p className="text-sm text-muted-foreground mt-2">
              Execute a trade to create your first position
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions ({positions.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-2 font-semibold">Symbol</th>
                <th className="text-right py-3 px-2 font-semibold">Qty</th>
                <th className="text-right py-3 px-2 font-semibold">Entry</th>
                <th className="text-right py-3 px-2 font-semibold">Current</th>
                <th className="text-right py-3 px-2 font-semibold">P&L</th>
                <th className="text-right py-3 px-2 font-semibold">SL / TGT</th>
                <th className="text-left py-3 px-2 font-semibold">Entry Time</th>
                <th className="text-center py-3 px-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => {
                const pnlIsPositive = position.unrealized_pnl >= 0
                const entryDate = new Date(position.entry_time).toLocaleDateString('en-IN', {
                  month: 'short',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })

                return (
                  <tr key={position.trade_id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="py-3 px-2 font-medium">{position.symbol}</td>
                    <td className="text-right py-3 px-2">{position.quantity}</td>
                    <td className="text-right py-3 px-2">₹{position.entry_price.toFixed(2)}</td>
                    <td className="text-right py-3 px-2 font-semibold">
                      ₹{position.current_price.toFixed(2)}
                    </td>
                    <td className={`text-right py-3 px-2 font-semibold ${pnlIsPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                      <div className="flex items-center justify-end gap-1">
                        {pnlIsPositive ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        <span>
                          {pnlIsPositive ? '+' : ''}₹{Math.abs(position.unrealized_pnl).toLocaleString('en-IN')} ({position.unrealized_pnl_pct.toFixed(2)}%)
                        </span>
                      </div>
                    </td>
                    <td className="text-right py-3 px-2 text-xs">
                      <div className="space-y-1">
                        {position.stop_loss && (
                          <div className="text-red-600">
                            SL: ₹{position.stop_loss.toFixed(2)}
                          </div>
                        )}
                        {position.target && (
                          <div className="text-emerald-600">
                            TGT: ₹{position.target.toFixed(2)}
                          </div>
                        )}
                        {!position.stop_loss && !position.target && (
                          <div className="text-muted-foreground italic">No levels</div>
                        )}
                      </div>
                    </td>
                    <td className="text-left py-3 px-2 text-xs text-muted-foreground">{entryDate}</td>
                    <td className="text-center py-3 px-2">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onModifyLevels(position)}
                          className="h-8 w-8 p-0"
                          title="Modify stop loss and target"
                        >
                          <Edit2 className="w-4 h-4 text-blue-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onClosePosition(position.trade_id, position.current_price)}
                          className="h-8 w-8 p-0"
                          title="Close position"
                        >
                          <X className="w-4 h-4 text-red-600" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default PositionsTable
