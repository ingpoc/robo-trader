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
              'w-full h-10 px-3 pr-10 text-base bg-white/70 border rounded-lg transition-all duration-200',
              'placeholder:text-warmgray-400',
              'focus:outline-none focus:ring-2 focus:ring-offset-2',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              error ? 'border-rose-500 focus:ring-rose-500' :
              success ? 'border-emerald-500 focus:ring-emerald-500' :
              isFocused ? 'border-copper-500 focus:ring-copper-500' : 'border-warmgray-300',
              className
            )}
            onFocus={handleFocus}
            onBlur={handleBlur}
            {...props}
          />
          {showValidation && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              {showError && (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
              {showSuccess && (
                <CheckCircle className="w-5 h-5 text-green-500" />
              )}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1 text-sm text-rose-600 flex items-center gap-1" role="alert">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </p>
        )}
        {success && !error && (
          <p className="mt-1 text-sm text-emerald-600 flex items-center gap-1">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Looks good!
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
