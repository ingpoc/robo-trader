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
import { Home, Newspaper, Users, Settings, FileText, X, Wifi, WifiOff, User, LogOut, Bell, Palette, Wallet, Eye, Database } from 'lucide-react'

const menuItems = [
  { path: '/', label: 'Overview', icon: Home },
  { path: '/news-earnings', label: 'News & Earnings', icon: Newspaper },
  { path: '/agents', label: 'Agents', icon: Users },
  { path: '/paper-trading', label: 'Paper Trading', icon: Wallet },
  { path: '/ai-transparency', label: 'AI Transparency', icon: Eye },
  { path: '/system-health', label: 'System Health', icon: Database },
  { path: '/config', label: 'Config', icon: Settings },
  { path: '/logs', label: 'Logs', icon: FileText },
]

interface NavigationProps {
  onClose?: () => void
}

export function Navigation({ onClose }: NavigationProps) {
  const isConnected = useDashboardStore((state) => state.isConnected)

  return (
    <nav
      className="flex flex-col h-full bg-gradient-to-b from-white/98 to-warmgray-50/95 dark:from-warmgray-800/98 dark:to-warmgray-900/95 backdrop-blur-sm border-r border-warmgray-300/50 dark:border-warmgray-700/50 shadow-lg"
      aria-label="Main navigation"
      role="navigation"
    >
      <div className="flex items-center justify-between h-16 px-6 border-b border-warmgray-200 dark:border-warmgray-700 bg-gradient-to-r from-white/90 to-warmgray-50/70 dark:from-warmgray-800/90 dark:to-warmgray-900/70">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 bg-gradient-to-br from-copper-500 to-copper-600 dark:from-copper-400 dark:to-copper-600 rounded-xl flex items-center justify-center shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105"
            aria-hidden="true"
          >
            <span className="text-white text-sm font-black">R</span>
          </div>
          <span className="text-lg font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">Robo Trader</span>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 hover:bg-warmgray-100 dark:hover:bg-warmgray-800 rounded-full"
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
              className="lg:hidden h-8 w-8 p-0 hover:bg-warmgray-100 dark:hover:bg-warmgray-800"
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
                  'flex items-center gap-4 px-4 py-3 text-sm font-bold rounded-lg transition-all duration-300 relative group focus:ring-2 focus:ring-copper-400 focus:ring-offset-2 dark:focus:ring-offset-warmgray-900',
                  isActive
                    ? 'bg-gradient-to-r from-copper-500 to-copper-600 dark:from-copper-600 dark:to-copper-700 text-white shadow-md before:content-[""] before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-8 before:bg-white dark:before:bg-warmgray-100 before:rounded-r before:shadow-lg'
                    : 'text-warmgray-700 dark:text-warmgray-300 hover:bg-gradient-to-r hover:from-warmgray-100 hover:to-warmgray-200 dark:hover:from-warmgray-700 dark:hover:to-warmgray-800 hover:text-copper-600 dark:hover:text-copper-400 hover:shadow-sm'
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
        className="flex items-center gap-3 h-16 px-6 border-t border-warmgray-200 dark:border-warmgray-700 bg-gradient-to-r from-warmgray-50/80 to-warmgray-100/60 dark:from-warmgray-900/80 dark:to-warmgray-800/60 text-xs"
        role="status"
        aria-live="polite"
        aria-label="Connection status"
      >
        {isConnected ? (
          <Wifi className="w-5 h-5 text-emerald-600 dark:text-emerald-400 animate-pulse" />
        ) : (
          <WifiOff className="w-5 h-5 text-warmgray-400 dark:text-warmgray-500" />
        )}
        <span
          className={cn(
            'font-bold transition-colors duration-200',
            isConnected ? 'text-emerald-700 dark:text-emerald-300' : 'text-warmgray-500 dark:text-warmgray-400'
          )}
          id="connection-status"
        >
          {isConnected ? 'Connected' : 'Offline'}
        </span>
      </div>
    </nav>
  )
}