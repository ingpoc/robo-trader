import { forwardRef, SelectHTMLAttributes, useState } from 'react'
import { cn } from '@/utils/cn'
import { ChevronDown } from 'lucide-react'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: string
  options?: { value: string; label: string }[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, options, children, onFocus, onBlur, ...props }, ref) => {
    const [isFocused, setIsFocused] = useState(false)

    const handleFocus = (e: React.FocusEvent<HTMLSelectElement>) => {
      setIsFocused(true)
      onFocus?.(e)
    }

    const handleBlur = (e: React.FocusEvent<HTMLSelectElement>) => {
      setIsFocused(false)
      onBlur?.(e)
    }

    return (
      <div className="w-full">
        <div className="relative">
          <select
            ref={ref}
            className={cn(
              // Base styling with luxury theme
              'w-full h-10 px-4 pr-10 text-base appearance-none',
              'bg-white dark:bg-warmgray-800',
              'border border-warmgray-300 dark:border-warmgray-700',
              'rounded-lg transition-all duration-200',
              'text-warmgray-900 dark:text-warmgray-100',
              
              // Focus styling with copper accent
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-warmgray-900',
              
              // Disabled state
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-warmgray-100 dark:disabled:bg-warmgray-700',
              
              // Error state
              error ? 'border-rose-500 dark:border-rose-600 focus:ring-rose-400' :
              // Focused state with copper
              isFocused ? 'border-copper-500 dark:border-copper-400 focus:ring-copper-400 shadow-sm shadow-copper-100 dark:shadow-copper-950' :
              // Default state
              'focus:ring-copper-400',
              
              className
            )}
            onFocus={handleFocus}
            onBlur={handleBlur}
            {...props}
          >
            {options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
            {children}
          </select>
          {/* Custom chevron icon */}
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warmgray-500 dark:text-warmgray-400 pointer-events-none" />
        </div>
        {error && (
          <p className="mt-2 text-sm text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'
