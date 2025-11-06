import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Switch } from '@/components/ui/Switch'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Cpu, Clock, RefreshCw, Eye, Play, Loader2, Save } from 'lucide-react'
import type { BackgroundTaskConfig } from '@/types/api'
import type { PromptConfig } from '../types'
import { getFrequencyDisplay, getPriorityColor, formatTaskName } from '../utils'

interface BackgroundTasksConfigProps {
  backgroundTasks: Record<string, BackgroundTaskConfig>
  prompts: Record<string, PromptConfig>
  visiblePrompts: Set<string>
  editingPrompts: Set<string>
  executingTasks: Set<string>
  isLoading: boolean
  isSaving: boolean
  onUpdateTask: (taskName: string, field: keyof BackgroundTaskConfig, value: any) => void
  onExecuteTask: (taskName: string) => void
  onTogglePrompt: (taskName: string) => void
  onTogglePromptEditing: (taskName: string) => void
  onSavePrompt: (taskName: string) => void
  onUpdatePrompt: (taskName: string, field: 'content' | 'description', value: string) => void
}

export const BackgroundTasksConfig: React.FC<BackgroundTasksConfigProps> = ({
  backgroundTasks,
  prompts,
  visiblePrompts,
  editingPrompts,
  executingTasks,
  isLoading,
  isSaving,
  onUpdateTask,
  onExecuteTask,
  onTogglePrompt,
  onTogglePromptEditing,
  onSavePrompt,
  onUpdatePrompt,
}) => {
  if (isLoading) {
    return (
      <div className="text-center py-8">
        <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-gray-400" />
        <p className="text-gray-600">Loading configuration...</p>
      </div>
    )
  }

  if (Object.keys(backgroundTasks).length === 0) {
    return (
      <div className="text-center py-8">
        <Cpu className="w-8 h-8 mx-auto mb-3 text-gray-400" />
        <p className="text-gray-600">No background tasks configured</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Alert>
        <AlertDescription>
          Configure background scheduler tasks that process data automatically.
          Set frequency, Claude usage, and priority for each task.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4">
        {Object.entries(backgroundTasks).map(([taskName, config]) => (
          <Card key={taskName}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{formatTaskName(taskName)}</CardTitle>
                  <CardDescription>Background scheduler processor</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={getPriorityColor(config.priority)}>
                    {config.priority} priority
                  </Badge>
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={(checked) => onUpdateTask(taskName, 'enabled', checked)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={`${taskName}-frequency`}>Frequency</Label>
                  <div className="flex gap-2">
                    <Input
                      id={`${taskName}-frequency`}
                      type="number"
                      min="1"
                      value={config.frequency}
                      onChange={(e) => onUpdateTask(taskName, 'frequency', parseInt(e.target.value))}
                      className="w-24"
                      disabled={!config.enabled}
                    />
                    <Select
                      value={config.frequencyUnit}
                      onValueChange={(value) => onUpdateTask(taskName, 'frequencyUnit', value)}
                      disabled={!config.enabled}
                    >
                      <SelectTrigger className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="minutes">Minutes</SelectItem>
                        <SelectItem value="hours">Hours</SelectItem>
                        <SelectItem value="days">Days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select
                    value={config.priority}
                    onValueChange={(value) => onUpdateTask(taskName, 'priority', value)}
                    disabled={!config.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${taskName}-claude`}>Claude AI Usage</Label>
                  <div className="flex items-center gap-2">
                    <Switch
                      id={`${taskName}-claude`}
                      checked={config.useClaude}
                      onCheckedChange={(checked) => onUpdateTask(taskName, 'useClaude', checked)}
                      disabled={!config.enabled}
                    />
                    <span className="text-sm text-gray-600">
                      {config.useClaude ? 'AI analysis enabled' : 'Basic processing only'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-sm text-gray-600">
                <Clock className="inline w-3 h-3 mr-1" />
                Runs {getFrequencyDisplay(config.frequency, config.frequencyUnit)} when enabled
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t space-y-2">
                <div className="flex gap-2">
                  <Button
                    variant="tertiary"
                    size="sm"
                    onClick={() => onExecuteTask(taskName)}
                    disabled={executingTasks.has(taskName) || !config.enabled}
                    className="flex-1"
                  >
                    {executingTasks.has(taskName) ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Run Now
                      </>
                    )}
                  </Button>
                  <Button
                    variant="tertiary"
                    size="sm"
                    onClick={() => onTogglePrompt(taskName)}
                    className="flex-1"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    {visiblePrompts.has(taskName) ? 'Hide Prompt' : 'View/Edit Prompt'}
                  </Button>
                </div>
              </div>

              {/* Prompt Display/Edit */}
              {visiblePrompts.has(taskName) && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg border space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">Perplexity API Prompt:</h4>
                    <Button
                      variant="tertiary"
                      size="sm"
                      onClick={() => onTogglePromptEditing(taskName)}
                    >
                      {editingPrompts.has(taskName) ? 'Cancel Edit' : 'Edit Prompt'}
                    </Button>
                  </div>

                  {editingPrompts.has(taskName) ? (
                    <>
                      {/* Description Field */}
                      <div className="space-y-2">
                        <Label htmlFor={`${taskName}-description`} className="text-xs font-medium">
                          Description
                        </Label>
                        <Input
                          id={`${taskName}-description`}
                          value={prompts[taskName]?.description || ''}
                          onChange={(e) => onUpdatePrompt(taskName, 'description', e.target.value)}
                          placeholder="Brief description of this prompt's purpose"
                          className="text-sm"
                        />
                      </div>

                      {/* Content Field */}
                      <div className="space-y-2">
                        <Label htmlFor={`${taskName}-content`} className="text-xs font-medium">
                          Prompt Content
                        </Label>
                        <Textarea
                          id={`${taskName}-content`}
                          value={prompts[taskName]?.content || ''}
                          onChange={(e) => onUpdatePrompt(taskName, 'content', e.target.value)}
                          placeholder="Enter the AI prompt content..."
                          className="min-h-48 font-mono text-xs"
                        />
                      </div>

                      {/* Save/Cancel Buttons */}
                      <div className="flex gap-2 pt-2">
                        <Button
                          size="sm"
                          onClick={() => onSavePrompt(taskName)}
                          disabled={isSaving}
                          className="flex-1"
                        >
                          <Save className="w-4 h-4 mr-2" />
                          {isSaving ? 'Saving...' : 'Save Prompt'}
                        </Button>
                        <Button
                          variant="tertiary"
                          size="sm"
                          onClick={() => onTogglePromptEditing(taskName)}
                          className="flex-1"
                        >
                          Cancel
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="text-xs text-gray-600">
                        <strong>Description:</strong> {prompts[taskName]?.description || 'No description available'}
                      </div>
                      <div className="text-xs text-gray-600">
                        <strong>Last Updated:</strong> {prompts[taskName]?.updated_at ? new Date(prompts[taskName].updated_at).toLocaleString() : 'Never'}
                      </div>
                      <div>
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-white p-3 rounded border max-h-48 overflow-y-auto">
                          {prompts[taskName]?.content || 'Loading prompt...'}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
