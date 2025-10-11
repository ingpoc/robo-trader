import { cn } from '@/utils/format'

interface SkeletonLoaderProps {
  className?: string
  variant?: 'default' | 'card' | 'text' | 'circle' | 'rectangle'
  lines?: number
}

export function SkeletonLoader({
  className,
  variant = 'default',
  lines = 1
}: SkeletonLoaderProps) {
  const baseClasses = 'skeleton-shimmer bg-gray-200'

  if (variant === 'card') {
    return (
      <div className={cn('card-shadow rounded-lg p-4 bg-white', className)}>
        <div className={cn('h-4 w-3/4 mb-3', baseClasses)} />
        <div className={cn('h-8 w-1/2 mb-4', baseClasses)} />
        <div className={cn('h-3 w-full mb-2', baseClasses)} />
        <div className={cn('h-3 w-4/5', baseClasses)} />
      </div>
    )
  }

  if (variant === 'text') {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-4',
              i === lines - 1 ? 'w-3/4' : 'w-full',
              baseClasses
            )}
          />
        ))}
      </div>
    )
  }

  if (variant === 'circle') {
    return (
      <div
        className={cn(
          'rounded-full aspect-square',
          baseClasses,
          className
        )}
      />
    )
  }

  if (variant === 'rectangle') {
    return (
      <div
        className={cn(
          'rounded-md',
          baseClasses,
          className
        )}
      />
    )
  }

  // Default variant
  return (
    <div
      className={cn(
        'h-4 w-full rounded',
        baseClasses,
        className
      )}
    />
  )
}

interface SkeletonGridProps {
  rows: number
  cols: number
  className?: string
}

export function SkeletonGrid({ rows, cols, className }: SkeletonGridProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-3">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <SkeletonLoader
              key={colIndex}
              className={cn(
                'flex-1 h-4',
                colIndex === cols - 1 && rowIndex === rows - 1 ? 'w-3/4' : 'w-full'
              )}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface SkeletonCardProps {
  className?: string
  showAvatar?: boolean
  lines?: number
}

export function SkeletonCard({ className, showAvatar = false, lines = 3 }: SkeletonCardProps) {
  return (
    <div className={cn('card-shadow rounded-lg p-4 bg-white', className)}>
      {showAvatar && (
        <div className="flex items-center space-x-3 mb-3">
          <SkeletonLoader variant="circle" className="w-10 h-10" />
          <div className="flex-1 space-y-2">
            <SkeletonLoader className="h-4 w-1/2" />
            <SkeletonLoader className="h-3 w-1/3" />
          </div>
        </div>
      )}
      <SkeletonLoader variant="text" lines={lines} />
    </div>
  )
}