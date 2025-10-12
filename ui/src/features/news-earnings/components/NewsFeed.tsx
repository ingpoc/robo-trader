import { memo, useCallback } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { SentimentBadge } from '@/components/ui/SentimentBadge'
import { formatDateTime, formatRelativeTime } from '@/utils/format'
import { useNewsEarningsStore } from '@/stores/newsEarningsStore'
import type { NewsItem } from '@/types/domain'

interface NewsFeedProps {
  news: NewsItem[]
  lastUpdated?: string | null
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
}

export const NewsFeed = memo<NewsFeedProps>(({
  news,
  lastUpdated,
  isLoading,
  error,
  onRetry,
}) => {
  const { expandedNews, toggleNewsExpansion } = useNewsEarningsStore()

  const handleToggleExpansion = useCallback((newsId: string) => {
    toggleNewsExpansion(newsId)
  }, [toggleNewsExpansion])

  if (isLoading) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📰 News Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-slate-600 dark:text-slate-400">Loading latest news...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📰 News Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md mx-auto">
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Unable to load news data</h3>
              <p className="text-red-700 dark:text-red-300 text-sm mb-4">{error}</p>
              {onRetry && (
                <Button onClick={onRetry} variant="outline" className="border-red-300 text-red-700 hover:bg-red-50">
                  Retry
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!news || news.length === 0) {
    return (
      <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📰 News Feed
          </CardTitle>
          {lastUpdated && (
            <div className="text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-3 py-1 rounded-full">
              Updated {formatRelativeTime(lastUpdated)}
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-slate-100 dark:bg-slate-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">📰</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Recent News</h3>
            <p className="text-slate-600 dark:text-slate-400">No recent news found for the selected stock</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-xl border-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl flex items-center gap-3 text-slate-900 dark:text-slate-100">
            📰 News Feed
          </CardTitle>
          {lastUpdated && (
            <div className="text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-3 py-1 rounded-full">
              Updated {formatRelativeTime(lastUpdated)}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {news.map((item) => (
            <article
              key={item.id}
              className="group border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-300 bg-white dark:bg-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/80"
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="font-bold text-lg text-slate-900 dark:text-slate-100 flex-1 leading-tight pr-4">
                  {item.title}
                </h3>
                <SentimentBadge sentiment={item.sentiment} />
              </div>

              <p className="text-slate-700 dark:text-slate-300 mb-4 leading-relaxed">
                {expandedNews.has(item.id) ? item.content || item.summary : item.summary}
              </p>

              {(item.content && item.content !== item.summary) && (
                <button
                  onClick={() => handleToggleExpansion(item.id)}
                  className="flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium mb-4 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
                  aria-expanded={expandedNews.has(item.id)}
                  aria-controls={`news-content-${item.id}`}
                >
                  {expandedNews.has(item.id) ? (
                    <>
                      <ChevronUp className="w-4 h-4" />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      Read full article
                    </>
                  )}
                </button>
              )}

              <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-6 text-sm text-slate-500 dark:text-slate-400">
                  {item.source && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Source:</span>
                      <span className="bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded-md">{item.source}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    <time dateTime={item.published_at}>
                      {formatDateTime(item.published_at)}
                    </time>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Relevance</div>
                    <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                      {(item.relevance_score * 100).toFixed(0)}%
                    </div>
                  </div>
                  {item.citations && item.citations.length > 0 && (
                    <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-700">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  )
})

NewsFeed.displayName = 'NewsFeed'