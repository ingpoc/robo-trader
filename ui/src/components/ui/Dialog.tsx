import { forwardRef, DialogHTMLAttributes, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/utils/cn'
import { X } from 'lucide-react'

export interface DialogProps extends DialogHTMLAttributes<HTMLDialogElement> {
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export const Dialog = forwardRef<HTMLDialogElement, DialogProps>(
  ({ className, open, onOpenChange, children, ...props }, ref) => {
    const internalRef = useRef<HTMLDialogElement>(null)
    const dialogRef = (ref as any) || internalRef

    useEffect(() => {
      const dialog = dialogRef.current
      if (dialog) {
        if (open) {
          dialog.showModal()
          document.body.style.overflow = 'hidden'
        } else {
          dialog.close()
          document.body.style.overflow = 'unset'
        }
      }

      return () => {
        document.body.style.overflow = 'unset'
      }
    }, [open, dialogRef])

    const handleBackdropClick = useCallback((e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onOpenChange?.(false)
      }
    }, [onOpenChange])

    return (
      <dialog
        ref={dialogRef}
        className={cn(
          'fixed inset-0 z-50 w-full max-w-lg mx-auto rounded-xl',
          'bg-white dark:bg-warmgray-800',
          'border border-warmgray-300 dark:border-warmgray-700',
          'shadow-2xl backdrop-blur-md',
          'animate-in fade-in zoom-in-95 duration-200',
          'open:animate-in open:fade-in open:zoom-in-95',
          '::backdrop:bg-black/40',
          className
        )}
        onClick={handleBackdropClick}
        {...props}
      >
        {children}
      </dialog>
    )
  }
)

Dialog.displayName = 'Dialog'

export interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  onClose?: () => void
  showCloseButton?: boolean
}

export const DialogContent = forwardRef<HTMLDivElement, DialogContentProps>(
  ({ className, children, onClose, showCloseButton = true, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative max-h-[90vh] overflow-y-auto w-full p-6',
          'text-warmgray-900 dark:text-warmgray-100',
          className
        )}
        {...props}
      >
        {showCloseButton && onClose && (
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-lg p-2 text-warmgray-500 dark:text-warmgray-400 hover:bg-warmgray-100 dark:hover:bg-warmgray-700 hover:text-warmgray-900 dark:hover:text-warmgray-100 transition-all duration-200"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        )}
        {children}
      </div>
    )
  }
)

DialogContent.displayName = 'DialogContent'

export interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const DialogHeader = forwardRef<HTMLDivElement, DialogHeaderProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex flex-col space-y-2 border-b border-warmgray-200 dark:border-warmgray-700 pb-4 mb-4',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

DialogHeader.displayName = 'DialogHeader'

export interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

export const DialogTitle = forwardRef<HTMLHeadingElement, DialogTitleProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <h2
        ref={ref}
        className={cn(
          'text-2xl font-bold leading-none tracking-tight font-serif text-warmgray-900 dark:text-warmgray-100',
          className
        )}
        {...props}
      >
        {children}
      </h2>
    )
  }
)

DialogTitle.displayName = 'DialogTitle'

export interface DialogDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

export const DialogDescription = forwardRef<HTMLParagraphElement, DialogDescriptionProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn(
          'text-sm text-warmgray-600 dark:text-warmgray-400 mt-2',
          className
        )}
        {...props}
      >
        {children}
      </p>
    )
  }
)

DialogDescription.displayName = 'DialogDescription'

export interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const DialogFooter = forwardRef<HTMLDivElement, DialogFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-end gap-3 border-t border-warmgray-200 dark:border-warmgray-700 pt-4 mt-6',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

DialogFooter.displayName = 'DialogFooter'
