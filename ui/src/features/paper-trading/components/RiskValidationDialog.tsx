/**
 * Risk Validation Dialog Component
 * Pre-trade confirmation dialog for high-risk trades
 */

import React from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react'
import type { TradeValidationResult } from '../types'

export interface RiskValidationDialogProps {
  isOpen: boolean
  tradeData: {
    symbol: string
    type: 'BUY' | 'SELL'
    quantity: number
    entryPrice: number
    stopLoss?: number
    target?: number
    totalValue: number
  } | null
  validationResult: TradeValidationResult | null
  onClose: () => void
  onConfirm: () => Promise<void>
  isLoading?: boolean
}

export const RiskValidationDialog: React.FC<RiskValidationDialogProps> = ({
  isOpen,
  tradeData,
  validationResult,
  onClose,
  onConfirm,
  isLoading = false
}) => {
  if (!tradeData || !validationResult) return null

  const getRiskBadgeColor = () => {
    switch (validationResult.riskLevel) {
      case 'high':
        return 'bg-red-100 dark:bg-red-900 text-red-800'
      case 'medium':
        return 'bg-amber-100 dark:bg-amber-900 text-amber-800'
      default:
        return 'bg-green-100 dark:bg-green-900 text-green-800'
    }
  }

  const getButtonVariant = () => {
    if (validationResult.errors.length > 0) return 'secondary'
    if (validationResult.riskLevel === 'high') return 'destructive'
    return 'default'
  }

  const riskRewardRatio = tradeData.stopLoss && tradeData.target
    ? ((tradeData.target - tradeData.entryPrice) / (tradeData.entryPrice - tradeData.stopLoss)).toFixed(2)
    : null

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            Confirm Trade Execution
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Risk Level Badge */}
          <div className={`p-4 rounded-lg ${getRiskBadgeColor()}`}>
            <div className="flex items-center justify-between">
              <span className="font-semibold uppercase text-sm">
                {validationResult.riskLevel} RISK
              </span>
              <span className="text-xs font-medium">
                {validationResult.riskLevel === 'high' ? '⚠️ Requires Confirmation' : '✓ Acceptable'}
              </span>
            </div>
          </div>

          {/* Trade Summary */}
          <div className="bg-muted p-4 rounded-lg space-y-3">
            <h3 className="font-semibold text-sm">Trade Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Symbol:</span>
                <span className="font-medium">{tradeData.symbol}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type:</span>
                <span className={`font-medium ${tradeData.type === 'BUY' ? 'text-emerald-600' : 'text-red-600'}`}>
                  {tradeData.type}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Quantity:</span>
                <span className="font-medium">{tradeData.quantity} shares</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Entry Price:</span>
                <span className="font-medium">₹{tradeData.entryPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Value:</span>
                <span className="font-medium">₹{tradeData.totalValue.toLocaleString('en-IN')}</span>
              </div>
              {tradeData.stopLoss && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Stop Loss:</span>
                  <span className="font-medium text-red-600">₹{tradeData.stopLoss.toFixed(2)}</span>
                </div>
              )}
              {tradeData.target && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Target:</span>
                  <span className="font-medium text-emerald-600">₹{tradeData.target.toFixed(2)}</span>
                </div>
              )}
              {riskRewardRatio && (
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-muted-foreground">Risk:Reward Ratio:</span>
                  <span className="font-medium">1:{riskRewardRatio}</span>
                </div>
              )}
            </div>
          </div>

          {/* Validation Errors */}
          {validationResult.errors.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-red-600">Errors</h3>
              <div className="space-y-1">
                {validationResult.errors.map((error, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm p-2 bg-red-50 dark:bg-red-950 rounded">
                    <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <span className="text-red-600">{error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Validation Warnings */}
          {validationResult.warnings.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-amber-600">Warnings</h3>
              <div className="space-y-1">
                {validationResult.warnings.map((warning, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm p-2 bg-amber-50 dark:bg-amber-950 rounded">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <span className="text-amber-600">{warning}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Success Message */}
          {validationResult.errors.length === 0 && validationResult.riskLevel === 'low' && (
            <div className="flex items-start gap-2 p-3 bg-green-50 dark:bg-green-950 rounded">
              <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-green-600">All validations passed. Trade is ready to execute.</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="tertiary"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isLoading || validationResult.errors.length > 0}
            variant={getButtonVariant()}
            className={validationResult.riskLevel === 'high' ? 'bg-red-600 hover:bg-red-700' : ''}
          >
            {isLoading ? 'Executing...' : 'Execute Trade'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default RiskValidationDialog
