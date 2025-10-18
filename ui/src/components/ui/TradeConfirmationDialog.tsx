import { forwardRef, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/ui/RiskLevelBadge'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/format'
import type { TradeFormData } from '@/utils/validation'
import type { RiskLevel } from '@/types/domain'

export interface TradeConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  tradeData: TradeFormData
  onConfirm: () => void
  onCancel: () => void
  isExecuting?: boolean
  riskLevel?: RiskLevel
  riskWarnings?: string[]
}

export const TradeConfirmationDialog = forwardRef<HTMLDivElement, TradeConfirmationDialogProps>(
  ({
    open,
    onOpenChange,
    tradeData,
    onConfirm,
    onCancel,
    isExecuting = false,
    riskLevel = 'low',
    riskWarnings = [],
  }, ref) => {
    const [confirmed, setConfirmed] = useState(false)

    const totalValue = tradeData.price && tradeData.quantity
      ? tradeData.price * tradeData.quantity
      : tradeData.quantity || 0

    const handleConfirm = () => {
      if (!confirmed) {
        setConfirmed(true)
        return
      }
      onConfirm()
      setConfirmed(false)
    }

    const handleCancel = () => {
      setConfirmed(false)
      onCancel()
    }

    const getRiskBadgeVariant = (level: string) => {
      switch (level) {
        case 'high': return 'destructive'
        case 'medium': return 'secondary'
        default: return 'default'
      }
    }

    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent ref={ref} className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Confirm Trade Execution
              <RiskLevelBadge level={riskLevel} />
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Trade Summary */}
            <div className="bg-warmgray-50 rounded-lg p-4 space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-warmgray-600">Symbol:</span>
                  <div className="font-semibold text-lg">{tradeData.symbol}</div>
                </div>
                <div>
                  <span className="text-warmgray-600">Side:</span>
                  <div className={cn(
                    "font-semibold",
                    tradeData.side === 'BUY' ? "text-emerald-600" : "text-rose-600"
                  )}>
                    {tradeData.side}
                  </div>
                </div>
                <div>
                  <span className="text-warmgray-600">Quantity:</span>
                  <div className="font-semibold">{tradeData.quantity?.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-warmgray-600">Order Type:</span>
                  <div className="font-semibold">{tradeData.order_type}</div>
                </div>
                {tradeData.price && (
                  <>
                    <div>
                      <span className="text-warmgray-600">Price:</span>
                      <div className="font-semibold">{formatCurrency(tradeData.price)}</div>
                    </div>
                    <div>
                      <span className="text-warmgray-600">Total Value:</span>
                      <div className="font-semibold">{formatCurrency(totalValue)}</div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Risk Warnings */}
            {riskWarnings.length > 0 && (
              <div className="bg-copper-50 border border-copper-200 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <svg className="w-5 h-5 text-copper-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <div className="space-y-1">
                    <div className="font-medium text-copper-800">Risk Warnings</div>
                    <ul className="text-sm text-copper-700 space-y-1">
                      {riskWarnings.map((warning, index) => (
                        <li key={index} className="flex items-start gap-1">
                          <span>•</span>
                          <span>{warning}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Confirmation Checkbox for High Risk */}
            {riskLevel === 'high' && (
              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="confirm-high-risk"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  className="mt-1"
                />
                <label htmlFor="confirm-high-risk" className="text-sm text-warmgray-700">
                  I acknowledge the high risk associated with this trade and confirm execution
                </label>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isExecuting}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                variant={riskLevel === 'high' ? 'danger' : 'primary'}
                onClick={handleConfirm}
                disabled={isExecuting || (riskLevel === 'high' && !confirmed)}
                className="flex-1"
              >
                {isExecuting ? 'Executing...' : confirmed ? 'Confirm Trade' : 'Review & Confirm'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }
)

TradeConfirmationDialog.displayName = 'TradeConfirmationDialog'