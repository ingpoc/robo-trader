import { forwardRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'

export interface ConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'danger'
  onConfirm: () => void
  onCancel?: () => void
  isLoading?: boolean
  children?: React.ReactNode
}

export const ConfirmationDialog = forwardRef<HTMLDivElement, ConfirmationDialogProps>(
  ({
    open,
    onOpenChange,
    title,
    description,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'default',
    onConfirm,
    onCancel,
    isLoading = false,
    children,
  }, ref) => {
    const handleConfirm = () => {
      onConfirm()
    }

    const handleCancel = () => {
      onCancel?.()
      onOpenChange(false)
    }

    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent ref={ref} className="max-w-md">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {description && (
              <p className="text-sm text-warmgray-600 leading-relaxed">
                {description}
              </p>
            )}

            {children}

            <div className="flex gap-3 pt-4">
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isLoading}
                className="flex-1"
              >
                {cancelText}
              </Button>
              <Button
                variant={variant === 'danger' ? 'danger' : 'primary'}
                onClick={handleConfirm}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? 'Processing...' : confirmText}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }
)

ConfirmationDialog.displayName = 'ConfirmationDialog'