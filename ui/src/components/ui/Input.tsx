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
              'h-10 w-full rounded-lg border border-input bg-card px-4 pr-10 text-sm text-foreground transition-all duration-200 placeholder:text-muted-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              'disabled:cursor-not-allowed disabled:bg-muted/60 disabled:text-muted-foreground',
              error ? 'border-rose-500 focus-visible:ring-rose-300' :
              success ? 'border-emerald-500 focus-visible:ring-emerald-300' :
              isFocused ? 'border-primary shadow-sm shadow-copper-100' :
              'hover:border-border/90',
              className
            )}
            onFocus={handleFocus}
            onBlur={handleBlur}
            {...props}
          />
          {showValidation && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              {showError && (
                <AlertCircle className="w-5 h-5 text-rose-500" />
              )}
              {showSuccess && (
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              )}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-2 flex items-center gap-1 text-sm text-rose-600" role="alert">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </p>
        )}
        {success && !error && (
          <p className="mt-2 flex items-center gap-1 text-sm text-emerald-600">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Looks good!
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
