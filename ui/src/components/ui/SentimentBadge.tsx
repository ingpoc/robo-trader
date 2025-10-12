import { memo } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { SENTIMENT_COLORS } from '@/lib/constants'
import type { SentimentType } from '@/types/domain'

interface SentimentBadgeProps {
  sentiment: SentimentType
  className?: string
}

export const SentimentBadge = memo<SentimentBadgeProps>(({
  sentiment,
  className = '',
}) => {
  const getSentimentIcon = (sentiment: SentimentType) => {
    switch (sentiment) {
      case 'positive':
        return <TrendingUp className="w-4 h-4" />
      case 'negative':
        return <TrendingDown className="w-4 h-4" />
      default:
        return <Minus className="w-4 h-4" />
    }
  }

  const colors = SENTIMENT_COLORS[sentiment] || SENTIMENT_COLORS.neutral

  return (
    <Badge
      className={`px-3 py-2 text-sm font-semibold border-2 flex items-center gap-2 transition-all duration-200 ${colors.bg} ${colors.border} ${colors.text} ${className}`}
      role="status"
      aria-label={`Sentiment: ${sentiment}`}
    >
      {getSentimentIcon(sentiment)}
      <span className="capitalize">{sentiment}</span>
    </Badge>
  )
})

SentimentBadge.displayName = 'SentimentBadge'