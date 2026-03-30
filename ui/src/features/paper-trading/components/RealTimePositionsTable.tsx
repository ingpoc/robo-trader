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

const formatCurrencyOrUnavailable = (amount: number | null | undefined) =>
  amount == null ? 'Unavailable' : formatCurrency(amount)

const formatPercent = (percent: number | null | undefined) =>
  percent == null ? 'Unavailable' : `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`

const getPnLColor = (pnl: number | null | undefined) => {
  if (pnl == null) return 'text-muted-foreground'
  if (pnl > 0) return 'text-emerald-600'
  if (pnl < 0) return 'text-red-600'
  return 'text-muted-foreground'
}

export const RealTimePositionsTable: React.FC<RealTimePositionsTableProps> = ({
  positions,
  isLoading = false,
}) => {
  const valuedPositions = positions.filter((position) => position.unrealized_pnl != null)
  const totalPnL = valuedPositions.reduce((sum, position) => sum + (position.unrealized_pnl ?? 0), 0)
  const totalInvestment = positions.reduce(
    (sum, position) => sum + position.entry_price * Math.abs(position.quantity),
    0,
  )
  const totalPnLPercent = valuedPositions.length > 0 && totalInvestment > 0 ? (totalPnL / totalInvestment) * 100 : null
  const staleMarks = positions.filter((position) => position.markStatus && position.markStatus !== 'live').length
  const unavailableValuationCount = positions.filter(
    (position) => position.current_price == null || position.unrealized_pnl == null || position.unrealized_pnl_pct == null,
  ).length

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
                <span>{staleMarks} unavailable mark{staleMarks === 1 ? '' : 's'}</span>
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
          <p className="desk-kicker">Deployed Capital</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{formatCurrency(totalInvestment)}</p>
          <p className="mt-3 text-sm text-muted-foreground">
            Capital committed based on the position ledger entry prices.
          </p>
        </Card>

        <Card className="p-4">
          <p className="desk-kicker">Live Unrealized P&amp;L</p>
          <p className={`mt-2 text-2xl font-semibold ${getPnLColor(valuedPositions.length > 0 ? totalPnL : null)}`}>
            {valuedPositions.length > 0 ? formatCurrency(totalPnL) : 'Unavailable'}
          </p>
          <p className="mt-3 text-sm text-muted-foreground">
            {unavailableValuationCount > 0
              ? 'Aggregate unrealized P&L is hidden until live marks return.'
              : 'Aggregate unrealized P&L across all open positions.'}
          </p>
        </Card>

        <Card className="p-4">
          <p className="desk-kicker">Live Return</p>
          <p className={`mt-2 text-2xl font-semibold ${getPnLColor(totalPnLPercent)}`}>
            {formatPercent(totalPnLPercent)}
          </p>
          <p className="mt-3 text-sm text-muted-foreground">
            {unavailableValuationCount > 0
              ? 'Mark-to-market return is hidden while live valuation is unavailable.'
              : 'Return on currently deployed capital.'}
          </p>
        </Card>
      </div>

      {unavailableValuationCount > 0 ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50/80 px-4 py-3 text-sm text-amber-950">
          These positions remain readable, but {unavailableValuationCount} valuation field{unavailableValuationCount === 1 ? ' is' : 's are'} unavailable. No entry-price marks were substituted.
        </div>
      ) : null}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border/70">
            <thead className="bg-muted/20">
              <tr className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                <th className="px-4 py-3 font-medium">Position</th>
                <th className="px-4 py-3 font-medium text-right">Qty</th>
                <th className="px-4 py-3 font-medium text-right">Entry</th>
                <th className="px-4 py-3 font-medium text-right">Current</th>
                <th className="px-4 py-3 font-medium text-right">P&amp;L</th>
                <th className="px-4 py-3 font-medium text-right">Return</th>
                <th className="px-4 py-3 font-medium text-right">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 bg-white/90 dark:bg-warmgray-900/70">
              {isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <tr key={index} className="animate-pulse">
                    <td className="px-4 py-4" colSpan={7}>
                      <div className="h-12 rounded-xl bg-muted/30" />
                    </td>
                  </tr>
                ))
              ) : positions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                    No open positions yet.
                  </td>
                </tr>
              ) : (
                positions.map((position) => {
                  const liveMark = position.markStatus === 'live'
                  const hasLiveValuation = (
                    position.current_price != null
                    && position.unrealized_pnl != null
                    && position.unrealized_pnl_pct != null
                  )
                  const pnlIsPositive = (position.unrealized_pnl ?? 0) >= 0

                  return (
                    <tr key={position.trade_id} className="align-top">
                      <td className="px-4 py-4">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-foreground">{position.symbol}</p>
                            <Badge variant="outline" className="text-[10px] uppercase">
                              {position.tradeType ?? 'Position'}
                            </Badge>
                            <Badge variant={liveMark ? 'outline' : 'secondary'} className="text-[10px] uppercase">
                              {liveMark ? 'Live mark' : 'Mark unavailable'}
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
                        {formatCurrencyOrUnavailable(position.current_price)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {hasLiveValuation ? (
                          <div className={`flex items-center justify-end gap-1 font-medium ${getPnLColor(position.unrealized_pnl)}`}>
                            {pnlIsPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                            <span>{formatCurrency(position.unrealized_pnl ?? 0)}</span>
                          </div>
                        ) : (
                          <span className="font-medium text-muted-foreground">Unavailable</span>
                        )}
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
          Prices come from Zerodha. If live marks become unavailable, the paper-trading surface must remain truthful and never substitute entry-price marks.
        </p>
      </div>
    </div>
  )
}

export default RealTimePositionsTable
