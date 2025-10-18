import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import { CheckCircle, AlertCircle } from 'lucide-react'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string
  success?: boolean
  showValidation?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, success, showValidation, onBlur, onFocus, ...props }, ref) => {
    const [isFocused, setIsFocused] = useState(false)

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true)
      onFocus?.(e)
    }

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false)
      onBlur?.(e)
    }

    const showSuccess = success && !error && showValidation
    const showError = error && showValidation

    return (
      <div className="w-full">
        <div className="relative">
          <input
            ref={ref}
            className={cn(
              // Base styling with luxury theme
              'w-full h-10 px-4 pr-10 text-base',
              'bg-white dark:bg-warmgray-800',
              'border border-warmgray-300 dark:border-warmgray-700',
              'rounded-lg transition-all duration-200',
              'text-warmgray-900 dark:text-warmgray-100',
              'placeholder:text-warmgray-400 dark:placeholder:text-warmgray-500',
              
              // Focus styling with copper accent
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-warmgray-900',
              
              // Disabled state
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-warmgray-100 dark:disabled:bg-warmgray-700',
              
              // Error state
              error ? 'border-rose-500 dark:border-rose-600 focus:ring-rose-400' :
              // Success state
              success ? 'border-emerald-500 dark:border-emerald-600 focus:ring-emerald-400' :
              // Focused state with copper
              isFocused ? 'border-copper-500 dark:border-copper-400 focus:ring-copper-400 shadow-sm shadow-copper-100 dark:shadow-copper-950' :
              // Default state
              'focus:ring-copper-400',
              
              className
            )}
            onFocus={handleFocus}
            onBlur={handleBlur}
            {...props}
          />
          {showValidation && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              {showError && (
                <AlertCircle className="w-5 h-5 text-rose-500 dark:text-rose-400" />
              )}
              {showSuccess && (
                <CheckCircle className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
              )}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-2 text-sm text-rose-600 dark:text-rose-400 flex items-center gap-1" role="alert">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </p>
        )}
        {success && !error && (
          <p className="mt-2 text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Looks good!
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
