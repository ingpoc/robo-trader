import { NavLink } from 'react-router-dom'
import { cn } from '@/utils/format'
import { useDashboardStore } from '@/store/dashboardStore'

const menuItems = [
  { path: '/', label: 'Dashboard', icon: '▦' },
  { path: '/agents', label: 'AI Agents', icon: '◆' },
  { path: '/trading', label: 'Trading', icon: '⇄' },
  { path: '/config', label: 'Settings', icon: '⚙' },
  { path: '/agent-config', label: 'Agent Configuration', icon: '⚙' },
  { path: '/logs', label: 'Logs', icon: '≡' },
]

export function Navigation() {
  const isConnected = useDashboardStore((state) => state.isConnected)

  return (
    <nav className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="flex items-center gap-2 h-16 px-4 border-b border-gray-200">
        <div className="w-8 h-8 bg-gray-900 rounded flex items-center justify-center">
          <span className="text-white text-lg font-bold">R</span>
        </div>
        <div className="flex flex-col">
          <span className="text-base font-semibold text-gray-900">Robo Trader</span>
          <span className="text-xs text-gray-600">AI Trading</span>
        </div>
      </div>

      <div className="flex flex-col gap-1 p-2 flex-1">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 h-10 rounded transition-colors',
                isActive
                  ? 'bg-gray-100 text-gray-900 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              )
            }
          >
            <span aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="flex flex-col gap-2 p-4 border-t border-gray-200">
        <div className="flex items-center gap-2 text-sm">
          <div
            className={cn(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-gray-900' : 'bg-gray-300'
            )}
          />
          <span className="text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </nav>
  )
}
