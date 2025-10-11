import { NavLink } from 'react-router-dom'
import { cn } from '@/utils/format'
import { useDashboardStore } from '@/store/dashboardStore'
import { Button } from '@/components/ui/Button'

const menuItems = [
  { path: '/', label: 'Overview' },
  { path: '/agents', label: 'Agents' },
  { path: '/trading', label: 'Trading' },
  { path: '/config', label: 'Config' },
  { path: '/agent-config', label: 'Agent Config' },
  { path: '/logs', label: 'Logs' },
]

interface NavigationProps {
  onClose?: () => void
}

export function Navigation({ onClose }: NavigationProps) {
  const isConnected = useDashboardStore((state) => state.isConnected)

  return (
    <nav
      className="flex flex-col h-full bg-white/95 backdrop-blur-sm border-r border-gray-200/50 shadow-lg"
      aria-label="Main navigation"
      role="navigation"
    >
      <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200/50">
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 bg-accent rounded flex items-center justify-center shadow-sm"
            aria-hidden="true"
          >
            <span className="text-white text-sm font-bold">R</span>
          </div>
          <span className="text-sm font-semibold text-gray-900">Robo Trader</span>
        </div>
        {onClose && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="lg:hidden h-8 w-8 p-0"
            aria-label="Close sidebar"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        )}
      </div>

      <div className="flex flex-col gap-1 p-3 flex-1" role="menubar">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={onClose}
            role="menuitem"
            tabIndex={0}
            aria-current={({ isActive }) => isActive ? 'page' : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 relative group focus-ring',
                isActive
                  ? 'bg-accent text-white shadow-md before:content-[""] before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-6 before:bg-white before:rounded-r'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-accent hover:shadow-sm'
              )
            }
          >
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div
        className="flex items-center gap-3 h-14 px-4 border-t border-gray-200/50 bg-gray-50/50 text-xs"
        role="status"
        aria-live="polite"
        aria-label="Connection status"
      >
        <div
          className={cn(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-success shadow-sm shadow-success/50 animate-pulse' : 'bg-gray-400'
          )}
          aria-hidden="true"
        />
        <span
          className={cn(
            'font-medium',
            isConnected ? 'text-success-dark' : 'text-gray-500'
          )}
          id="connection-status"
        >
          {isConnected ? 'Connected' : 'Offline'}
        </span>
      </div>
    </nav>
  )
}
