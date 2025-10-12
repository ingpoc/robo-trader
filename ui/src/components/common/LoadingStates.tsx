import { LoadingSpinner, LoadingOverlay, ProgressBar } from './LoadingSpinner'

interface LoadingCardProps {
  title?: string
  description?: string
  variant?: 'skeleton' | 'spinner'
  className?: string
}

export function LoadingCard({ title, description, variant = 'skeleton', className }: LoadingCardProps) {
  if (variant === 'spinner') {
    return (
      <div className={`flex flex-col gap-4 p-6 bg-white border border-gray-200 card-shadow rounded-lg ${className || ''}`}>
        {title && (
          <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">
            {title}
          </div>
        )}
        <div className="flex-1 flex items-center justify-center py-8">
          <LoadingSpinner
            size="lg"
            variant="primary"
            text={description || 'Loading...'}
          />
        </div>
      </div>
    )
  }

  return (
    <div className={`flex flex-col gap-4 p-6 bg-white border border-gray-200 card-shadow rounded-lg ${className || ''}`}>
      {title && (
        <div className="text-xs font-medium text-gray-600 uppercase tracking-wider">
          {title}
        </div>
      )}
      <div className="flex flex-col gap-3">
        <div className="h-4 bg-gray-100 skeleton-shimmer rounded" />
        <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-3/4" />
        <div className="h-16 bg-gray-100 skeleton-shimmer rounded" />
        <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-1/2" />
      </div>
    </div>
  )
}

interface LoadingButtonProps {
  loading: boolean
  children: React.ReactNode
  loadingText?: string
  progress?: number
  className?: string
  onClick?: () => void
  disabled?: boolean
}

export function LoadingButton({
  loading,
  children,
  loadingText,
  progress,
  className,
  onClick,
  disabled
}: LoadingButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-accent hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed ${className || ''}`}
    >
      {loading ? (
        <div className="flex items-center gap-2">
          <LoadingSpinner
            size="sm"
            variant="default"
            showProgress={progress !== undefined}
            progress={progress}
          />
          {loadingText || 'Loading...'}
        </div>
      ) : (
        children
      )}
    </button>
  )
}

interface LoadingListProps {
  count?: number
  className?: string
}

export function LoadingList({ count = 3, className }: LoadingListProps) {
  return (
    <div className={`flex flex-col gap-3 ${className || ''}`}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="p-4 border border-gray-200 bg-white rounded-lg">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 bg-gray-100 skeleton-shimmer rounded-full" />
            <div className="flex-1">
              <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-1/3 mb-1" />
              <div className="h-3 bg-gray-100 skeleton-shimmer rounded w-1/4" />
            </div>
          </div>
          <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-full mb-1" />
          <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-2/3" />
        </div>
      ))}
    </div>
  )
}

interface LoadingTableProps {
  rows?: number
  columns?: number
  className?: string
}

export function LoadingTable({ rows = 5, columns = 4, className }: LoadingTableProps) {
  return (
    <div className={`border border-gray-200 rounded-lg overflow-hidden ${className || ''}`}>
      {/* Table Header */}
      <div className="bg-gray-50 border-b border-gray-200 p-4">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, index) => (
            <div key={index} className="h-4 bg-gray-200 skeleton-shimmer rounded flex-1" />
          ))}
        </div>
      </div>
      {/* Table Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="border-b border-gray-100 last:border-b-0 p-4">
          <div className="flex gap-4">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <div key={colIndex} className="h-4 bg-gray-100 skeleton-shimmer rounded flex-1" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

interface LoadingChartProps {
  className?: string
}

export function LoadingChart({ className }: LoadingChartProps) {
  return (
    <div className={`p-6 bg-white border border-gray-200 card-shadow rounded-lg ${className || ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="h-5 bg-gray-100 skeleton-shimmer rounded w-32" />
        <div className="h-4 bg-gray-100 skeleton-shimmer rounded w-20" />
      </div>
      <div className="h-64 bg-gray-100 skeleton-shimmer rounded" />
      <div className="flex justify-between mt-4">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="h-3 bg-gray-100 skeleton-shimmer rounded w-12" />
        ))}
      </div>
    </div>
  )
}

export { LoadingSpinner, LoadingOverlay, ProgressBar }