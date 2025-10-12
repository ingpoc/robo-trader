import { memo } from 'react'
import { TrendingUp, TrendingDown, Target } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { RECOMMENDATION_COLORS } from '@/lib/constants'
import type { RecommendationAction } from '@/types/domain'

interface RecommendationBadgeProps {
  action: RecommendationAction
  className?: string
}

export const RecommendationBadge = memo<RecommendationBadgeProps>(({
  action,
  className = '',
}) => {
  const getRecommendationIcon = (action: RecommendationAction) => {
    switch (action) {
      case 'buy':
        return <TrendingUp className="w-5 h-5" />
      case 'sell':
        return <TrendingDown className="w-5 h-5" />
      default:
        return <Target className="w-5 h-5" />
    }
  }

  const colors = RECOMMENDATION_COLORS[action]

  return (
    <Badge
      className={`px-4 py-2 text-sm font-bold border-2 flex items-center gap-2 ${colors} ${className}`}
      role="status"
      aria-label={`Recommendation: ${action}`}
    >
      {getRecommendationIcon(action)}
      <span>{action.toUpperCase()}</span>
    </Badge>
  )
})

RecommendationBadge.displayName = 'RecommendationBadge'