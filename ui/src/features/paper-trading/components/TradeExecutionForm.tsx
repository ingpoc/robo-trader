/**
 * Trade Execution Form Component
 * Complete form for executing new buy/sell trades
 */

import React, { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react'
import { useTradeValidation } from '../hooks/useTradeValidation'
import type { TradeFormData, TradeValidationResult } from '../types'
import type { AccountOverviewResponse, OpenPositionResponse } from '../types'

const STRATEGIES = [
  'Momentum',
  'Breakout',
  'Reversal',
  'Swing',
  'Scalping',
  'News-Based',
  'Technical',
  'Fundamental'
]

export interface TradeExecutionFormProps {
  accountOverview: AccountOverviewResponse | null
  positions: OpenPositionResponse[]
  onSubmit: (data: TradeFormData, validation: TradeValidationResult) => Promise<void>
  isLoading?: boolean
}

export const TradeExecutionForm: React.FC<TradeExecutionFormProps> = ({
  accountOverview,
  positions,
  onSubmit,
  isLoading = false
}) => {
  const [tradeType, setTradeType] = useState<'BUY' | 'SELL'>('BUY')
  const [formData, setFormData] = useState<TradeFormData>({
    symbol: '',
    quantity: 0,
    entryPrice: 0,
    stopLoss: undefined,
    target: undefined,
    strategy: 'Technical',
    type: 'BUY'
  })
  const [rationale, setRationale] = useState('')
  const [error, setError] = useState<string>('')

  const validation = useTradeValidation(
    { ...formData, type: tradeType },
    accountOverview,
    positions
  )

  const totalValue = useMemo(() => {
    return formData.quantity * formData.entryPrice
  }, [formData.quantity, formData.entryPrice])

  const riskRewardRatio = useMemo(() => {
    if (!formData.stopLoss || !formData.target) return null
    const risk = Math.abs(formData.entryPrice - formData.stopLoss)
    const reward = Math.abs(formData.target - formData.entryPrice)
    return (reward / risk).toFixed(2)
  }, [formData.entryPrice, formData.stopLoss, formData.target])

  const handleTypeChange = (type: 'BUY' | 'SELL') => {
    setTradeType(type)
    setFormData(prev => ({ ...prev, type }))
    setError('')
  }

  const handleInputChange = (field: keyof TradeFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const handleSubmit = async () => {
    if (!validation.isValid) {
      setError('Please fix validation errors before submitting')
      return
    }

    if (!formData.symbol) {
      setError('Symbol is required')
      return
    }

    try {
      await onSubmit({ ...formData, type: tradeType }, validation)
      setFormData({
        symbol: '',
        quantity: 0,
        entryPrice: 0,
        stopLoss: undefined,
        target: undefined,
        strategy: 'Technical',
        type: 'BUY'
      })
      setRationale('')
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trade execution failed')
    }
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">Execute Trade</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trade Type Toggle */}
        <div className="flex gap-2">
          <Button
            variant={tradeType === 'BUY' ? 'default' : 'outline'}
            onClick={() => handleTypeChange('BUY')}
            className={tradeType === 'BUY' ? 'bg-emerald-600 hover:bg-emerald-700 w-full' : 'w-full'}
            disabled={isLoading}
          >
            BUY
          </Button>
          <Button
            variant={tradeType === 'SELL' ? 'default' : 'outline'}
            onClick={() => handleTypeChange('SELL')}
            className={tradeType === 'SELL' ? 'bg-red-600 hover:bg-red-700 w-full' : 'w-full'}
            disabled={isLoading}
          >
            SELL
          </Button>
        </div>

        {/* Symbol Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Symbol</label>
          <Input
            placeholder="e.g., INFY, TCS"
            value={formData.symbol}
            onChange={(e) => handleInputChange('symbol', e.target.value.toUpperCase())}
            disabled={isLoading}
          />
        </div>

        {/* Quantity Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Quantity</label>
          <Input
            type="number"
            placeholder="Number of shares"
            value={formData.quantity || ''}
            onChange={(e) => handleInputChange('quantity', parseInt(e.target.value) || 0)}
            min="1"
            disabled={isLoading}
          />
        </div>

        {/* Entry Price Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Entry Price (₹)</label>
          <Input
            type="number"
            placeholder="Entry price"
            value={formData.entryPrice || ''}
            onChange={(e) => handleInputChange('entryPrice', parseFloat(e.target.value) || 0)}
            step="0.01"
            min="0"
            disabled={isLoading}
          />
        </div>

        {/* Stop Loss Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Stop Loss (₹) - Optional</label>
          <Input
            type="number"
            placeholder="Stop loss price"
            value={formData.stopLoss || ''}
            onChange={(e) => handleInputChange('stopLoss', e.target.value ? parseFloat(e.target.value) : undefined)}
            step="0.01"
            min="0"
            disabled={isLoading}
          />
        </div>

        {/* Target Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Target (₹) - Optional</label>
          <Input
            type="number"
            placeholder="Target price"
            value={formData.target || ''}
            onChange={(e) => handleInputChange('target', e.target.value ? parseFloat(e.target.value) : undefined)}
            step="0.01"
            min="0"
            disabled={isLoading}
          />
        </div>

        {/* Strategy Dropdown */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Strategy</label>
          <select
            value={formData.strategy}
            onChange={(e) => handleInputChange('strategy', e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm"
          >
            {STRATEGIES.map(strategy => (
              <option key={strategy} value={strategy}>{strategy}</option>
            ))}
          </select>
        </div>

        {/* Rationale Textarea */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Rationale - Optional</label>
          <textarea
            placeholder="Why are you taking this trade?"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm resize-none"
            rows={3}
          />
        </div>

        {/* Trade Summary */}
        {totalValue > 0 && (
          <div className="bg-muted p-3 rounded-lg space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Total Value:</span>
              <span className="font-semibold">₹{totalValue.toLocaleString('en-IN')}</span>
            </div>
            {riskRewardRatio && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Risk:Reward:</span>
                <span className="font-semibold">1:{riskRewardRatio}</span>
              </div>
            )}
          </div>
        )}

        {/* Risk Level Badge */}
        {validation.isValid && (
          <div className={`p-2 rounded-lg text-sm ${
            validation.riskLevel === 'high' ? 'bg-red-50 dark:bg-red-950 text-red-600' :
            validation.riskLevel === 'medium' ? 'bg-amber-50 dark:bg-amber-950 text-amber-600' :
            'bg-green-50 dark:bg-green-950 text-green-600'
          }`}>
            <span className="font-semibold">{validation.riskLevel.toUpperCase()} RISK</span>
          </div>
        )}

        {/* Validation Errors */}
        {validation.errors.length > 0 && (
          <div className="space-y-2">
            {validation.errors.map((err, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm p-2 bg-red-50 dark:bg-red-950 rounded">
                <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                <span className="text-red-600">{err}</span>
              </div>
            ))}
          </div>
        )}

        {/* Validation Warnings */}
        {validation.warnings.length > 0 && (
          <div className="space-y-2">
            {validation.warnings.map((warn, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm p-2 bg-amber-50 dark:bg-amber-950 rounded">
                <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <span className="text-amber-600">{warn}</span>
              </div>
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="flex items-start gap-2 text-sm p-2 bg-red-50 dark:bg-red-950 rounded">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            <span className="text-red-600">{error}</span>
          </div>
        )}

        {/* Success Message */}
        {validation.errors.length === 0 && validation.riskLevel === 'low' && (
          <div className="flex items-start gap-2 text-sm p-2 bg-green-50 dark:bg-green-950 rounded">
            <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-green-600">Form is ready to submit</span>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={isLoading || !validation.isValid || !formData.symbol}
          className="w-full"
          variant={validation.riskLevel === 'high' ? 'destructive' : 'default'}
        >
          {isLoading ? 'Executing...' : 'Execute Trade'}
        </Button>
      </CardContent>
    </Card>
  )
}

export default TradeExecutionForm
