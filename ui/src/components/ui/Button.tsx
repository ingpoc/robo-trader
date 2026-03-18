import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-lg border text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
  {
    variants: {
      variant: {
        default: 'border-primary bg-primary text-primary-foreground shadow-sm hover:border-primary/90 hover:bg-primary/90',
        primary: 'bg-copper-500 text-white border border-copper-500 dark:bg-copper-600 dark:border-copper-600 hover:bg-copper-600 dark:hover:bg-copper-700 hover:shadow-lg hover:shadow-copper-500/25 hover:-translate-y-0.5 focus:ring-copper-400 dark:focus:ring-copper-500 active:scale-95 active:translate-y-0',
        outline: 'border-border bg-card text-foreground shadow-sm hover:bg-muted hover:text-foreground',
        secondary: 'bg-white/80 dark:bg-warmgray-800/80 text-warmgray-900 dark:text-warmgray-100 border border-warmgray-300 dark:border-warmgray-600 hover:border-copper-400 dark:hover:border-copper-500 hover:bg-warmgray-50 dark:hover:bg-warmgray-700/50 hover:text-copper-500 dark:hover:text-copper-400 hover:shadow-md focus:ring-copper-400 dark:focus:ring-copper-500',
        destructive: 'border-destructive bg-destructive text-destructive-foreground shadow-sm hover:border-destructive/90 hover:bg-destructive/90',
        tertiary: 'bg-transparent text-copper-600 dark:text-copper-400 border-2 border-copper-300 dark:border-copper-600 hover:bg-copper-50 dark:hover:bg-copper-950 hover:border-copper-500 dark:hover:border-copper-400 hover:shadow-md focus:ring-copper-400 dark:focus:ring-copper-500',
        link: 'border-transparent bg-transparent px-0 text-primary shadow-none hover:text-primary/80 hover:underline',
        ghost: 'bg-transparent text-warmgray-700 dark:text-warmgray-300 hover:bg-warmgray-100 dark:hover:bg-warmgray-800 hover:text-copper-500 dark:hover:text-copper-400 active:bg-warmgray-200 dark:active:bg-warmgray-700 focus:ring-copper-400 dark:focus:ring-copper-500',
        success: 'bg-emerald-600 text-white border border-emerald-600 dark:bg-emerald-700 dark:border-emerald-700 hover:bg-emerald-700 dark:hover:bg-emerald-800 hover:shadow-lg hover:shadow-emerald-500/25 hover:-translate-y-0.5 focus:ring-emerald-400 dark:focus:ring-emerald-500 active:scale-95 active:translate-y-0',
        danger: 'bg-rose-600 text-white border border-rose-600 dark:bg-rose-700 dark:border-rose-700 hover:bg-rose-700 dark:hover:bg-rose-800 hover:shadow-lg hover:shadow-rose-500/25 hover:-translate-y-0.5 focus:ring-rose-400 dark:focus:ring-rose-500 active:scale-95 active:translate-y-0',
        warning: 'bg-amber-600 text-white border border-amber-600 dark:bg-amber-700 dark:border-amber-700 hover:bg-amber-700 dark:hover:bg-amber-800 hover:shadow-lg hover:shadow-amber-500/25 hover:-translate-y-0.5 focus:ring-amber-400 dark:focus:ring-amber-500 active:scale-95 active:translate-y-0',
      },
      size: {
        xs: 'h-8 px-2.5 text-xs gap-1',
        sm: 'h-9 px-3 text-xs gap-1.5',
        md: 'h-10 px-4 text-sm gap-2',
        lg: 'h-12 px-6 text-base gap-2.5',
        xl: 'h-14 px-8 text-lg gap-3',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, children, disabled, isLoading, ...props }, ref) => {
    const showLoading = isLoading || (disabled && typeof children === 'string' && (children.toLowerCase().includes('...') || children.toLowerCase().includes('loading')))

    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || showLoading}
        {...props}
      >
        {showLoading && (
          <svg 
            className="animate-spin -ml-1 mr-2 h-4 w-4" 
            viewBox="0 0 24 24" 
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path 
              className="opacity-75" 
              fill="currentColor" 
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" 
            />
          </svg>
        )}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'
