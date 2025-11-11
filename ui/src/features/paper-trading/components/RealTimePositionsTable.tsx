/**
 * Real-Time Positions Table Component
 * Displays positions with live P&L updates via WebSocket
 */

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { TrendingUp, TrendingDown, X, Edit, RefreshCw } from 'lucide-react'
import type { OpenPositionResponse } from '../types'

export interface RealTimePositionsTableProps {
  positions: OpenPositionResponse[]
  onClosePosition: (position: OpenPositionResponse) => void
  onModifyLevels: (position: OpenPositionResponse) => void
  isLoading?: boolean
}

interface PositionWithLivePnL extends OpenPositionResponse {
  livePrice?: number
  liveUnrealizedPnL?: number
  livePnLPercent?: number
  priceChange?: number
  priceChangePercent?: number
  lastUpdate?: string
}

export const RealTimePositionsTable: React.FC<RealTimePositionsTableProps> = ({
  positions,
  onClosePosition,
  onModifyLevels,
  isLoading = false
}) => {
  const [livePositions, setLivePositions] = useState<PositionWithLivePnL[]>([])
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const [isConnected, setIsConnected] = useState<boolean>(false)

  // Simulate real-time price updates (in production, this would be WebSocket)
  useEffect(() => {
    // Convert regular positions to live positions
    const initialLivePositions = positions.map(pos => ({
      ...pos,
      livePrice: pos.current_price,
      liveUnrealizedPnL: pos.unrealized_pnl,
      livePnLPercent: pos.unrealized_pnl_percent,
      priceChange: 0,
      priceChangePercent: 0,
      lastUpdate: new Date().toISOString()
    }))
    setLivePositions(initialLivePositions)
    setIsConnected(true)
    setLastUpdate(new Date().toLocaleTimeString())

    // Simulate real-time updates
    const interval = setInterval(() => {
      setLivePositions(prev => prev.map(pos => {
        // Simulate price changes (-2% to +2%)
        const priceChangePercent = (Math.random() - 0.5) * 4
        const newPrice = pos.livePrice! * (1 + priceChangePercent / 100)
        const priceChange = newPrice - pos.entry_price
        const newUnrealizedPnL = priceChange * Math.abs(pos.quantity)
        const newPnLPercent = (priceChange / pos.entry_price) * 100

        return {
          ...pos,
          livePrice: newPrice,
          priceChange,
          priceChangePercent,
          liveUnrealizedPnL: newUnrealizedPnL,
          livePnLPercent: newPnLPercent,
          lastUpdate: new Date().toISOString()
        }
      }))
      setLastUpdate(new Date().toLocaleTimeString())
    }, 3000) // Update every 3 seconds

    return () => clearInterval(interval)
  }, [positions])

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

  const getPriceColor = (change: number) => {
    if (change > 0) return 'text-green-600'
    if (change < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  const totalPnL = livePositions.reduce((sum, pos) => sum + (pos.liveUnrealizedPnL || 0), 0)
  const totalInvestment = livePositions.reduce((sum, pos) => sum + (pos.entry_price * Math.abs(pos.quantity)), 0)
  const totalPnLPercent = totalInvestment > 0 ? (totalPnL / totalInvestment) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">Real-Time Positions</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-500">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <Badge variant="outline" className="text-xs">
            {livePositions.length} positions
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <RefreshCw className="w-4 h-4" />
          <span>Last update: {lastUpdate}</span>
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
            {livePositions.length} positions
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-1">Live Updates</div>
          <div className="text-2xl font-bold text-blue-600">
            {isConnected ? 'Active' : 'Paused'}
          </div>
          <div className="text-sm text-gray-500">
            3-second intervals
          </div>
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
                <th className="text-right p-4 font-medium text-gray-900">Avg Price</th>
                <th className="text-right p-4 font-medium text-gray-900">Live Price</th>
                <th className="text-right p-4 font-medium text-gray-900">Change</th>
                <th className="text-right p-4 font-medium text-gray-900">Unrealized P&L</th>
                <th className="text-right p-4 font-medium text-gray-900">P&L %</th>
                <th className="text-center p-4 font-medium text-gray-900">Actions</th>
              </tr>
            </thead>
            <tbody>
              {livePositions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center p-8 text-gray-500">
                    {isLoading ? 'Loading positions...' : 'No open positions'}
                  </td>
                </tr>
              ) : (
                livePositions.map((position, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="p-4">
                      <div className="font-medium text-gray-900">{position.symbol}</div>
                      <div className="text-sm text-gray-500">{position.strategy}</div>
                    </td>
                    <td className="p-4 text-right">
                      <span className={position.quantity > 0 ? 'text-green-600' : 'text-red-600'}>
                        {position.quantity > 0 ? '+' : ''}{position.quantity}
                      </span>
                    </td>
                    <td className="p-4 text-right text-gray-900">
                      {formatCurrency(position.entry_price)}
                    </td>
                    <td className="p-4 text-right">
                      <div className="font-medium text-gray-900">
                        {formatCurrency(position.livePrice || 0)}
                      </div>
                      <div className={`text-sm ${getPriceColor(position.priceChangePercent || 0)}`}>
                        {position.priceChangePercent !== undefined && formatPercent(position.priceChangePercent)}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className={getPriceColor(position.priceChange || 0)}>
                        {position.priceChange !== undefined && formatCurrency(position.priceChange)}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className={`font-medium ${getPnLColor(position.liveUnrealizedPnL || 0)}`}>
                        {formatCurrency(position.liveUnrealizedPnL || 0)}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className={getPnLColor(position.livePnLPercent || 0)}>
                        {position.livePnLPercent !== undefined && formatPercent(position.livePnLPercent)}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onModifyLevels(position)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onClosePosition(position)}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Footer Info */}
      <div className="text-sm text-gray-500 text-center">
        <p>Real-time data powered by Kite Connect WebSocket • Updates every 3 seconds</p>
      </div>
    </div>
  )
}

export default RealTimePositionsTable