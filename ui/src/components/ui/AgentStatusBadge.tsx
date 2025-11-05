import { memo } from 'react'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { AGENT_STATUS_COLORS } from '@/lib/constants'
import type { AgentStatus } from '@/types/domain'

interface AgentStatusBadgeProps {
  status: AgentStatus
  className?: string
}

export const AgentStatusBadge = memo<AgentStatusBadgeProps>(({
  status,
  className = '',
}) => {
  const getStatusIcon = (status: AgentStatus) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-4 h-4" />
      case 'inactive':
        return <XCircle className="w-4 h-4" />
      case 'error':
        return <AlertCircle className="w-4 h-4" />
    }
  }

  const colors = AGENT_STATUS_COLORS[status]

  return (
    <Badge
      className={`px-3 py-2 text-sm font-semibold border-2 flex items-center gap-2 transition-all duration-200 ${colors.bg} ${colors.border} ${colors.text} ${className}`}
      role="status"
      aria-label={`Agent status: ${status}`}
    >
      {getStatusIcon(status)}
      <span className="capitalize">{status}</span>
    </Badge>
  )
})

AgentStatusBadge.displayName = 'AgentStatusBadge'