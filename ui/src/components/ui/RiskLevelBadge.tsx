import { memo } from 'react'
import { Shield, AlertTriangle, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { RISK_LEVEL_COLORS } from '@/lib/constants'
import type { RiskLevel } from '@/types/domain'

interface RiskLevelBadgeProps {
  level: RiskLevel
  className?: string
}

export const RiskLevelBadge = memo<RiskLevelBadgeProps>(({
  level,
  className = '',
}) => {
  const getRiskIcon = (level: RiskLevel) => {
    switch (level) {
      case 'low':
        return <Shield className="w-4 h-4" />
      case 'medium':
        return <AlertTriangle className="w-4 h-4" />
      case 'high':
        return <AlertCircle className="w-4 h-4" />
    }
  }

  const colors = RISK_LEVEL_COLORS[level]

  return (
    <Badge
      className={`px-3 py-2 text-sm font-semibold border-2 flex items-center gap-2 transition-all duration-200 ${colors.bg} ${colors.border} ${colors.text} ${className}`}
      role="status"
      aria-label={`Risk level: ${level}`}
    >
      {getRiskIcon(level)}
      <span className="capitalize">{level}</span>
    </Badge>
  )
})

RiskLevelBadge.displayName = 'RiskLevelBadge'