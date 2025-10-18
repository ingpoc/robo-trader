import { cn } from '@/lib/utils'

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
  const baseClasses = 'skeleton-shimmer-luxury bg-gradient-to-r from-warmgray-200 via-warmgray-100 to-warmgray-200 animate-pulse'

  if (variant === 'card') {
    return (
      <div className={cn('shadow-md rounded-xl p-6 bg-gradient-to-br from-white/95 to-warmgray-50/70 backdrop-blur-sm ring-1 ring-warmgray-300/50', className)}>
        <div className={cn('h-5 w-3/4 mb-4 rounded-lg', baseClasses)} />
        <div className={cn('h-8 w-1/2 mb-6 rounded-lg', baseClasses)} />
        <div className={cn('h-4 w-full mb-3 rounded-lg', baseClasses)} />
        <div className={cn('h-4 w-4/5 rounded-lg', baseClasses)} />
      </div>
    )
  }

  if (variant === 'text') {
    return (
      <div className={cn('space-y-3', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-4 rounded-lg',
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
    <div className={cn('shadow-professional rounded-xl p-6 bg-gradient-to-br from-white/95 to-warmgray-50/70 backdrop-blur-sm ring-1 ring-warmgray-300/50 animate-scale-in', className)}>
      {showAvatar && (
        <div className="flex items-center space-x-4 mb-4">
          <SkeletonLoader variant="circle" className="w-12 h-12" />
          <div className="flex-1 space-y-3">
            <SkeletonLoader className="h-5 w-1/2 rounded-lg" />
            <SkeletonLoader className="h-4 w-1/3 rounded-lg" />
          </div>
        </div>
      )}
      <SkeletonLoader variant="text" lines={lines} />
    </div>
  )
}

interface SkeletonTableProps {
  rows: number
  columns: number
  className?: string
}

export function SkeletonTable({ rows, columns, className }: SkeletonTableProps) {
  return (
    <div className={cn('space-y-4 p-6', className)}>
      {/* Table Header */}
      <div className="flex space-x-6 pb-4 border-b border-warmgray-300/50">
        {Array.from({ length: columns }).map((_, colIndex) => (
          <SkeletonLoader
            key={`header-${colIndex}`}
            className={cn(
              'h-5 rounded-lg',
              colIndex === 0 ? 'w-24' : colIndex === columns - 1 ? 'w-20' : 'w-28'
            )}
          />
        ))}
      </div>

      {/* Table Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-6 py-4 border-b border-warmgray-200/50 last:border-b-0">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <SkeletonLoader
              key={`cell-${rowIndex}-${colIndex}`}
              className={cn(
                'h-5 rounded-lg',
                colIndex === 0 ? 'w-24' : colIndex === columns - 1 ? 'w-20' : 'w-28'
              )}
            />
          ))}
        </div>
      ))}
    </div>
  )
}