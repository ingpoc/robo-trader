import { cn } from '@/utils/format'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  text?: string
  variant?: 'default' | 'primary' | 'secondary'
  showProgress?: boolean
  progress?: number
}

export function LoadingSpinner({
  size = 'md',
  className,
  text,
  variant = 'default',
  showProgress = false,
  progress
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  }

  const colorClasses = {
    default: 'text-gray-600',
    primary: 'text-accent',
    secondary: 'text-gray-400'
  }

  return (
    <div className={cn('flex flex-col items-center justify-center gap-2', className)}>
      <div className="relative">
        <svg
          className={cn(
            'animate-spin',
            sizeClasses[size],
            colorClasses[variant]
          )}
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        {showProgress && progress !== undefined && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className={cn(
              'text-xs font-medium',
              colorClasses[variant]
            )}>
              {Math.round(progress)}%
            </div>
          </div>
        )}
      </div>
      {text && (
        <p className={cn(
          'text-sm font-medium text-center',
          colorClasses[variant]
        )}>
          {text}
        </p>
      )}
      {showProgress && progress !== undefined && (
        <div className="w-full max-w-32">
          <ProgressBar progress={progress} size="sm" />
        </div>
      )}
    </div>
  )
}

interface ProgressBarProps {
  progress: number // 0-100
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'success' | 'warning' | 'error'
}

export function ProgressBar({
  progress,
  className,
  showLabel = false,
  size = 'md',
  variant = 'default'
}: ProgressBarProps) {
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  }

  const colorClasses = {
    default: 'bg-accent',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error'
  }

  return (
    <div className={cn('w-full', className)}>
      <div className={cn(
        'w-full bg-gray-200 rounded-full overflow-hidden',
        sizeClasses[size]
      )}>
        <div
          className={cn(
            'h-full transition-all duration-300 ease-out rounded-full',
            colorClasses[variant]
          )}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between items-center mt-1">
          <span className="text-xs text-gray-500">Progress</span>
          <span className="text-xs font-medium text-gray-700">
            {Math.round(progress)}%
          </span>
        </div>
      )}
    </div>
  )
}

interface LoadingOverlayProps {
  isVisible: boolean
  text?: string
  className?: string
}

export function LoadingOverlay({
  isVisible,
  text = 'Loading...',
  className
}: LoadingOverlayProps) {
  if (!isVisible) return null

  return (
    <div className={cn(
      'absolute inset-0 z-50 flex items-center justify-center',
      'bg-white/80 backdrop-blur-sm rounded-lg',
      className
    )}>
      <div className="flex flex-col items-center gap-3 p-6 bg-white rounded-lg shadow-lg border">
        <LoadingSpinner size="lg" variant="primary" />
        <p className="text-sm font-medium text-gray-700">{text}</p>
      </div>
    </div>
  )
}