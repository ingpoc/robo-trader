import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Eye, TrendingUp, AlertTriangle, CheckCircle, Clock, Zap, Database, RefreshCw } from 'lucide-react'

interface DataTypeMetrics {
  data_type: string
  quality_score: number
  optimization_attempts: number
  optimization_triggered: boolean
  prompt_optimized: boolean
  last_updated?: string
}

interface OptimizationHistory {
  prompt_id: string
  quality_score: number
  optimization_version: number
  claude_feedback: string
  usage_count: number
  created_at: string
}

interface DataPipelineAnalysisProps {
  isLoading?: boolean
}

export const DataPipelineAnalysis: React.FC<DataPipelineAnalysisProps> = ({ isLoading = false }) => {
  const [pipelineData, setPipelineData] = useState<Record<string, DataTypeMetrics> | null>(null)
  const [selectedDataType, setSelectedDataType] = useState('earnings')
  const [optimizationHistory, setOptimizationHistory] = useState<OptimizationHistory[]>([])
  const [performanceSummary, setPerformanceSummary] = useState<any>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const dataTypes = [
    { id: 'earnings', name: 'Earnings', icon: '📊', color: 'blue' },
    { id: 'news', name: 'News', icon: '📰', color: 'green' },
    { id: 'fundamentals', name: 'Fundamentals', icon: '💹', color: 'purple' },
    { id: 'metrics', name: 'Technical Metrics', icon: '📈', color: 'orange' }
  ]

  useEffect(() => {
    fetchPipelineData()
    fetchPerformanceSummary()

    // Poll for updates every 30 seconds
    const interval = setInterval(() => {
      fetchPipelineData()
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedDataType) {
      fetchOptimizationHistory(selectedDataType)
    }
  }, [selectedDataType])

  const fetchPipelineData = async () => {
    try {
      // Fetch quality summary from current session or most recent
      const response = await fetch('/api/claude/transparency/data-quality-summary')
      if (!response.ok) throw new Error('Failed to fetch pipeline data')

      const data = await response.json()
      setPipelineData(data.quality_summary || {})
    } catch (error) {
      console.error('Failed to load pipeline data:', error)
    }
  }

  const fetchOptimizationHistory = async (dataType: string) => {
    try {
      const response = await fetch(`/api/prompts/optimization-history/${dataType}?limit=10`)
      if (!response.ok) throw new Error('Failed to fetch optimization history')

      const data = await response.json()
      setOptimizationHistory(data.history || [])
    } catch (error) {
      console.error('Failed to load optimization history:', error)
    }
  }

  const fetchPerformanceSummary = async () => {
    try {
      const response = await fetch('/api/prompts/performance-summary?days=30')
      if (!response.ok) throw new Error('Failed to fetch performance summary')

      const data = await response.json()
      setPerformanceSummary(data)
    } catch (error) {
      console.error('Failed to load performance summary:', error)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await Promise.all([
      fetchPipelineData(),
      fetchOptimizationHistory(selectedDataType),
      fetchPerformanceSummary()
    ])
    setIsRefreshing(false)
  }

  const getQualityColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getQualityBadge = (score: number) => {
    if (score >= 8) return { label: 'Excellent', variant: 'default' as const, className: 'bg-green-600' }
    if (score >= 6) return { label: 'Good', variant: 'secondary' as const, className: 'bg-yellow-600' }
    return { label: 'Needs Improvement', variant: 'destructive' as const }
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Data Pipeline Analysis</h2>
          <p className="text-sm text-muted-foreground">
            Real-time quality monitoring of Claude's optimized data fetching
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={isRefreshing}
          variant="tertiary"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Performance Summary Cards */}
      {performanceSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Quality Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceSummary.overall.avg_quality.toFixed(1)}/10
              </div>
              <Progress
                value={performanceSummary.overall.avg_quality * 10}
                className="mt-2"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Optimizations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceSummary.overall.total_prompts}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Last 30 days
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Best Quality
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {performanceSummary.overall.best_quality.toFixed(1)}/10
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Peak performance
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceSummary.overall.total_usage}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Prompts used
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Current Data Quality by Type */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Current Data Quality
          </CardTitle>
          <CardDescription>
            Real-time quality scores for each data type
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {dataTypes.map((type) => {
              const metrics = pipelineData?.[type.id]
              const qualityBadge = metrics ? getQualityBadge(metrics.quality_score) : null

              return (
                <div
                  key={type.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedDataType === type.id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => setSelectedDataType(type.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{type.icon}</span>
                    {metrics?.prompt_optimized && (
                      <Badge variant="tertiary" className="text-xs">
                        <Zap className="h-3 w-3 mr-1" />
                        Optimized
                      </Badge>
                    )}
                  </div>

                  <h3 className="font-semibold mb-1">{type.name}</h3>

                  {metrics ? (
                    <>
                      <div className={`text-2xl font-bold ${getQualityColor(metrics.quality_score)}`}>
                        {metrics.quality_score.toFixed(1)}/10
                      </div>

                      <Progress
                        value={metrics.quality_score * 10}
                        className="mt-2 mb-2"
                      />

                      {qualityBadge && (
                        <Badge
                          variant={qualityBadge.variant}
                          className={qualityBadge.className}
                        >
                          {qualityBadge.label}
                        </Badge>
                      )}

                      {metrics.optimization_triggered && (
                        <p className="text-xs text-muted-foreground mt-2">
                          {metrics.optimization_attempts} optimization{metrics.optimization_attempts !== 1 ? 's' : ''}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">No data yet</p>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Optimization History for Selected Type */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Optimization History - {dataTypes.find(t => t.id === selectedDataType)?.name}
          </CardTitle>
          <CardDescription>
            Track how Claude improved prompts over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          {optimizationHistory.length > 0 ? (
            <div className="space-y-4">
              {optimizationHistory.map((item, index) => (
                <div
                  key={item.prompt_id}
                  className="p-4 border rounded-lg space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="tertiary">
                        Version {item.optimization_version}
                      </Badge>
                      <span className={`font-semibold ${getQualityColor(item.quality_score)}`}>
                        Quality: {item.quality_score.toFixed(1)}/10
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Used {item.usage_count}x</span>
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {item.claude_feedback && (
                    <div className="text-sm bg-muted/30 p-3 rounded">
                      <p className="font-medium mb-1">Claude's Feedback:</p>
                      <p className="text-muted-foreground">{item.claude_feedback}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Database className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>No optimization history for this data type yet</p>
              <p className="text-sm mt-1">History will appear as Claude optimizes prompts</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
