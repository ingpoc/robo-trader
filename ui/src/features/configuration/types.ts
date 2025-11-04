/**
 * Shared types for Configuration Feature
 */

import type { BackgroundTaskConfig, AIAgentConfig, GlobalConfig } from '@/types/api'

export interface PromptConfig {
  prompt_name: string
  content: string
  description: string
  created_at: string
  updated_at: string
}

export interface ConfigurationState {
  backgroundTasks: Record<string, BackgroundTaskConfig>
  aiAgents: Record<string, AIAgentConfig>
  globalSettings: GlobalConfig | null
  prompts: Record<string, PromptConfig>
}

export interface LoadingState {
  isLoading: boolean
  isSaving: boolean
  executingTasks: Set<string>
  executingAgents: Set<string>
}

export interface PromptState {
  visiblePrompts: Set<string>
  editingPrompts: Set<string>
}
