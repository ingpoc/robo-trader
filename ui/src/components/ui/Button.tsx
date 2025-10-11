import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/format'

const buttonVariants = cva(
  'inline-flex items-center justify-center font-medium transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]',
  {
    variants: {
      variant: {
        primary: 'bg-gray-900 text-white border border-gray-900 hover:bg-gray-800',
        secondary: 'bg-white text-gray-900 border border-gray-300 hover:border-gray-400',
        outline: 'bg-transparent text-gray-900 border border-gray-300 hover:bg-gray-50',
        ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 active:bg-gray-200',
      },
      size: {
        sm: 'h-8 px-3 text-13',
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
