import { forwardRef, HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export interface TabNavigationProps extends HTMLAttributes<HTMLDivElement> {
  tabs: { id: string; label: string; active?: boolean }[]
  onTabChange?: (tabId: string) => void
}

export const TabNavigation = forwardRef<HTMLDivElement, TabNavigationProps>(
  ({ className, tabs, onTabChange, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('flex border-b border-warmgray-300', className)} {...props}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange?.(tab.id)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-copper-500 focus:ring-offset-2',
              tab.active
                ? 'border-copper-500 text-copper-600 bg-copper-50'
                : 'border-transparent text-warmgray-500 hover:text-warmgray-700 hover:border-warmgray-300'
            )}
            role="tab"
            aria-selected={tab.active}
            tabIndex={tab.active ? 0 : -1}
          >
            {tab.label}
          </button>
        ))}
      </div>
    )
  }
)

TabNavigation.displayName = 'TabNavigation'