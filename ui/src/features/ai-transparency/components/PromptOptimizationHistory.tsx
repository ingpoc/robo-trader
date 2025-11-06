import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { ChevronDown, ChevronUp, Eye, TrendingUp, AlertTriangle, Info } from 'lucide-react'

interface OptimizationAttempt {
  attempt_number: number
  prompt_text: string
  data_received: string
  quality_score: number
  claude_analysis: string
  missing_elements: Array<{ element: string; description: string; importance: string }>
  redundant_elements: string[]
  optimization_time_ms?: number
  created_at: string
}

interface PromptDetails {
  prompt_id: string
  data_type: string
  original_prompt: string
  attempts: OptimizationAttempt[]
  total_attempts: number
}

interface PromptOptimizationHistoryProps {
  promptId?: string
}

export const PromptOptimizationHistory: React.FC<PromptOptimizationHistoryProps> = ({ promptId }) => {
  const [promptDetails, setPromptDetails] = useState<PromptDetails | null>(null)
  const [expandedAttempts, setExpandedAttempts] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (promptId) {
      fetchPromptDetails(promptId)
    }
  }, [promptId])

  const fetchPromptDetails = async (id: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/prompts/attempts/${id}`)
      if (!response.ok) throw new Error('Failed to fetch prompt details')

      const data = await response.json()
      setPromptDetails(data)
    } catch (error) {
      console.error('Failed to load prompt details:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleAttempt = (attemptNumber: number) => {
    const newExpanded = new Set(expandedAttempts)
    if (newExpanded.has(attemptNumber)) {
      newExpanded.delete(attemptNumber)
    } else {
      newExpanded.add(attemptNumber)
    }
    setExpandedAttempts(newExpanded)
  }

  const getQualityColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getQualityBadgeVariant = (score: number) => {
    if (score >= 8) return 'default'
    if (score >= 6) return 'secondary'
    return 'destructive'
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">Loading optimization details...</p>
        </CardContent>
      </Card>
    )
  }

  if (!promptDetails) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">Select a prompt to view optimization details</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            Optimization Overview
          </CardTitle>
          <CardDescription>
            How Claude iteratively improved this {promptDetails.data_type} prompt
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Data Type</p>
              <p className="font-semibold capitalize">{promptDetails.data_type}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Total Attempts</p>
              <p className="font-semibold">{promptDetails.total_attempts}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Final Quality</p>
              <p className={`font-semibold text-lg ${getQualityColor(promptDetails.attempts[promptDetails.attempts.length - 1]?.quality_score || 0)}`}>
                {promptDetails.attempts[promptDetails.attempts.length - 1]?.quality_score.toFixed(1)}/10
              </p>
            </div>
          </div>

          {/* Original Prompt */}
          <div>
            <h4 className="font-semibold mb-2">Original Prompt</h4>
            <div className="bg-muted/30 p-4 rounded-lg text-sm font-mono">
              {promptDetails.original_prompt}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Optimization Attempts Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Optimization Timeline</CardTitle>
          <CardDescription>
            Step-by-step improvements made by Claude
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {promptDetails.attempts.map((attempt, index) => {
              const isExpanded = expandedAttempts.has(attempt.attempt_number)
              const isFirstAttempt = index === 0
              const isLastAttempt = index === promptDetails.attempts.length - 1
              const previousScore = index > 0 ? promptDetails.attempts[index - 1].quality_score : 0
              const improvement = index > 0 ? attempt.quality_score - previousScore : 0

              return (
                <div
                  key={attempt.attempt_number}
                  className={`border rounded-lg ${isLastAttempt ? 'border-primary' : ''}`}
                >
                  {/* Attempt Header */}
                  <div
                    className="p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                    onClick={() => toggleAttempt(attempt.attempt_number)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge variant="tertiary">
                          Attempt {attempt.attempt_number}
                        </Badge>
                        <Badge variant={getQualityBadgeVariant(attempt.quality_score) as any}>
                          Quality: {attempt.quality_score.toFixed(1)}/10
                        </Badge>
                        {improvement > 0 && (
                          <Badge variant="default" className="bg-green-600">
                            <TrendingUp className="h-3 w-3 mr-1" />
                            +{improvement.toFixed(1)}
                          </Badge>
                        )}
                        {improvement < 0 && (
                          <Badge variant="destructive">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            {improvement.toFixed(1)}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {attempt.optimization_time_ms && (
                          <span className="text-sm text-muted-foreground">
                            {attempt.optimization_time_ms}ms
                          </span>
                        )}
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="px-4 pb-4 space-y-4">
                      {/* Claude's Analysis */}
                      {attempt.claude_analysis && (
                        <div>
                          <h5 className="font-semibold text-sm mb-2">Claude's Analysis:</h5>
                          <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded text-sm">
                            {attempt.claude_analysis}
                          </div>
                        </div>
                      )}

                      {/* Missing Elements */}
                      {attempt.missing_elements && attempt.missing_elements.length > 0 && (
                        <div>
                          <h5 className="font-semibold text-sm mb-2 text-amber-600">
                            Missing Elements:
                          </h5>
                          <div className="space-y-2">
                            {attempt.missing_elements.map((element, i) => (
                              <div key={i} className="bg-amber-50 dark:bg-amber-950 p-3 rounded text-sm">
                                <p className="font-medium">{element.element}</p>
                                <p className="text-muted-foreground text-xs mt-1">
                                  {element.description}
                                </p>
                                {element.importance && (
                                  <Badge variant="tertiary" className="mt-2 text-xs">
                                    {element.importance}
                                  </Badge>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Redundant Elements */}
                      {attempt.redundant_elements && attempt.redundant_elements.length > 0 && (
                        <div>
                          <h5 className="font-semibold text-sm mb-2 text-red-600">
                            Redundant Elements:
                          </h5>
                          <div className="flex flex-wrap gap-2">
                            {attempt.redundant_elements.map((element, i) => (
                              <Badge key={i} variant="tertiary" className="bg-red-50 dark:bg-red-950">
                                {element}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Prompt Used */}
                      <div>
                        <h5 className="font-semibold text-sm mb-2">Prompt Used:</h5>
                        <div className="bg-muted/30 p-3 rounded text-xs font-mono max-h-32 overflow-y-auto">
                          {attempt.prompt_text}
                        </div>
                      </div>

                      {/* Data Preview */}
                      <div>
                        <h5 className="font-semibold text-sm mb-2">Data Received (Preview):</h5>
                        <div className="bg-muted/30 p-3 rounded text-xs font-mono max-h-32 overflow-y-auto">
                          {attempt.data_received}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Final Result Summary */}
      {promptDetails.attempts.length > 1 && (
        <Card className="border-green-200 bg-green-50 dark:bg-green-950">
          <CardHeader>
            <CardTitle className="text-green-700 dark:text-green-300">
              Optimization Success
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm">
                Claude successfully improved this prompt through {promptDetails.total_attempts} iterations:
              </p>
              <ul className="text-sm space-y-1 ml-4">
                <li>
                  <strong>Initial Quality:</strong> {promptDetails.attempts[0].quality_score.toFixed(1)}/10
                </li>
                <li>
                  <strong>Final Quality:</strong> {promptDetails.attempts[promptDetails.attempts.length - 1].quality_score.toFixed(1)}/10
                </li>
                <li>
                  <strong>Total Improvement:</strong>{' '}
                  <span className="text-green-600 dark:text-green-400 font-semibold">
                    +{(promptDetails.attempts[promptDetails.attempts.length - 1].quality_score - promptDetails.attempts[0].quality_score).toFixed(1)} points
                  </span>
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
