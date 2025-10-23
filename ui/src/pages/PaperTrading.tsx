/**
 * Paper Trading Page
 * Main interface for paper trading account management
 */

import React, { useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { usePaperTrading } from '@/hooks/usePaperTrading'
import { useAccount } from '@/contexts/AccountContext'
import { AccountSelector } from '@/components/AccountSelector'
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
  Shield,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react'

export function PaperTrading() {
  const { selectedAccount } = useAccount()

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
  } = usePaperTrading(selectedAccount?.account_id)

  const [tradeForm, setTradeForm] = useState({
    symbol: '',
    quantity: '',
    price: '',
    stopLoss: '',
    target: '',
    rationale: '',
    strategy: '',
    type: 'BUY' as 'BUY' | 'SELL',
  })

  const [closeForm, setCloseForm] = useState<{ tradeId: string; exitPrice: string } | null>(null)
  const [modifyStopLossTarget, setModifyStopLossTarget] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [showRiskDialog, setShowRiskDialog] = useState(false)
  const [pendingTrade, setPendingTrade] = useState<any>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  // Risk validation logic
  const validateTrade = useMemo(() => {
    if (!accountOverview || !tradeForm.symbol || !tradeForm.quantity || !tradeForm.price) {
      return { isValid: false, errors: [], warnings: [], riskLevel: 'low' as const }
    }

    const quantity = parseInt(tradeForm.quantity)
    const price = parseFloat(tradeForm.price)
    const tradeValue = quantity * price
    const errors: string[] = []
    const warnings: string[] = []
    let riskLevel: 'low' | 'medium' | 'high' = 'low'

    // Buying power check
    if (tradeForm.type === 'BUY' && tradeValue > accountOverview.buying_power) {
      errors.push(`Insufficient buying power. Required: ₹${tradeValue.toLocaleString()}, Available: ₹${accountOverview.buying_power.toLocaleString()}`)
    }

    // Position size limits (5% of portfolio max)
    const maxPositionSize = accountOverview.balance * 0.05
    if (tradeValue > maxPositionSize) {
      errors.push(`Position size exceeds 5% limit. Max allowed: ₹${maxPositionSize.toLocaleString()}`)
      riskLevel = 'high'
    } else if (tradeValue > maxPositionSize * 0.8) {
      warnings.push(`Position size is 80% of maximum limit`)
      riskLevel = 'medium'
    }

    // Portfolio risk check (10% max total exposure)
    const currentExposure = accountOverview.deployed_capital
    const maxPortfolioRisk = accountOverview.balance * 0.10
    if (tradeForm.type === 'BUY' && currentExposure + tradeValue > maxPortfolioRisk) {
      errors.push(`Trade would exceed 10% portfolio risk limit`)
      riskLevel = 'high'
    } else if (tradeForm.type === 'BUY' && currentExposure + tradeValue > maxPortfolioRisk * 0.8) {
      warnings.push(`Trade would bring portfolio exposure to 80% of risk limit`)
      riskLevel = 'medium'
    }

    // Stop loss validation
    if (tradeForm.stopLoss) {
      const stopLoss = parseFloat(tradeForm.stopLoss)

      // Validate stop loss direction based on trade type
      if (tradeForm.type === 'BUY' && stopLoss >= price) {
        errors.push('Stop loss must be below entry price for BUY orders')
      } else if (tradeForm.type === 'SELL' && stopLoss <= price) {
        errors.push('Stop loss must be above entry price for SELL orders')
      }

      const stopLossPct = Math.abs(price - stopLoss) / price * 100

      if (stopLossPct < 0.5) {
        warnings.push('Stop loss is very tight (< 0.5% from entry)')
        riskLevel = riskLevel === 'low' ? 'medium' : riskLevel
      } else if (stopLossPct > 15) {
        warnings.push('Stop loss is very wide (> 15% from entry)')
      }
    } else {
      warnings.push('No stop loss set - consider adding risk protection')
      riskLevel = riskLevel === 'low' ? 'medium' : riskLevel
    }

    // Target price validation
    if (tradeForm.target) {
      const target = parseFloat(tradeForm.target)

      // Validate target direction based on trade type
      if (tradeForm.type === 'BUY' && target <= price) {
        errors.push('Target price must be above entry price for BUY orders')
      } else if (tradeForm.type === 'SELL' && target >= price) {
        errors.push('Target price must be below entry price for SELL orders')
      }

      const targetPct = Math.abs(price - target) / price * 100

      if (targetPct < 1) {
        warnings.push('Target is very close (< 1% from entry)')
      } else if (targetPct > 50) {
        warnings.push('Target is very ambitious (> 50% from entry)')
      }
    }

    // Check for existing position in same symbol
    const existingPosition = positions.find(p => p.symbol === tradeForm.symbol.toUpperCase())
    if (existingPosition && tradeForm.type === 'BUY') {
      warnings.push(`Already have position in ${tradeForm.symbol}. Consider if this increases concentration risk.`)
      riskLevel = riskLevel === 'low' ? 'medium' : riskLevel
    }

    // Check for strategy rationale if AI suggested
    if (!tradeForm.rationale.trim()) {
      warnings.push('Strategy rationale helps Claude learn from trades')
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      riskLevel
    }
  }, [accountOverview, tradeForm, positions])

  const handleExecuteTrade = async () => {
    if (!tradeForm.symbol || !tradeForm.quantity || !tradeForm.price) {
      setValidationErrors(['Please fill in symbol, quantity, and price'])
      return
    }

    const validation = validateTrade
    setValidationErrors(validation.errors)

    if (!validation.isValid) {
      return
    }

    // For high-risk trades, show confirmation dialog
    if (validation.riskLevel === 'high' || validation.warnings.length > 0) {
      setPendingTrade({
        symbol: tradeForm.symbol.toUpperCase(),
        quantity: parseInt(tradeForm.quantity),
        entry_price: parseFloat(tradeForm.price),
        strategy_rationale: tradeForm.rationale || 'Manual trade',
        stop_loss: tradeForm.stopLoss ? parseFloat(tradeForm.stopLoss) : undefined,
        target_price: tradeForm.target ? parseFloat(tradeForm.target) : undefined,
        type: tradeForm.type,
        validation
      })
      setShowRiskDialog(true)
      return
    }

    // Execute trade directly for low-risk trades
    executeValidatedTrade({
      symbol: tradeForm.symbol.toUpperCase(),
      quantity: parseInt(tradeForm.quantity),
      entry_price: parseFloat(tradeForm.price),
      strategy_rationale: tradeForm.rationale || 'Manual trade',
      strategy: tradeForm.strategy || 'manual',
      stop_loss: tradeForm.stopLoss ? parseFloat(tradeForm.stopLoss) : undefined,
      target_price: tradeForm.target ? parseFloat(tradeForm.target) : undefined,
    })
  }

  const executeValidatedTrade = (tradeData: any) => {
    if (tradeData.type === 'BUY') {
      executeBuy(tradeData)
    } else {
      executeSell(tradeData)
    }

    // Reset form
    setTradeForm({
      symbol: '',
      quantity: '',
      price: '',
      stopLoss: '',
      target: '',
      rationale: '',
      strategy: '',
      type: 'BUY',
    })
    setValidationErrors([])
  }

  const confirmHighRiskTrade = () => {
    if (pendingTrade) {
      executeValidatedTrade(pendingTrade)
      setShowRiskDialog(false)
      setPendingTrade(null)
    }
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

  if (!selectedAccount) {
    return (
      <div className="space-y-6 p-6">
        <AccountSelector />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <Wallet className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Account Selected</h2>
            <p className="text-muted-foreground mb-4">Please select or create a trading account to continue</p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <AccountSelector />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
            <p>Loading paper trading account...</p>
          </div>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-6 p-6">
        <AccountSelector />
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Failed to load paper trading account. Please try again.</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Account Selector */}
      <AccountSelector />

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Paper Trading</h1>
          <p className="text-muted-foreground">
            Account: <span className="font-mono">{selectedAccount?.account_id || 'No account selected'}</span>
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
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="swing">Swing Trading</TabsTrigger>
          <TabsTrigger value="options">Options Trading</TabsTrigger>
          <TabsTrigger value="ai-learning">AI Learning</TabsTrigger>
          <TabsTrigger value="execute">Execute Trade</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* Swing Trading Tab */}
        <TabsContent value="swing" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Unrealized P&L Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Unrealized P&L
                  <div className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    Live Prices
                  </div>
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

        {/* Options Trading Tab */}
        <TabsContent value="options" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Options Trading - Coming Soon</CardTitle>
              <CardDescription>
                Advanced options strategies, Greeks monitoring, and spread management for Claude's learning
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Shield className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-xl font-semibold mb-2">Options Trading Interface</h3>
                <p className="text-muted-foreground mb-4">
                  This section will include options chains, Greeks dashboard, spread strategies, and premium tracking
                  to help Claude master options trading through paper trading practice.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <h4 className="font-medium mb-2">Greeks Monitoring</h4>
                    <p className="text-sm text-muted-foreground">Delta, Gamma, Theta, Vega tracking</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <h4 className="font-medium mb-2">Spread Strategies</h4>
                    <p className="text-sm text-muted-foreground">Iron condors, call spreads, protective puts</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <h4 className="font-medium mb-2">Premium Flow</h4>
                    <p className="text-sm text-muted-foreground">Collected vs paid premium tracking</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Learning Tab */}
        <TabsContent value="ai-learning" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Claude's Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-copper-500" />
                  Claude's Learning Progress
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-emerald-50 rounded-lg">
                    <p className="text-2xl font-bold text-emerald-600">
                      {accountOverview?.win_rate.toFixed(1)}%
                    </p>
                    <p className="text-sm text-emerald-700">Win Rate</p>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600">
                      {metrics?.total_trades || 0}
                    </p>
                    <p className="text-sm text-blue-700">Total Trades</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Token Usage Today</span>
                    <span className="font-medium">2,450 / 10,000</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div className="bg-copper-500 h-2 rounded-full" style={{ width: '24.5%' }}></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Strategy Effectiveness */}
            <Card>
              <CardHeader>
                <CardTitle>Strategy Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-muted/50 rounded">
                    <span className="font-medium">Breakout Trading</span>
                    <span className="text-emerald-600 font-bold">68% Win Rate</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted/50 rounded">
                    <span className="font-medium">RSI Divergence</span>
                    <span className="text-emerald-600 font-bold">72% Win Rate</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted/50 rounded">
                    <span className="font-medium">Mean Reversion</span>
                    <span className="text-rose-600 font-bold">45% Win Rate</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Daily Strategy Log */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-copper-500" />
                Claude's Daily Strategy Log
              </CardTitle>
              <CardDescription>
                AI's self-reflection and learning insights from today's trading
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-l-4 border-copper-500 pl-4">
                <h4 className="font-semibold text-copper-800">What worked today:</h4>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• RSI divergence at support levels worked 2/3 times</li>
                  <li>• Swing trades held 2-3 days performed better than intraday</li>
                  <li>• Stop losses at 2% below entry prevented larger losses</li>
                </ul>
              </div>

              <div className="border-l-4 border-rose-500 pl-4">
                <h4 className="font-semibold text-rose-800">What didn't work:</h4>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• Breakout trades on low volume failed consistently</li>
                  <li>• Averaging down increased losses in trending markets</li>
                  <li>• Wide stop losses (5%+) led to premature exits</li>
                </ul>
              </div>

              <div className="border-l-4 border-blue-500 pl-4">
                <h4 className="font-semibold text-blue-800">Tomorrow's focus:</h4>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• Watch for RSI 30 level breakouts with volume confirmation</li>
                  <li>• Avoid averaging down - strict 2% stop loss rule</li>
                  <li>• Focus on 2-3 day swing trades in large cap stocks</li>
                </ul>
              </div>

              <div className="flex justify-between items-center pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  Token usage: 2,450 / 10,000 remaining today
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    Ask Claude for Advice
                  </Button>
                  <Button size="sm" className="bg-copper-600 hover:bg-copper-700">
                    Save Strategy Notes
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Execute Trade Tab */}
        <TabsContent value="execute">
          <div className="space-y-4">
            {/* Risk Status Indicators */}
            {accountOverview && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="border-green-200 bg-green-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      <div>
                        <p className="text-sm font-medium text-green-800">Buying Power</p>
                        <p className="text-lg font-bold text-green-900">₹{accountOverview.buying_power.toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-blue-200 bg-blue-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <Shield className="w-5 h-5 text-blue-600" />
                      <div>
                        <p className="text-sm font-medium text-blue-800">Max Position Size</p>
                        <p className="text-lg font-bold text-blue-900">₹{(accountOverview.balance * 0.05).toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-orange-200 bg-orange-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-orange-600" />
                      <div>
                        <p className="text-sm font-medium text-orange-800">Portfolio Risk Limit</p>
                        <p className="text-lg font-bold text-orange-900">₹{(accountOverview.balance * 0.10).toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Trade Form */}
            <Card>
              <CardHeader>
                <CardTitle>Execute Trade</CardTitle>
                <CardDescription>Enter trade details to execute BUY or SELL orders</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Validation Errors */}
                {validationErrors.length > 0 && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1">
                        {validationErrors.map((error, index) => (
                          <li key={index}>{error}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Risk Warnings */}
                {validateTrade.warnings.length > 0 && validationErrors.length === 0 && (
                  <Alert className="border-yellow-200 bg-yellow-50">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1">
                        {validateTrade.warnings.map((warning, index) => (
                          <li key={index} className="text-yellow-800">{warning}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Risk Level Indicator */}
                {tradeForm.symbol && tradeForm.quantity && tradeForm.price && (
                  <div className={`flex items-center gap-2 p-3 rounded-lg border ${
                    validateTrade.riskLevel === 'high' ? 'bg-red-50 border-red-200' :
                    validateTrade.riskLevel === 'medium' ? 'bg-yellow-50 border-yellow-200' :
                    'bg-green-50 border-green-200'
                  }`}>
                    <Shield className={`w-5 h-5 ${
                      validateTrade.riskLevel === 'high' ? 'text-red-600' :
                      validateTrade.riskLevel === 'medium' ? 'text-yellow-600' :
                      'text-green-600'
                    }`} />
                    <div>
                      <p className="text-sm font-medium">Risk Level: {validateTrade.riskLevel.toUpperCase()}</p>
                      <p className="text-xs text-muted-foreground">
                        {validateTrade.riskLevel === 'high' ? 'High risk - confirmation required' :
                         validateTrade.riskLevel === 'medium' ? 'Medium risk - review warnings' :
                         'Low risk - safe to proceed'}
                      </p>
                    </div>
                  </div>
                )}

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

                  <div className="col-span-2 sm:col-span-1">
                    <Label>Strategy Tag</Label>
                    <Select
                      value={tradeForm.strategy || ''}
                      onChange={(e) => setTradeForm({ ...tradeForm, strategy: e.target.value })}
                      options={[
                        { value: 'breakout', label: 'Breakout' },
                        { value: 'mean_reversion', label: 'Mean Reversion' },
                        { value: 'trend_following', label: 'Trend Following' },
                        { value: 'rsi_divergence', label: 'RSI Divergence' },
                        { value: 'support_resistance', label: 'Support/Resistance' },
                        { value: 'other', label: 'Other' }
                      ]}
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
                </div>

                {/* Risk-Reward Analysis */}
                {tradeForm.price && tradeForm.quantity && (tradeForm.stopLoss || tradeForm.target) && (
                  <div className="mt-4 p-4 bg-muted/50 rounded-lg border">
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      Risk-Reward Analysis
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      {tradeForm.stopLoss && (
                        <div className="space-y-1">
                          <p className="text-muted-foreground">Stop Loss P&L</p>
                          <p className={`font-bold ${tradeForm.type === 'BUY' ? 'text-red-600' : 'text-green-600'}`}>
                            ₹{((parseFloat(tradeForm.stopLoss) - parseFloat(tradeForm.price)) * parseInt(tradeForm.quantity) * (tradeForm.type === 'BUY' ? -1 : 1)).toLocaleString()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {Math.abs(((parseFloat(tradeForm.stopLoss) - parseFloat(tradeForm.price)) / parseFloat(tradeForm.price)) * 100).toFixed(2)}% from entry
                          </p>
                        </div>
                      )}

                      {tradeForm.target && (
                        <div className="space-y-1">
                          <p className="text-muted-foreground">Target P&L</p>
                          <p className={`font-bold ${tradeForm.type === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                            ₹{((parseFloat(tradeForm.target) - parseFloat(tradeForm.price)) * parseInt(tradeForm.quantity) * (tradeForm.type === 'BUY' ? 1 : -1)).toLocaleString()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {Math.abs(((parseFloat(tradeForm.target) - parseFloat(tradeForm.price)) / parseFloat(tradeForm.price)) * 100).toFixed(2)}% from entry
                          </p>
                        </div>
                      )}

                      {tradeForm.stopLoss && tradeForm.target && (
                        <div className="space-y-1">
                          <p className="text-muted-foreground">Risk-Reward Ratio</p>
                          <p className="font-bold text-blue-600">
                            1:{((Math.abs(parseFloat(tradeForm.target) - parseFloat(tradeForm.price)) / Math.abs(parseFloat(tradeForm.stopLoss) - parseFloat(tradeForm.price)))).toFixed(2)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {((Math.abs(parseFloat(tradeForm.target) - parseFloat(tradeForm.price)) / Math.abs(parseFloat(tradeForm.stopLoss) - parseFloat(tradeForm.price))) >= 2) ? '✅ Good ratio' : '⚠️ Consider better ratio'}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">

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
                  disabled={executeBuyLoading || executeSellLoading || !validateTrade.isValid}
                  className={`w-full ${
                    validateTrade.riskLevel === 'high' ? 'bg-red-600 hover:bg-red-700' :
                    validateTrade.riskLevel === 'medium' ? 'bg-yellow-600 hover:bg-yellow-700' :
                    tradeForm.type === 'BUY' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                  }`}
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
          </div>
        </TabsContent>

        {/* Positions Tab */}
        <TabsContent value="positions">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Open Positions ({positions.length})
                <div className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  Real-time P&L
                </div>
              </CardTitle>
              <CardDescription>Currently open trades with live market prices and unrealized P&L</CardDescription>
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
                        <th className="text-right">Stop Loss</th>
                        <th className="text-right">Target</th>
                        <th className="text-right">P&L</th>
                        <th className="text-center">%</th>
                        <th className="text-center">Strategy</th>
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
                          <td className="text-right">
                            <div className="flex items-center gap-1">
                              <span>₹{pos.current_price.toFixed(2)}</span>
                              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" title="Real-time price from market data" />
                            </div>
                          </td>
                          <td className="text-right">
                            {pos.stop_loss ? (
                              <div className="space-y-1">
                                <div className="font-medium">₹{pos.stop_loss.toFixed(2)}</div>
                                <div className={`text-xs ${pos.current_price <= pos.stop_loss ? 'text-red-600 font-bold' : 'text-muted-foreground'}`}>
                                  {pos.current_price <= pos.stop_loss ? '⚠️ AT RISK' : `${(((pos.stop_loss - pos.entry_price) / pos.entry_price) * 100 * (pos.trade_type === 'BUY' ? -1 : 1)).toFixed(1)}%`}
                                </div>
                              </div>
                            ) : (
                              <span className="text-muted-foreground text-sm">-</span>
                            )}
                          </td>
                          <td className="text-right">
                            {pos.target_price ? (
                              <div className="space-y-1">
                                <div className="font-medium">₹{pos.target_price.toFixed(2)}</div>
                                <div className={`text-xs ${pos.current_price >= pos.target_price ? 'text-green-600 font-bold' : 'text-muted-foreground'}`}>
                                  {pos.current_price >= pos.target_price ? '🎯 TARGET HIT' : `${(((pos.target_price - pos.entry_price) / pos.entry_price) * 100 * (pos.trade_type === 'BUY' ? 1 : -1)).toFixed(1)}%`}
                                </div>
                              </div>
                            ) : (
                              <span className="text-muted-foreground text-sm">-</span>
                            )}
                          </td>
                          <td className={`text-right font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            ₹{pos.unrealized_pnl.toLocaleString()}
                          </td>
                          <td className={`text-center font-bold ${pos.unrealized_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {pos.unrealized_pnl_pct.toFixed(2)}%
                          </td>
                          <td className="text-center">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium capitalize">
                              {pos.strategy_rationale?.split(' ')[0] || 'Manual'}
                            </span>
                          </td>
                          <td className="text-center">
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleClosePosition(pos.trade_id, pos.current_price)}
                                title="Close Position"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setModifyStopLossTarget(pos)}
                                title="Modify Stop Loss/Target"
                              >
                                <Target className="w-4 h-4" />
                              </Button>
                            </div>
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

          {/* Modify Stop Loss/Target Dialog */}
          {modifyStopLossTarget && (
            <Card className="mt-4 border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Modify Stop Loss & Target
                </CardTitle>
                <CardDescription>
                  Update risk management levels for {modifyStopLossTarget.symbol}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Stop Loss (₹)</Label>
                    <Input
                      type="number"
                      placeholder="Remove stop loss"
                      defaultValue={modifyStopLossTarget.stop_loss || ''}
                      onChange={(e) => {
                        const value = e.target.value;
                        setModifyStopLossTarget({
                          ...modifyStopLossTarget,
                          stop_loss: value ? parseFloat(value) : undefined
                        });
                      }}
                    />
                  </div>
                  <div>
                    <Label>Target Price (₹)</Label>
                    <Input
                      type="number"
                      placeholder="Remove target"
                      defaultValue={modifyStopLossTarget.target_price || ''}
                      onChange={(e) => {
                        const value = e.target.value;
                        setModifyStopLossTarget({
                          ...modifyStopLossTarget,
                          target_price: value ? parseFloat(value) : undefined
                        });
                      }}
                    />
                  </div>
                </div>

                {/* Risk-Reward Preview */}
                {modifyStopLossTarget.stop_loss && modifyStopLossTarget.target_price && (
                  <div className="p-3 bg-white/50 rounded border">
                    <p className="text-sm font-medium mb-2">Risk-Reward Preview</p>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Risk (Stop Loss)</p>
                        <p className="font-bold text-red-600">
                          ₹{((modifyStopLossTarget.stop_loss - modifyStopLossTarget.entry_price) * modifyStopLossTarget.quantity * (modifyStopLossTarget.trade_type === 'BUY' ? -1 : 1)).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Reward (Target)</p>
                        <p className="font-bold text-green-600">
                          ₹{((modifyStopLossTarget.target_price - modifyStopLossTarget.entry_price) * modifyStopLossTarget.quantity * (modifyStopLossTarget.trade_type === 'BUY' ? 1 : -1)).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Ratio</p>
                        <p className="font-bold text-blue-600">
                          1:{((Math.abs(modifyStopLossTarget.target_price - modifyStopLossTarget.entry_price) / Math.abs(modifyStopLossTarget.stop_loss - modifyStopLossTarget.entry_price))).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      // TODO: Implement API call to update stop loss/target
                      alert('Stop Loss/Target modification feature coming soon! Backend API needs to be implemented.');
                      setModifyStopLossTarget(null);
                    }}
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                  >
                    Update Levels
                  </Button>
                  <Button onClick={() => setModifyStopLossTarget(null)} variant="outline" className="flex-1">
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
                        <th className="text-center">Strategy</th>
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
                          <td className="text-center">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium capitalize">
                              {trade.strategy_rationale?.split(' ')[0] || 'Manual'}
                            </span>
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

      {/* Risk Confirmation Dialog */}
      <Dialog open={showRiskDialog} onOpenChange={setShowRiskDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              Confirm High-Risk Trade
            </DialogTitle>
            <DialogDescription>
              This trade has been flagged as high-risk. Please review the details below and confirm if you want to proceed.
            </DialogDescription>
          </DialogHeader>

          {pendingTrade && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm font-medium">Symbol</p>
                  <p className="text-lg">{pendingTrade.symbol}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Type</p>
                  <p className={`text-lg font-bold ${pendingTrade.type === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                    {pendingTrade.type}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Quantity</p>
                  <p className="text-lg">{pendingTrade.quantity.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Price</p>
                  <p className="text-lg">₹{pendingTrade.entry_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Total Value</p>
                  <p className="text-lg font-bold">₹{(pendingTrade.quantity * pendingTrade.entry_price).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Risk Level</p>
                  <p className={`text-lg font-bold ${
                    pendingTrade.validation.riskLevel === 'high' ? 'text-red-600' :
                    pendingTrade.validation.riskLevel === 'medium' ? 'text-yellow-600' :
                    'text-green-600'
                  }`}>
                    {pendingTrade.validation.riskLevel.toUpperCase()}
                  </p>
                </div>
              </div>

              {pendingTrade.validation.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <p className="font-medium mb-2">Critical Issues:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {pendingTrade.validation.errors.map((error: string, index: number) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {pendingTrade.validation.warnings.length > 0 && (
                <Alert className="border-yellow-200 bg-yellow-50">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <AlertDescription>
                    <p className="font-medium mb-2 text-yellow-800">Warnings:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {pendingTrade.validation.warnings.map((warning: string, index: number) => (
                        <li key={index} className="text-yellow-800">{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              <Alert className="border-blue-200 bg-blue-50">
                <Shield className="h-4 w-4 text-blue-600" />
                <AlertDescription className="text-blue-800">
                  <strong>Risk Management Reminder:</strong> High-risk trades can significantly impact your portfolio.
                  Ensure you have a clear exit strategy and are comfortable with potential losses.
                </AlertDescription>
              </Alert>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRiskDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={confirmHighRiskTrade}
              disabled={executeBuyLoading || executeSellLoading}
              className="bg-red-600 hover:bg-red-700"
            >
              {executeBuyLoading || executeSellLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Executing...
                </>
              ) : (
                'Confirm High-Risk Trade'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default PaperTrading
