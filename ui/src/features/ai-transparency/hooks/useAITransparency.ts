/**
 * AI Transparency Hook
 * Aggregates Claude agent decision logs, reflections, and session data
 */

import { useClaudeTransparency } from '@/hooks/useClaudeTransparency'

export const useAITransparency = () => {
  const { tradeLogs, strategyReflections, sessionData, isLoading } = useClaudeTransparency()

  return {
    tradeLogs: tradeLogs || [],
    reflections: strategyReflections || [],
    sessions: sessionData || [],
    isLoading,
  }
}
