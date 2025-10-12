import { NavLink } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useDashboardStore } from '@/store/dashboardStore'
import { Button } from '@/components/ui/Button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Home, Newspaper, Users, TrendingUp, Settings, Settings2, FileText, X, Wifi, WifiOff, User, LogOut, Bell, Palette } from 'lucide-react'

const menuItems = [
  { path: '/', label: 'Overview', icon: Home },
  { path: '/news-earnings', label: 'News & Earnings', icon: Newspaper },
  { path: '/agents', label: 'Agents', icon: Users },
  { path: '/trading', label: 'Trading', icon: TrendingUp },
  { path: '/config', label: 'Config', icon: Settings },
  { path: '/agent-config', label: 'Agent Config', icon: Settings2 },
  { path: '/logs', label: 'Logs', icon: FileText },
]

interface NavigationProps {
  onClose?: () => void
}

export function Navigation({ onClose }: NavigationProps) {
  const isConnected = useDashboardStore((state) => state.isConnected)

  return (
    <nav
      className="flex flex-col h-full bg-gradient-to-b from-white/95 to-gray-50/90 backdrop-blur-sm border-r border-gray-200/50 shadow-professional"
      aria-label="Main navigation"
      role="navigation"
    >
      <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200/50 bg-gradient-to-r from-white/80 to-gray-50/60">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-professional"
            aria-hidden="true"
          >
            <span className="text-white text-sm font-black">R</span>
          </div>
          <span className="text-lg font-bold text-gray-900 bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">Robo Trader</span>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-full"
                aria-label="User menu"
              >
                <User className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="cursor-pointer">
                <User className="mr-2 h-4 w-4" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer">
                <Bell className="mr-2 h-4 w-4" />
                Notifications
              </DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer">
                <Palette className="mr-2 h-4 w-4" />
                Theme
              </DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer">
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="cursor-pointer text-red-600 focus:text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="lg:hidden h-8 w-8 p-0 hover:bg-gray-100 dark:hover:bg-slate-800"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1 p-3 flex-1" role="menubar">
        {menuItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              role="menuitem"
              tabIndex={0}
              aria-current={({ isActive }) => isActive ? 'page' : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-4 px-4 py-3 text-sm font-bold rounded-xl transition-all duration-300 relative group focus-ring',
                  isActive
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-professional before:content-[""] before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-8 before:bg-white before:rounded-r before:shadow-lg'
                    : 'text-gray-700 hover:bg-gradient-to-r hover:from-gray-100 hover:to-gray-200 hover:text-blue-700 hover:shadow-md'
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          )
        })}
      </div>

      <div
        className="flex items-center gap-3 h-16 px-6 border-t border-gray-200/50 bg-gradient-to-r from-gray-50/80 to-gray-100/60 text-xs"
        role="status"
        aria-live="polite"
        aria-label="Connection status"
      >
        {isConnected ? (
          <Wifi className="w-5 h-5 text-green-600 animate-pulse" />
        ) : (
          <WifiOff className="w-5 h-5 text-gray-400" />
        )}
        <span
          className={cn(
            'font-bold',
            isConnected ? 'text-green-700' : 'text-gray-500'
          )}
          id="connection-status"
        >
          {isConnected ? 'Connected' : 'Offline'}
        </span>
      </div>
    </nav>
  )
}