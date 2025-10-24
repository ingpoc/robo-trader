/**
 * Position Modifier Dialog Component
 * Modal for modifying stop loss and target prices on active positions
 */

import React, { useState, useMemo } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { AlertTriangle } from 'lucide-react'
import type { OpenPositionResponse } from '../types'

export interface PositionModifierDialogProps {
  isOpen: boolean
  position: OpenPositionResponse | null
  onClose: () => void
  onConfirm: (stopLoss?: number, target?: number) => Promise<void>
  isLoading?: boolean
}

export const PositionModifierDialog: React.FC<PositionModifierDialogProps> = ({
  isOpen,
  position,
  onClose,
  onConfirm,
  isLoading = false
}) => {
  const [stopLoss, setStopLoss] = useState<string>('')
  const [target, setTarget] = useState<string>('')
  const [errors, setErrors] = useState<string[]>([])

  const validation = useMemo(() => {
    const newErrors: string[] = []

    if (stopLoss && target) {
      const slPrice = parseFloat(stopLoss)
      const tgtPrice = parseFloat(target)

      if (isNaN(slPrice) || isNaN(tgtPrice)) {
        newErrors.push('Invalid prices')
        return { isValid: false, errors: newErrors, riskRewardRatio: 0 }
      }

      if (slPrice >= position!.entry_price) {
        newErrors.push('Stop loss must be below entry price for long positions')
      }

      if (tgtPrice <= position!.entry_price) {
        newErrors.push('Target must be above entry price for long positions')
      }

      if (slPrice >= tgtPrice) {
        newErrors.push('Stop loss must be below target')
      }

      const risk = position!.entry_price - slPrice
      const reward = tgtPrice - position!.entry_price
      const riskRewardRatio = reward / risk

      return { isValid: newErrors.length === 0, errors: newErrors, riskRewardRatio }
    }

    return { isValid: true, errors: newErrors, riskRewardRatio: 0 }
  }, [stopLoss, target, position])

  const handleConfirm = async () => {
    if (!validation.isValid) return

    const finalStopLoss = stopLoss ? parseFloat(stopLoss) : position?.stop_loss
    const finalTarget = target ? parseFloat(target) : position?.target

    try {
      await onConfirm(finalStopLoss, finalTarget)
      setStopLoss('')
      setTarget('')
      setErrors([])
      onClose()
    } catch (err) {
      setErrors([err instanceof Error ? err.message : 'Failed to modify position'])
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setStopLoss('')
      setTarget('')
      setErrors([])
      onClose()
    }
  }

  if (!position) return null

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Modify Levels - {position.symbol}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Position Details */}
          <div className="bg-muted p-3 rounded-lg space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Entry Price:</span>
              <span className="font-medium">₹{position.entry_price.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Current Price:</span>
              <span className="font-medium">₹{position.current_price.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Quantity:</span>
              <span className="font-medium">{position.quantity} shares</span>
            </div>
          </div>

          {/* Stop Loss Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Stop Loss (₹) {position.stop_loss && `- Current: ₹${position.stop_loss.toFixed(2)}`}</label>
            <Input
              type="number"
              placeholder={position.stop_loss ? `Current: ₹${position.stop_loss.toFixed(2)}` : 'Enter stop loss price'}
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              step="0.01"
              min="0"
              disabled={isLoading}
            />
          </div>

          {/* Target Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Target (₹) {position.target && `- Current: ₹${position.target.toFixed(2)}`}</label>
            <Input
              type="number"
              placeholder={position.target ? `Current: ₹${position.target.toFixed(2)}` : 'Enter target price'}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              step="0.01"
              min="0"
              disabled={isLoading}
            />
          </div>

          {/* Risk/Reward Ratio */}
          {validation.riskRewardRatio > 0 && (
            <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Risk:Reward Ratio:</span>
                <span className="font-semibold text-blue-600">
                  1:{validation.riskRewardRatio.toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {/* Validation Errors */}
          {(errors.length > 0 || validation.errors.length > 0) && (
            <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg space-y-2">
              {[...errors, ...validation.errors].map((error, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-red-600">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isLoading || !validation.isValid}
          >
            {isLoading ? 'Updating...' : 'Update Levels'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default PositionModifierDialog
