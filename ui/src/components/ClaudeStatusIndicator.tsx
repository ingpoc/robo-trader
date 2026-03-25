import { useClaudeStatus } from '@/hooks/useClaudeStatus'
import { cn } from '@/lib/utils'

const STATUS_META = {
  unavailable: {
    label: 'Claude offline',
    tone: 'text-muted-foreground',
    dot: 'bg-muted-foreground/50',
  },
  authenticated: {
    label: 'Claude auth',
    tone: 'text-amber-700',
    dot: 'bg-amber-500',
  },
  degraded: {
    label: 'Claude limited',
    tone: 'text-amber-700',
    dot: 'bg-amber-500',
  },
  idle: {
    label: 'Claude ready',
    tone: 'text-emerald-700',
    dot: 'bg-emerald-500',
  },
  'connected/idle': {
    label: 'Claude ready',
    tone: 'text-emerald-700',
    dot: 'bg-emerald-500',
  },
  analyzing: {
    label: 'Claude active',
    tone: 'text-primary',
    dot: 'bg-primary animate-pulse',
  },
} as const

export function ClaudeStatusIndicator() {
  const { status, message } = useClaudeStatus()
  const meta = STATUS_META[status]

  return (
    <div className="flex items-center gap-2" title={message}>
      <span className={cn('h-2.5 w-2.5 rounded-full', meta.dot)} aria-hidden="true" />
      <span className={cn('text-xs font-semibold', meta.tone)}>{meta.label}</span>
    </div>
  )
}
