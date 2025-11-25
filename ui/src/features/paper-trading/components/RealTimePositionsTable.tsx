/**
 * Real-Time Positions Table Component
 * READ-ONLY display with live P&L - trades executed via MCP only
 */

import React from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { TrendingUp, TrendingDown, RefreshCw, Wifi } from 'lucide-react'
import type { OpenPositionResponse } from '../types'

export interface RealTimePositionsTableProps {
  positions: OpenPositionResponse[]
  isLoading?: boolean
}

export const RealTimePositionsTable: React.FC<RealTimePositionsTableProps> = ({
  positions,
  isLoading = false
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount)
  }

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`
  }

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600'
    if (pnl < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  const totalPnL = positions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)
  const totalInvestment = positions.reduce((sum, pos) => sum + (pos.entry_price * Math.abs(pos.quantity)), 0)
  const totalPnLPercent = totalInvestment > 0 ? (totalPnL / totalInvestment) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">Real-Time Positions</h3>
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-green-500" />
            <span className="text-sm text-gray-500">Live</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {positions.length} positions
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <RefreshCw className="w-4 h-4" />
          <span>Last update: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-1">Total P&L</div>
          <div className={`text-2xl font-bold ${getPnLColor(totalPnL)}`}>
            {formatCurrency(totalPnL)}
          </div>
          <div className={`text-sm ${getPnLColor(totalPnLPercent)}`}>
            {formatPercent(totalPnLPercent)}
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-1">Total Investment</div>
          <div className="text-2xl font-bold text-gray-900">
            {formatCurrency(totalInvestment)}
          </div>
          <div className="text-sm text-gray-500">
            {positions.length} positions
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-1">Data Source</div>
          <div className="text-2xl font-bold text-blue-600">Zerodha</div>
          <div className="text-sm text-gray-500">Real-time prices</div>
        </Card>
      </div>

      {/* Positions Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-4 font-medium text-gray-900">Symbol</th>
                <th className="text-right p-4 font-medium text-gray-900">Quantity</th>
                <th className="text-right p-4 font-medium text-gray-900">Entry Price</th>
                <th className="text-right p-4 font-medium text-gray-900">Current Price</th>
                <th className="text-right p-4 font-medium text-gray-900">Unrealized P&L</th>
                <th className="text-right p-4 font-medium text-gray-900">P&L %</th>
                <th className="text-right p-4 font-medium text-gray-900">SL / Target</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center p-8 text-gray-500">
                    {isLoading ? 'Loading positions...' : 'No open positions - AI will trade via MCP'}
                  </td>
                </tr>
              ) : (
                positions.map((position) => {
                  const pnlIsPositive = position.unrealized_pnl >= 0
                  return (
                    <tr key={position.trade_id} className="border-b hover:bg-gray-50">
                      <td className="p-4">
                        <div className="font-medium text-gray-900">{position.symbol}</div>
                        <div className="text-sm text-gray-500">{position.strategy || 'AI Strategy'}</div>
                      </td>
                      <td className="p-4 text-right font-medium">{position.quantity}</td>
                      <td className="p-4 text-right text-gray-900">
                        {formatCurrency(position.entry_price)}
                      </td>
                      <td className="p-4 text-right font-medium text-gray-900">
                        {formatCurrency(position.current_price)}
                      </td>
                      <td className="p-4 text-right">
                        <div className={`flex items-center justify-end gap-1 font-medium ${getPnLColor(position.unrealized_pnl)}`}>
                          {pnlIsPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                          {formatCurrency(position.unrealized_pnl)}
                        </div>
                      </td>
                      <td className="p-4 text-right">
                        <div className={getPnLColor(position.unrealized_pnl_pct)}>
                          {formatPercent(position.unrealized_pnl_pct)}
                        </div>
                      </td>
                      <td className="p-4 text-right text-sm">
                        {position.stop_loss && (
                          <div className="text-red-600">SL: {formatCurrency(position.stop_loss)}</div>
                        )}
                        {position.target && (
                          <div className="text-green-600">TGT: {formatCurrency(position.target)}</div>
                        )}
                        {!position.stop_loss && !position.target && (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Footer Info */}
      <div className="text-sm text-gray-500 text-center">
        <p>Real-time prices from Zerodha Kite Connect • All trades executed by AI via MCP</p>
      </div>
    </div>
  )
}

export default RealTimePositionsTable
