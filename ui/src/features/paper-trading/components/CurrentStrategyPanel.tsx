import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Brain, Target, Database, TrendingUp, AlertTriangle, Eye, RefreshCw, CheckCircle } from 'lucide-react'

interface DataQualityMetrics {
  [key: string]: {
    quality_score: number
    optimization_attempts: number
    optimization_triggered: boolean
    prompt_optimized: boolean
  }
}

interface CurrentStrategy {
  strategy_type: string
  focus_areas: string[]
  risk_level: string
  current_analysis?: string
  data_quality: DataQualityMetrics
  last_updated: string
}

interface CurrentStrategyPanelProps {
  accountId: string
  accountType: string
}

export const CurrentStrategyPanel: React.FC<CurrentStrategyPanelProps> = ({
  accountId,
  accountType
}) => {
  const [currentStrategy, setCurrentStrategy] = useState<CurrentStrategy | null>(null)
  const [dataQuality, setDataQuality] = useState<DataQualityMetrics>({})
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    fetchCurrentStrategy()
    fetchDataQuality()

    // Poll for updates every 60 seconds
    const interval = setInterval(() => {
      fetchDataQuality()
    }, 60000)

    return () => clearInterval(interval)
  }, [accountId])

  const fetchCurrentStrategy = async () => {
    setIsLoading(true)
    try {
      // Fetch current strategy from Claude's latest session
      const response = await fetch(`/api/claude/current-strategy/${accountType}`)
      if (!response.ok) throw new Error('Failed to fetch current strategy')

      const data = await response.json()
      setCurrentStrategy(data.strategy)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to load current strategy:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchDataQuality = async () => {
    try {
      // Fetch latest data quality metrics
      const response = await fetch('/api/claude/transparency/data-quality-summary')
      if (!response.ok) throw new Error('Failed to fetch data quality')

      const data = await response.json()
      setDataQuality(data.quality_summary || {})
    } catch (error) {
      console.error('Failed to load data quality:', error)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await Promise.all([fetchCurrentStrategy(), fetchDataQuality()])
    setIsRefreshing(false)
  }

  const getQualityColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getOverallQuality = () => {
    const scores = Object.values(dataQuality).map(d => d.quality_score)
    if (scores.length === 0) return 0
    return scores.reduce((sum, score) => sum + score, 0) / scores.length
  }

  const overallQuality = getOverallQuality()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            <CardTitle>Current Strategy</CardTitle>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        <CardDescription>
          Claude's active trading strategy with data quality indicators
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Data Quality */}
        <div className="p-4 border rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold flex items-center gap-2">
              <Database className="h-4 w-4" />
              Overall Data Quality
            </h4>
            <span className={`text-2xl font-bold ${getQualityColor(overallQuality)}`}>
              {overallQuality.toFixed(1)}/10
            </span>
          </div>
          <Progress value={overallQuality * 10} className="mb-2" />
          <p className="text-xs text-muted-foreground">
            {overallQuality >= 8 && 'Excellent data quality - High confidence trading decisions'}
            {overallQuality >= 6 && overallQuality < 8 && 'Good data quality - Moderate confidence'}
            {overallQuality < 6 && 'Data quality needs improvement - Exercise caution'}
          </p>
        </div>

        {/* Data Quality by Type */}
        <div>
          <h4 className="font-semibold mb-3">Data Source Quality</h4>
          <div className="space-y-3">
            {Object.entries(dataQuality).map(([type, metrics]) => (
              <div key={type} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`font-medium capitalize ${getQualityColor(metrics.quality_score)}`}>
                    {type}
                  </div>
                  {metrics.prompt_optimized && (
                    <Badge variant="outline" className="text-xs">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Optimized
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${getQualityColor(metrics.quality_score)}`}>
                    {metrics.quality_score.toFixed(1)}
                  </span>
                  <div className="w-24">
                    <Progress value={metrics.quality_score * 10} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Current Strategy Details */}
        {currentStrategy && (
          <div>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
              <Target className="h-4 w-4" />
              Strategy Details
            </h4>
            <div className="space-y-3">
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Strategy Type</p>
                <p className="font-medium capitalize">{currentStrategy.strategy_type}</p>
              </div>

              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Risk Level</p>
                <Badge
                  variant={
                    currentStrategy.risk_level === 'high' ? 'destructive' :
                    currentStrategy.risk_level === 'moderate' ? 'secondary' :
                    'default'
                  }
                >
                  {currentStrategy.risk_level}
                </Badge>
              </div>

              {currentStrategy.focus_areas && currentStrategy.focus_areas.length > 0 && (
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground mb-2">Focus Areas</p>
                  <div className="flex flex-wrap gap-2">
                    {currentStrategy.focus_areas.map((area, index) => (
                      <Badge key={index} variant="outline">
                        {area}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {currentStrategy.current_analysis && (
                <div className="p-3 border rounded-lg bg-blue-50 dark:bg-blue-950">
                  <p className="text-sm text-muted-foreground mb-2">Current Market Analysis</p>
                  <p className="text-sm">{currentStrategy.current_analysis}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Data Quality Warning */}
        {overallQuality < 7 && (
          <div className="p-4 border border-amber-500 rounded-lg bg-amber-50 dark:bg-amber-950 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
                Data Quality Alert
              </p>
              <p className="text-sm text-amber-800 dark:text-amber-200">
                Current data quality is below optimal levels. Trading decisions may have lower confidence.
                Claude is working to improve data quality through prompt optimization.
              </p>
            </div>
          </div>
        )}

        {/* Last Updated */}
        {lastUpdated && (
          <div className="text-xs text-muted-foreground text-center">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
