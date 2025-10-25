/**
 * Close Position Dialog Component
 * Modal for closing an open position with exit price input
 */

import React, { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import type { OpenPositionResponse } from '../types'

export interface ClosePositionDialogProps {
  isOpen: boolean
  position: OpenPositionResponse | null
  onClose: () => void
  onConfirm: (exitPrice: number) => Promise<void>
  isLoading?: boolean
}

export const ClosePositionDialog: React.FC<ClosePositionDialogProps> = ({
  isOpen,
  position,
  onClose,
  onConfirm,
  isLoading = false
}) => {
  const [exitPrice, setExitPrice] = useState<string>('')
  const [error, setError] = useState<string>('')

  const handleConfirm = async () => {
    if (!position || !exitPrice) {
      setError('Exit price is required')
      return
    }

    const price = parseFloat(exitPrice)
    if (isNaN(price) || price <= 0) {
      setError('Invalid exit price')
      return
    }

    try {
      await onConfirm(price)
      setExitPrice('')
      setError('')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close position')
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setExitPrice('')
      setError('')
      onClose()
    }
  }

  if (!position) return null

  const pnl = (parseFloat(exitPrice) - position.entry_price) * position.quantity
  const pnlPct = ((pnl / (position.entry_price * position.quantity)) * 100).toFixed(2)

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Close Position - {position.symbol}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Position Details */}
          <div className="bg-muted p-3 rounded-lg space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Quantity:</span>
              <span className="font-medium">{position.quantity} shares</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Entry Price:</span>
              <span className="font-medium">₹{position.entry_price.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Current Price:</span>
              <span className="font-medium">₹{position.current_price.toFixed(2)}</span>
            </div>
          </div>

          {/* Exit Price Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Exit Price (₹)</label>
            <Input
              type="number"
              placeholder="Enter exit price"
              value={exitPrice}
              onChange={(e) => {
                setExitPrice(e.target.value)
                setError('')
              }}
              step="0.01"
              min="0"
              disabled={isLoading}
            />
          </div>

          {/* P&L Preview */}
          {exitPrice && (
            <div className={`p-3 rounded-lg ${pnl >= 0 ? 'bg-emerald-50 dark:bg-emerald-950' : 'bg-red-50 dark:bg-red-950'}`}>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-muted-foreground">P&L:</span>
                <span className={`font-semibold ${pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {pnl >= 0 ? '+' : ''}₹{Math.abs(pnl).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Return:</span>
                <span className={`font-semibold ${pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {pnl >= 0 ? '+' : ''}{pnlPct}%
                </span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950 text-red-600 text-sm rounded-lg">
              {error}
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
            disabled={isLoading || !exitPrice || !!error}
            className="bg-red-600 hover:bg-red-700"
          >
            {isLoading ? 'Closing...' : 'Close Position'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ClosePositionDialog
