import { forwardRef, HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export interface TabNavigationProps extends HTMLAttributes<HTMLDivElement> {
  tabs: { id: string; label: string; active?: boolean }[]
  onTabChange?: (tabId: string) => void
}

export const TabNavigation = forwardRef<HTMLDivElement, TabNavigationProps>(
  ({ className, tabs, onTabChange, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('flex border-b border-border', className)} {...props}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange?.(tab.id)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
              tab.active
                ? 'border-primary text-foreground bg-muted/60'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
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
