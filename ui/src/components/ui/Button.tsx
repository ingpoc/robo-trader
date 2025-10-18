import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus-ring rounded-lg',
  {
    variants: {
      variant: {
        primary: 'bg-copper-500 text-white border border-copper-500 hover:bg-copper-600 hover:shadow-md hover:shadow-copper/25 hover:translate-y-[-1px]',
        secondary: 'bg-white/70 text-warmgray-900 border border-warmgray-300 hover:border-copper-500 hover:bg-white hover:shadow-md hover:text-copper-500',
        outline: 'bg-transparent text-copper-500 border border-copper-500 hover:bg-copper-500 hover:text-white hover:shadow-md',
        ghost: 'bg-transparent text-warmgray-700 hover:bg-warmgray-100 hover:text-copper-500 active:bg-warmgray-200',
        success: 'bg-emerald-600 text-white border border-emerald-600 hover:bg-emerald-700 hover:shadow-md hover:shadow-emerald/25 hover:translate-y-[-1px]',
        danger: 'bg-rose-600 text-white border border-rose-600 hover:bg-rose-700 hover:shadow-md hover:shadow-rose/25 hover:translate-y-[-1px]',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, children, disabled, ...props }, ref) => {
    const isLoading = disabled && typeof children === 'string' && (children.toLowerCase().includes('...') || children.toLowerCase().includes('loading'))

    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'
