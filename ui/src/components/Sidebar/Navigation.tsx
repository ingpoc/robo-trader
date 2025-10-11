import { NavLink } from 'react-router-dom'
import { cn } from '@/utils/format'
import { useDashboardStore } from '@/store/dashboardStore'

const menuItems = [
  { path: '/', label: 'Overview' },
  { path: '/agents', label: 'Agents' },
  { path: '/trading', label: 'Trading' },
  { path: '/config', label: 'Config' },
  { path: '/agent-config', label: 'Agent Config' },
  { path: '/logs', label: 'Logs' },
]

export function Navigation() {
  const isConnected = useDashboardStore((state) => state.isConnected)

  return (
    <nav className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="flex items-center h-14 px-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-gray-900 flex items-center justify-center">
            <span className="text-white text-sm font-semibold">R</span>
          </div>
          <span className="text-sm font-semibold text-gray-900">Robo Trader</span>
        </div>
      </div>

      <div className="flex flex-col gap-0.5 p-2 flex-1">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'flex items-center px-3 h-10 text-sm transition-colors relative',
                isActive
                  ? 'bg-gray-900 text-white font-medium before:content-[""] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-white'
                  : 'text-gray-700 hover:bg-gray-100'
              )
            }
          >
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="flex items-center gap-2 h-12 px-4 border-t border-gray-200 text-xs">
        <div
          className={cn(
            'w-1.5 h-1.5',
            isConnected ? 'bg-success' : 'bg-gray-300'
          )}
        />
        <span className="text-gray-600">
          {isConnected ? 'Connected' : 'Offline'}
        </span>
      </div>
    </nav>
  )
}
