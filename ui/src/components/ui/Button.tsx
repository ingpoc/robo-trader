import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/format'

const buttonVariants = cva(
  'inline-flex items-center justify-center font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus-ring rounded-md',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-white border border-accent hover:bg-accent-dark hover:shadow-lg hover:shadow-accent/25',
        secondary: 'bg-white text-gray-900 border border-gray-300 hover:border-accent hover:bg-gray-50 hover:shadow-md',
        outline: 'bg-transparent text-accent border border-accent hover:bg-accent hover:text-white hover:shadow-md',
        ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 hover:text-accent active:bg-gray-200',
        success: 'bg-success text-white border border-success hover:bg-success-dark hover:shadow-lg hover:shadow-success/25',
        danger: 'bg-error text-white border border-error hover:bg-error-dark hover:shadow-lg hover:shadow-error/25',
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
