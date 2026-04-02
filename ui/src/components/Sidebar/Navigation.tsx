import { NavLink } from 'react-router-dom'
import { Activity, Home, Settings, Wallet, X } from 'lucide-react'

import { ClaudeStatusIndicator } from '@/components/ClaudeStatusIndicator'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

const menuItems = [
  { path: '/', label: 'Overview', icon: Home, detail: 'Capital, blockers, operator posture' },
  { path: '/health', label: 'Health', icon: Activity, detail: 'Runtime truth, readiness, broker state' },
  { path: '/paper-trading', label: 'Paper Trading', icon: Wallet, detail: 'Explicit discovery, research, review' },
  { path: '/configuration', label: 'Configuration', icon: Settings, detail: 'Policy, limits, criteria guardrails' },
]

interface NavigationProps {
  onClose?: () => void
}

export function Navigation({ onClose }: NavigationProps) {
  return (
    <nav
      className="flex h-full flex-col border-r border-border/80 bg-white/95 backdrop-blur-sm dark:bg-warmgray-800/95"
      aria-label="Main navigation"
      role="navigation"
    >
      <div className="flex min-h-[5.5rem] items-start justify-between border-b border-border/80 px-6 py-5">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div
              className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-background text-foreground"
              aria-hidden="true"
            >
              <span className="text-sm font-semibold">R</span>
            </div>
            <div>
              <p className="font-serif text-lg font-semibold text-foreground">Robo Trader</p>
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Paper-first operator desk</p>
            </div>
          </div>
          <p className="max-w-[13rem] text-sm leading-6 text-muted-foreground">
            Treat AI as a precise instrument. Nothing expensive should happen without a clear operator intent.
          </p>
        </div>

        {onClose ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </Button>
        ) : null}
      </div>

      <div className="flex flex-1 flex-col px-4 py-4">
        <div className="mb-3 px-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Navigation</p>
        </div>

        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-start gap-3 rounded-xl px-4 py-3 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                    isActive ? 'bg-muted/60 text-foreground' : 'text-muted-foreground hover:bg-muted/35 hover:text-foreground',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        'absolute bottom-3 left-0 top-3 w-px rounded-full transition-colors',
                        isActive ? 'bg-primary' : 'bg-transparent group-hover:bg-border',
                      )}
                      aria-hidden="true"
                    />
                    <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', isActive ? 'text-primary' : 'text-muted-foreground')} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold">{item.label}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
                    </div>
                  </>
                )}
              </NavLink>
            )
          })}
        </div>
      </div>

      <div className="border-t border-border/80 px-6 py-4">
        <div className="flex items-center justify-end gap-3 text-xs">
          <ClaudeStatusIndicator />
        </div>
      </div>
    </nav>
  )
}
