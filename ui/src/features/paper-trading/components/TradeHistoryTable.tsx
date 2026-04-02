/**
 * Trade History Table Component
 * Displays closed trades in a table format
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { SkeletonCard } from '@/components/common/SkeletonLoader'
import type { ClosedTradeResponse } from '../types'

export interface TradeHistoryTableProps {
  trades: ClosedTradeResponse[]
  isLoading?: boolean
}

export const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({
  trades,
  isLoading = false
}) => {
  const formatDate = (value: string) => {
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return 'Unavailable'
    }

    return parsed.toLocaleDateString('en-IN', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatCurrency = (value: number) => `₹${Number(value ?? 0).toFixed(2)}`

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
        </CardHeader>
        <CardContent>
          <SkeletonCard className="h-64" />
        </CardContent>
      </Card>
    )
  }

  if (trades.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-muted-foreground">No closed trades yet</p>
            <p className="text-sm text-muted-foreground mt-2">
              Your completed trades will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade History ({trades.length} trades)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-2 font-semibold">Symbol</th>
                <th className="text-right py-3 px-2 font-semibold">Qty</th>
                <th className="text-right py-3 px-2 font-semibold">Entry</th>
                <th className="text-right py-3 px-2 font-semibold">Exit</th>
                <th className="text-right py-3 px-2 font-semibold">P&L</th>
                <th className="text-left py-3 px-2 font-semibold">Strategy</th>
                <th className="text-center py-3 px-2 font-semibold">Days</th>
                <th className="text-left py-3 px-2 font-semibold">Entry Time</th>
                <th className="text-left py-3 px-2 font-semibold">Exit Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => {
                const pnl = Number(trade.pnl ?? 0)
                const pnlPct = Number(trade.pnl_pct ?? 0)
                const pnlIsPositive = pnl >= 0
                const entryDate = formatDate(trade.entry_time)
                const exitDate = formatDate(trade.exit_time)

                return (
                  <tr
                    key={trade.trade_id}
                    className="border-b hover:bg-muted/50 transition-colors"
                  >
                    <td className="py-3 px-2 font-medium">{trade.symbol}</td>
                    <td className="text-right py-3 px-2">{trade.quantity}</td>
                    <td className="text-right py-3 px-2">{formatCurrency(trade.entry_price)}</td>
                    <td className="text-right py-3 px-2">{formatCurrency(trade.exit_price)}</td>
                    <td
                      className={`text-right py-3 px-2 font-semibold ${
                        pnlIsPositive ? 'text-emerald-600' : 'text-red-600'
                      }`}
                    >
                      <div className="flex items-center justify-end gap-1">
                        {pnlIsPositive ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        <span>
                          {pnlIsPositive ? '+' : ''}₹{Math.abs(pnl).toLocaleString('en-IN')} (
                          {pnlPct.toFixed(2)}%)
                        </span>
                      </div>
                    </td>
                    <td className="text-left py-3 px-2 text-xs">
                      <span className="bg-muted px-2 py-1 rounded">
                        {trade.strategy || 'Manual'}
                      </span>
                    </td>
                    <td className="text-center py-3 px-2">{trade.holding_days}</td>
                    <td className="text-left py-3 px-2 text-xs text-muted-foreground">
                      {entryDate}
                    </td>
                    <td className="text-left py-3 px-2 text-xs text-muted-foreground">
                      {exitDate}
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

export default TradeHistoryTable
