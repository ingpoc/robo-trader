/**
 * Real-Time Positions Table Component
 * READ-ONLY display with truthful mark status for paper-trading positions.
 */

import React from 'react'
import { RefreshCw, TrendingDown, TrendingUp, Wifi, WifiOff } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import type { OpenPositionResponse } from '../types'

export interface RealTimePositionsTableProps {
  positions: OpenPositionResponse[]
  isLoading?: boolean
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
  }).format(amount)

const formatPercent = (percent: number) => `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`

const getPnLColor = (pnl: number) => {
  if (pnl > 0) return 'text-emerald-600'
  if (pnl < 0) return 'text-red-600'
  return 'text-muted-foreground'
}

export const RealTimePositionsTable: React.FC<RealTimePositionsTableProps> = ({
  positions,
  isLoading = false,
}) => {
  const totalPnL = positions.reduce((sum, position) => sum + position.unrealized_pnl, 0)
  const totalInvestment = positions.reduce(
    (sum, position) => sum + position.entry_price * Math.abs(position.quantity),
    0
  )
  const totalPnLPercent = totalInvestment > 0 ? (totalPnL / totalInvestment) * 100 : 0
  const staleMarks = positions.filter((position) => position.markStatus && position.markStatus !== 'live').length

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-muted/20 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-foreground">Open Positions</h3>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {staleMarks === 0 ? (
              <>
                <Wifi className="h-4 w-4 text-emerald-600" />
                <span>Live marks</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-amber-600" />
                <span>{staleMarks} stale mark{staleMarks === 1 ? '' : 's'}</span>
              </>
            )}
          </div>
          <Badge variant="outline" className="text-xs">
            {positions.length} positions
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="h-4 w-4" />
          <span>Last update: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-4">
          <div className="text-sm font-medium text-muted-foreground">Open exposure</div>
          <div className="mt-2 text-2xl font-semibold text-foreground">
            {formatCurrency(totalInvestment)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-sm font-medium text-muted-foreground">Unrealized P&amp;L</div>
          <div className={`mt-2 text-2xl font-semibold ${getPnLColor(totalPnL)}`}>
            {formatCurrency(totalPnL)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-sm font-medium text-muted-foreground">Return on deployed capital</div>
          <div className={`mt-2 text-2xl font-semibold ${getPnLColor(totalPnLPercent)}`}>
            {formatPercent(totalPnLPercent)}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-muted/35">
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3 text-right">Qty</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Current</th>
                <th className="px-4 py-3 text-right">P&amp;L</th>
                <th className="px-4 py-3 text-right">P&amp;L %</th>
                <th className="px-4 py-3 text-right">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">
                    Loading open positions...
                  </td>
                </tr>
              ) : positions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">
                    No open positions yet.
                  </td>
                </tr>
              ) : (
                positions.map((position) => {
                  const pnlIsPositive = position.unrealized_pnl >= 0
                  const liveMark = !position.markStatus || position.markStatus === 'live'

                  return (
                    <tr key={position.trade_id} className="hover:bg-muted/20">
                      <td className="px-4 py-4">
                        <div className="flex flex-col gap-1">
                          <div className="font-medium text-foreground">{position.symbol}</div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span>{position.strategy || 'AI strategy'}</span>
                            <Badge variant={liveMark ? 'outline' : 'secondary'} className="text-[10px] uppercase">
                              {liveMark ? 'Live mark' : 'Stale mark'}
                            </Badge>
                          </div>
                          {!liveMark && position.markDetail ? (
                            <div className="max-w-md text-xs leading-relaxed text-amber-700">
                              {position.markDetail}
                            </div>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right font-medium text-foreground">
                        {position.quantity}
                      </td>
                      <td className="px-4 py-4 text-right text-muted-foreground">
                        {formatCurrency(position.entry_price)}
                      </td>
                      <td className="px-4 py-4 text-right font-medium text-foreground">
                        {formatCurrency(position.current_price)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className={`flex items-center justify-end gap-1 font-medium ${getPnLColor(position.unrealized_pnl)}`}>
                          {pnlIsPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          <span>{formatCurrency(position.unrealized_pnl)}</span>
                        </div>
                      </td>
                      <td className={`px-4 py-4 text-right font-medium ${getPnLColor(position.unrealized_pnl_pct)}`}>
                        {formatPercent(position.unrealized_pnl_pct)}
                      </td>
                      <td className="px-4 py-4 text-right text-sm">
                        {position.stop_loss ? (
                          <div className="text-red-600">SL: {formatCurrency(position.stop_loss)}</div>
                        ) : null}
                        {position.target ? (
                          <div className="text-emerald-600">TGT: {formatCurrency(position.target)}</div>
                        ) : null}
                        {!position.stop_loss && !position.target ? (
                          <span className="text-muted-foreground">-</span>
                        ) : null}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="text-center text-sm text-muted-foreground">
        <p>
          Prices come from Zerodha when available. When live marks are unavailable, positions are shown with a stale
          entry-price mark and explicit status.
        </p>
      </div>
    </div>
  )
}

export default RealTimePositionsTable
