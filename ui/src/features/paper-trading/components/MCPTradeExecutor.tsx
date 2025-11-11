/**
 * MCP Trade Executor Component
 * Executes trades through MCP tools instead of manual forms
 */

import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { PlayCircle, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react'
import type { AccountOverviewResponse, OpenPositionResponse } from '../types'

export interface MCPTradeExecutorProps {
  accountOverview: AccountOverviewResponse | null
  onExecuteTrade: (tradeData: any) => Promise<void>
  isLoading?: boolean
}

interface QuickTradeAction {
  symbol: string
  action: 'BUY' | 'SELL'
  quantity: number
  reason: string
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH'
}

export const MCPTradeExecutor: React.FC<MCPTradeExecutorProps> = ({
  accountOverview,
  onExecuteTrade,
  isLoading = false
}) => {
  const [isExecuting, setIsExecuting] = useState(false)
  const [selectedAction, setSelectedAction] = useState<QuickTradeAction | null>(null)

  // Quick trade suggestions based on AI analysis
  const quickTradeSuggestions: QuickTradeAction[] = [
    {
      symbol: 'RELIANCE',
      action: 'BUY',
      quantity: 10,
      reason: 'Strong fundamentals, technical breakout above ₹2500',
      riskLevel: 'MEDIUM'
    },
    {
      symbol: 'TCS',
      action: 'SELL',
      quantity: 5,
      reason: 'Profit taking after 15% rally, overbought RSI',
      riskLevel: 'LOW'
    }
  ]

  const handleQuickTrade = async (action: QuickTradeAction) => {
    setSelectedAction(action)
    setIsExecuting(true)

    try {
      // Execute trade via MCP tools
      await onExecuteTrade({
        symbol: action.symbol,
        action: action.action,
        quantity: action.quantity,
        order_type: 'MARKET',
        product: 'CNC',
        account_id: 'paper_swing_main'
      })
    } finally {
      setIsExecuting(false)
      setSelectedAction(null)
    }
  }

  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return 'bg-green-100 text-green-800'
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800'
      case 'HIGH': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getActionIcon = (action: 'BUY' | 'SELL') => {
    return action === 'BUY' ? (
      <TrendingUp className="w-4 h-4 text-green-600" />
    ) : (
      <TrendingDown className="w-4 h-4 text-red-600" />
    )
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <PlayCircle className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">MCP Trade Execution</h3>
          <Badge variant="outline" className="text-xs">
            AI-Powered
          </Badge>
        </div>
        <div className="text-sm text-gray-500">
          Execute trades via Claude Agent SDK
        </div>
      </div>

      {/* Account Summary */}
      {accountOverview && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="font-medium text-blue-900">Available Balance:</span>
              <span className="ml-2 text-blue-700">
                ₹{accountOverview.balance.toLocaleString('en-IN')}
              </span>
            </div>
            <div className="text-sm">
              <span className="font-medium text-blue-900">Buying Power:</span>
              <span className="ml-2 text-blue-700">
                ₹{accountOverview.balance.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* AI Trade Suggestions */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <h4 className="font-medium text-gray-900">AI Trade Suggestions</h4>
          <Badge variant="outline" className="text-xs">
            {quickTradeSuggestions.length} opportunities
          </Badge>
        </div>

        {quickTradeSuggestions.map((suggestion, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  {getActionIcon(suggestion.action)}
                  <span className="font-semibold text-lg">
                    {suggestion.action} {suggestion.symbol}
                  </span>
                  <Badge className={getRiskBadgeColor(suggestion.riskLevel)}>
                    {suggestion.riskLevel} RISK
                  </Badge>
                </div>

                <p className="text-sm text-gray-600 mb-3">
                  {suggestion.reason}
                </p>

                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span>Quantity: {suggestion.quantity} shares</span>
                  <span>•</span>
                  <span>Estimated Value: ~₹{(suggestion.quantity * 2500).toLocaleString('en-IN')}</span>
                </div>
              </div>

              <Button
                onClick={() => handleQuickTrade(suggestion)}
                disabled={isLoading || isExecuting}
                variant={suggestion.action === 'BUY' ? 'default' : 'destructive'}
                className="ml-4"
              >
                {isExecuting && selectedAction?.symbol === suggestion.symbol ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Executing...
                  </>
                ) : (
                  <>
                    {getActionIcon(suggestion.action)}
                    Execute {suggestion.action}
                  </>
                )}
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Info Section */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h5 className="font-medium text-gray-900 mb-2">How MCP Trading Works</h5>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Trades are executed via Claude Agent SDK with real market prices</li>
          <li>• Each trade includes risk analysis and strategy validation</li>
          <li>• Real-time P&L tracking via WebSocket connections</li>
          <li>• All trades are logged for transparency and learning</li>
        </ul>
      </div>
    </Card>
  )
}

export default MCPTradeExecutor