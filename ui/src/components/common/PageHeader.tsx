import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  description,
  icon,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <section className={cn('page-header', className)}>
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          {icon ? (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-copper-200/70 bg-copper-50 text-copper-700 shadow-sm">
              {icon}
            </div>
          ) : null}
          <div className="min-w-0">
            <h1 className="page-title">{title}</h1>
            {description ? <p className="page-subtitle">{description}</p> : null}
          </div>
        </div>

        {actions ? (
          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            {actions}
          </div>
        ) : null}
      </div>
    </section>
  )
}
