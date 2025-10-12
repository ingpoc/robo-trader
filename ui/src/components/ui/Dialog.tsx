import { forwardRef, DialogHTMLAttributes, useEffect } from 'react'
import { cn } from '@/utils/cn'

export interface DialogProps extends DialogHTMLAttributes<HTMLDialogElement> {
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export const Dialog = forwardRef<HTMLDialogElement, DialogProps>(
  ({ className, open, onOpenChange, children, ...props }, ref) => {
    useEffect(() => {
      if (open) {
        document.body.style.overflow = 'hidden'
      } else {
        document.body.style.overflow = 'unset'
      }

      return () => {
        document.body.style.overflow = 'unset'
      }
    }, [open])

    return (
      <dialog
        ref={ref}
        className={cn(
          'fixed inset-0 z-50 flex items-center justify-center',
          'bg-black/50 backdrop-blur-sm',
          'animate-in fade-in duration-200',
          open ? 'block' : 'hidden',
          className
        )}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            onOpenChange?.(false)
          }
        }}
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
}

export const DialogContent = forwardRef<HTMLDivElement, DialogContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative max-h-[90vh] w-full max-w-lg rounded-lg bg-white p-6 shadow-lg',
          'animate-in zoom-in-95 duration-200',
          'focus:outline-none',
          className
        )}
        {...props}
      >
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
        className={cn('flex flex-col space-y-1.5 text-center sm:text-left', className)}
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
        className={cn('text-lg font-semibold leading-none tracking-tight', className)}
        {...props}
      >
        {children}
      </h2>
    )
  }
)

DialogTitle.displayName = 'DialogTitle'