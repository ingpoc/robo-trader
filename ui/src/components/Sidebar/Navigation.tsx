import { NavLink } from 'react-router-dom'
import { Home, Settings, Wallet, Database, Wifi, WifiOff, X } from 'lucide-react'

import { ClaudeStatusIndicator } from '@/components/ClaudeStatusIndicator'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'
import { useSystemStatusStore } from '@/stores/systemStatusStore'

const menuItems = [
  { path: '/', label: 'Overview', icon: Home },
  { path: '/paper-trading', label: 'Paper Trading', icon: Wallet },
  { path: '/system-health', label: 'System Health', icon: Database },
  { path: '/configuration', label: 'Configuration', icon: Settings },
]

interface NavigationProps {
  onClose?: () => void
}

export function Navigation({ onClose }: NavigationProps) {
  const isConnected = useSystemStatusStore((state) => state.isConnected)

  return (
    <nav
      className="flex h-full flex-col border-r border-border/80 bg-card/95 shadow-sm backdrop-blur-sm"
      aria-label="Main navigation"
      role="navigation"
    >
      <div className="flex h-16 items-center justify-between border-b border-border/80 px-6">
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-2xl border border-border bg-muted text-foreground shadow-sm"
            aria-hidden="true"
          >
            <span className="text-sm font-black">R</span>
          </div>
          <div>
            <p className="font-serif text-lg font-bold text-foreground">Robo Trader</p>
            <p className="text-xs text-muted-foreground">Paper-trading operator</p>
          </div>
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

      <div className="flex flex-1 flex-col gap-1 p-3">
        {menuItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-4 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          )
        })}
      </div>

      <div
        className="flex h-16 items-center justify-between gap-4 border-t border-border/80 bg-muted/35 px-6 text-xs"
        role="status"
        aria-live="polite"
        aria-label="System status"
      >
        <div className="flex items-center gap-3">
          {isConnected ? (
            <Wifi className="h-5 w-5 animate-pulse text-emerald-600" />
          ) : (
            <WifiOff className="h-5 w-5 text-muted-foreground" />
          )}
          <span
            className={cn(
              'font-semibold transition-colors duration-200',
              isConnected ? 'text-emerald-700' : 'text-muted-foreground'
            )}
          >
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>

        <ClaudeStatusIndicator />
      </div>
    </nav>
  )
}
