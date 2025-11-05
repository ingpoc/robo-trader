/**
 * Utility functions for Configuration Feature
 */

export const getFrequencyDisplay = (frequency: number, unit: string): string => {
  if (frequency === 1) {
    return `1 ${unit.slice(0, -1)}`
  }
  return `${frequency} ${unit}`
}

export const getPriorityColor = (priority: string): 'destructive' | 'default' | 'secondary' => {
  switch (priority) {
    case 'high': return 'destructive'
    case 'medium': return 'default'
    case 'low': return 'secondary'
    default: return 'default'
  }
}

export const getScopeColor = (scope: string): 'default' | 'secondary' | 'outline' => {
  switch (scope) {
    case 'portfolio': return 'default'
    case 'market': return 'secondary'
    case 'watchlist': return 'outline'
    default: return 'default'
  }
}

export const formatTaskName = (taskName: string): string => {
  return taskName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Simple logger for client-side
export const logger = {
  info: (message: string) => console.log(`[Configuration] ${message}`),
  error: (message: string) => console.error(`[Configuration] ${message}`)
}
