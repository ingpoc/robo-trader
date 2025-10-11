import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/utils/format'

interface BreadcrumbItem {
  label: string
  path?: string
}

interface BreadcrumbProps {
  items?: BreadcrumbItem[]
  className?: string
}

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/agents': 'Agents',
  '/trading': 'Trading',
  '/config': 'Configuration',
  '/agent-config': 'Agent Configuration',
  '/logs': 'System Logs',
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  const location = useLocation()

  // Auto-generate breadcrumbs from current path if not provided
  const breadcrumbItems = items || React.useMemo(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbItem[] = [{ label: 'Dashboard', path: '/' }]

    let currentPath = ''
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`
      const label = routeLabels[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1)
      breadcrumbs.push({ label, path: currentPath })
    })

    return breadcrumbs
  }, [location.pathname])

  if (breadcrumbItems.length <= 1) return null

  return (
    <nav
      className={cn('flex items-center space-x-1 text-sm text-gray-600', className)}
      aria-label="Breadcrumb"
    >
      {breadcrumbItems.map((item, index) => {
        const isLast = index === breadcrumbItems.length - 1
        const isFirst = index === 0

        return (
          <div key={item.path || item.label} className="flex items-center">
            {index > 0 && (
              <svg className="w-4 h-4 mx-1 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}

            {isLast ? (
              <span
                className="font-medium text-gray-900 px-2 py-1 rounded-md bg-gray-100"
                aria-current="page"
              >
                {item.label}
              </span>
            ) : item.path ? (
              <NavLink
                to={item.path}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 rounded-md transition-colors hover:bg-gray-100 hover:text-gray-900',
                  isFirst && 'font-medium'
                )}
              >
                {isFirst && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                )}
                <span>{item.label}</span>
              </NavLink>
            ) : (
              <span className="px-2 py-1">{item.label}</span>
            )}
          </div>
        )
      })}
    </nav>
  )
}

// Alternative compact version for mobile
export function BreadcrumbCompact({ items, className }: BreadcrumbProps) {
  const location = useLocation()

  const breadcrumbItems = items || React.useMemo(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbItem[] = [{ label: 'Dashboard', path: '/' }]

    let currentPath = ''
    pathSegments.forEach((segment) => {
      currentPath += `/${segment}`
      const label = routeLabels[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1)
      breadcrumbs.push({ label, path: currentPath })
    })

    return breadcrumbs
  }, [location.pathname])

  if (breadcrumbItems.length <= 1) return null

  const currentItem = breadcrumbItems[breadcrumbItems.length - 1]
  const parentItem = breadcrumbItems[breadcrumbItems.length - 2]

  return (
    <nav className={cn('flex items-center text-sm', className)} aria-label="Breadcrumb">
      {parentItem?.path && (
        <>
          <NavLink
            to={parentItem.path}
            className="text-gray-600 hover:text-gray-900 transition-colors"
          >
            {parentItem.label}
          </NavLink>
          <svg className="w-4 h-4 mx-1 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </>
      )}
      <span className="font-medium text-gray-900" aria-current="page">
        {currentItem.label}
      </span>
    </nav>
  )
}