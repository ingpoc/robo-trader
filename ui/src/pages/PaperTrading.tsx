/**
 * Paper Trading Page
 * Main interface for paper trading account management
 */

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { usePaperTrading } from '@/hooks/usePaperTrading'
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Wallet,
  AlertCircle,
  RefreshCw,
  Plus,
  X,
  Target,
  Activity,
} from 'lucide-react'

const ACCOUNT_ID = 'paper_swing_main' // Default account - can be made dynamic

export function PaperTrading() {
  const {
    accountOverview,
    positions,
    trades,
    metrics,
    totalUnrealizedPnL,
    unrealizedPnLPct,
    isLoading,
    isError,
    executeBuy,
    executeSell,
    closePosition,
    executeBuyLoading,
    executeSellLoading,
    refetchAccountOverview,
    refetchPositions,
  } = usePaperTrading(ACCOUNT_ID)

  const [tradeForm, setTradeForm] = useState({
    symbol: '',
    quantity: '',
    price: '',
    stopLoss: '',
    target: '',
    rationale: '',
    type: 'BUY' as 'BUY' | 'SELL',
  })

  const [closeForm, setCloseForm] = useState<{ tradeId: string; exitPrice: string } | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  const handleExecuteTrade = async () => {
    if (!tradeForm.symbol || !tradeForm.quantity || !tradeForm.price) {
      alert('Please fill in symbol, quantity, and price')
      return
    }

    const tradeData = {
      symbol: tradeForm.symbol.toUpperCase(),
      quantity: parseInt(tradeForm.quantity),
      entry_price: parseFloat(tradeForm.price),
      strategy_rationale: tradeForm.rationale || 'Manual trade',
      stop_loss: tradeForm.stopLoss ? parseFloat(tradeForm.stopLoss) : undefined,
      target_price: tradeForm.target ? parseFloat(tradeForm.target) : undefined,
    }

    if (tradeForm.type === 'BUY') {
      executeBuy(tradeData as any)
    } else {
      executeSell(tradeData as any)
    }

    // Reset form
    setTradeForm({
      symbol: '',
      quantity: '',
      price: '',
      stopLoss: '',
      target: '',
      rationale: '',
      type: 'BUY',
    })
  }

  const handleClosePosition = (tradeId: string, currentPrice: number) => {
    setCloseForm({ tradeId, exitPrice: currentPrice.toString() })
  }

  const confirmClosePosition = () => {
    if (!closeForm) return

    closePosition({
      tradeId: closeForm.tradeId,
      exit_price: parseFloat(closeForm.exitPrice),
      reason: 'Manual close',
    })

    setCloseForm(null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
          <p>Loading paper trading account...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>Failed to load paper trading account. Please try again.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Paper Trading</h1>
          <p className="text-muted-foreground">
            Account: <span className="font-mono">{ACCOUNT_ID}</span>
          </p>
        </div>
        <Button onClick={refetchAccountOverview} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Account Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {accountOverview && (
          <>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Account Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">₹{accountOverview.balance.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Buying Power: ₹{accountOverview.buying_power.toLocaleString()}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Deployed Capital
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ₹{accountOverview.deployed_capital.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {accountOverview.open_positions_count} position(s) open
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Monthly P&L
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className={`text-2xl font-bold ${
                    accountOverview.monthly_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  ₹{accountOverview.monthly_pnl.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {accountOverview.monthly_pnl_pct.toFixed(2)}%
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Win Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{accountOverview.win_rate.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Total Trades: {metrics?.total_trades || 0}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Main Content - Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="execute">Execute Trade</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Unrealized P&L Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Unrealized P&L
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-muted-foreground text-sm">Total</p>
                    <p className={`text-3xl font-bold ${totalUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ₹{Math.abs(totalUnrealizedPnL).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-muted-foreground text-sm">Percentage</p>
                    <p className={`text-2xl font-bold ${unrealizedPnLPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {unrealizedPnLPct.toFixed(2)}%
                    </p>
                  </div>
                </div>
                {positions.length > 0 && (
                  <div className="pt-2 border-t space-y-2">
                    {positions.slice(0, 5).map((pos) => (
                      <div key={pos.trade_id} className="flex justify-between text-sm">
                        <span className="font-medium">{pos.symbol}</span>
                        <span className={pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          ₹{pos.unrealized_pnl.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Performance Metrics */}
            {metrics && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Performance Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Winning Trades</p>
                      <p className="font-bold text-green-600">{metrics.winning_trades}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Losing Trades</p>
                      <p className="font-bold text-red-600">{metrics.losing_trades}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Avg Win</p>
                      <p className="font-bold">₹{metrics.avg_win.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Avg Loss</p>
                      <p className="font-bold">₹{metrics.avg_loss.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Profit Factor</p>
                      <p className="font-bold">{metrics.profit_factor.toFixed(2)}x</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Best Trade</p>
                      <p className="font-bold text-green-600">₹{metrics.largest_win.toLocaleString()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Execute Trade Tab */}
        <TabsContent value="execute">
          <Card>
            <CardHeader>
              <CardTitle>Execute Trade</CardTitle>
              <CardDescription>Enter trade details to execute BUY or SELL orders</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 sm:col-span-1">
                  <Label>Trade Type</Label>
                  <Select
                    value={tradeForm.type}
                    onChange={(e) => setTradeForm({ ...tradeForm, type: e.target.value as any })}
                    options={[
                      { value: 'BUY', label: 'BUY' },
                      { value: 'SELL', label: 'SELL' }
                    ]}
                  />
                </div>

                <div className="col-span-2 sm:col-span-1">
                  <Label>Symbol</Label>
                  <Input
                    placeholder="e.g., RELIANCE"
                    value={tradeForm.symbol}
                    onChange={(e) => setTradeForm({ ...tradeForm, symbol: e.target.value })}
                  />
                </div>

                <div className="col-span-1">
                  <Label>Quantity</Label>
                  <Input
                    type="number"
                    placeholder="0"
                    value={tradeForm.quantity}
                    onChange={(e) => setTradeForm({ ...tradeForm, quantity: e.target.value })}
                  />
                </div>

                <div className="col-span-1">
                  <Label>Price (₹)</Label>
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={tradeForm.price}
                    onChange={(e) => setTradeForm({ ...tradeForm, price: e.target.value })}
                  />
                </div>

                <div className="col-span-1">
                  <Label>Stop Loss (₹)</Label>
                  <Input
                    type="number"
                    placeholder="Optional"
                    value={tradeForm.stopLoss}
                    onChange={(e) => setTradeForm({ ...tradeForm, stopLoss: e.target.value })}
                  />
                </div>

                <div className="col-span-1">
                  <Label>Target Price (₹)</Label>
                  <Input
                    type="number"
                    placeholder="Optional"
                    value={tradeForm.target}
                    onChange={(e) => setTradeForm({ ...tradeForm, target: e.target.value })}
                  />
                </div>

                <div className="col-span-2">
                  <Label>Strategy Rationale</Label>
                  <Input
                    placeholder="Why are you making this trade?"
                    value={tradeForm.rationale}
                    onChange={(e) => setTradeForm({ ...tradeForm, rationale: e.target.value })}
                  />
                </div>
              </div>

              <Button
                onClick={handleExecuteTrade}
                disabled={executeBuyLoading || executeSellLoading}
                className={`w-full ${tradeForm.type === 'BUY' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {executeBuyLoading || executeSellLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Execute {tradeForm.type}
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Positions Tab */}
        <TabsContent value="positions">
          <Card>
            <CardHeader>
              <CardTitle>Open Positions ({positions.length})</CardTitle>
              <CardDescription>Currently open trades with real-time P&L</CardDescription>
            </CardHeader>
            <CardContent>
              {positions.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">No open positions</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Symbol</th>
                        <th className="text-center">Type</th>
                        <th className="text-right">Qty</th>
                        <th className="text-right">Entry</th>
                        <th className="text-right">Current</th>
                        <th className="text-right">P&L</th>
                        <th className="text-center">%</th>
                        <th className="text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos) => (
                        <tr key={pos.trade_id} className="border-b hover:bg-muted/50">
                          <td className="py-3 font-medium">{pos.symbol}</td>
                          <td className="text-center">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                pos.trade_type === 'BUY'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {pos.trade_type}
                            </span>
                          </td>
                          <td className="text-right">{pos.quantity}</td>
                          <td className="text-right">₹{pos.entry_price.toFixed(2)}</td>
                          <td className="text-right">₹{pos.current_price.toFixed(2)}</td>
                          <td className={`text-right font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            ₹{pos.unrealized_pnl.toLocaleString()}
                          </td>
                          <td className={`text-center font-bold ${pos.unrealized_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {pos.unrealized_pnl_pct.toFixed(2)}%
                          </td>
                          <td className="text-center">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleClosePosition(pos.trade_id, pos.current_price)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Close Position Dialog */}
          {closeForm && (
            <Card className="mt-4 border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="text-lg">Close Position</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Exit Price (₹)</Label>
                  <Input
                    type="number"
                    value={closeForm.exitPrice}
                    onChange={(e) => setCloseForm({ ...closeForm, exitPrice: e.target.value })}
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={confirmClosePosition} className="flex-1 bg-orange-600 hover:bg-orange-700">
                    Confirm Close
                  </Button>
                  <Button onClick={() => setCloseForm(null)} variant="outline" className="flex-1">
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Trade History</CardTitle>
              <CardDescription>Recently closed trades</CardDescription>
            </CardHeader>
            <CardContent>
              {trades.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">No closed trades</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Symbol</th>
                        <th className="text-center">Type</th>
                        <th className="text-right">Qty</th>
                        <th className="text-right">Entry</th>
                        <th className="text-right">Exit</th>
                        <th className="text-right">P&L</th>
                        <th className="text-center">%</th>
                        <th className="text-center">Days</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((trade) => (
                        <tr key={trade.trade_id} className="border-b hover:bg-muted/50">
                          <td className="py-3 font-medium">{trade.symbol}</td>
                          <td className="text-center">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                trade.trade_type === 'BUY'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {trade.trade_type}
                            </span>
                          </td>
                          <td className="text-right">{trade.quantity}</td>
                          <td className="text-right">₹{trade.entry_price.toFixed(2)}</td>
                          <td className="text-right">₹{trade.exit_price.toFixed(2)}</td>
                          <td className={`text-right font-bold ${trade.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            ₹{trade.realized_pnl.toLocaleString()}
                          </td>
                          <td className={`text-center font-bold ${trade.realized_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {trade.realized_pnl_pct.toFixed(2)}%
                          </td>
                          <td className="text-center">{trade.holding_period_days}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default PaperTrading
