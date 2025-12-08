/**
 * Stock Discovery Card Component
 * Temporary wrapper until full implementation is ready
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Search, RefreshCw, Play, Target } from 'lucide-react'

export const StockDiscoveryCard = () => {
  const [isLoading, setIsLoading] = React.useState(false)

  const handleTriggerDiscovery = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/paper-trading/discovery/trigger-daily', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      console.log('Discovery triggered:', data)
    } catch (error) {
      console.error('Failed to trigger discovery:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="w-5 h-5" />
          Stock Discovery
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          AI-powered stock discovery and watchlist management
        </div>

        <div className="flex items-center justify-between">
          <Badge variant="secondary">Backend Ready</Badge>
          <Button
            onClick={handleTriggerDiscovery}
            disabled={isLoading}
            size="sm"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Trigger Discovery
              </>
            )}
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <Target className="w-8 h-8 mx-auto mb-2 text-blue-600 dark:text-blue-400" />
            <div className="font-medium">Daily Scan</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Market-wide screening
            </div>
          </div>
          <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <Search className="w-8 h-8 mx-auto mb-2 text-green-600 dark:text-green-400" />
            <div className="font-medium">Sector Analysis</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Focused discovery
            </div>
          </div>
          <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <Target className="w-8 h-8 mx-auto mb-2 text-purple-600 dark:text-purple-400" />
            <div className="font-medium">Watchlist</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Track opportunities
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}