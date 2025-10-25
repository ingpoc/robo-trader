import React from 'react'
import { ClaudeIcon } from './icons/ClaudeIcon'
import { useClaudeStatus } from '@/hooks/useClaudeStatus'
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip'

export function ClaudeStatusIndicator() {
  const { status, message, currentTask } = useClaudeStatus()

  const getStatusConfig = () => {
    switch (status) {
      case 'unavailable':
        return {
          color: 'red' as const,
          bgColor: 'bg-red-50 dark:bg-red-950/20',
          borderColor: 'border-red-200 dark:border-red-800',
          textColor: 'text-red-700 dark:text-red-300',
          statusDot: 'bg-red-500',
          animate: false,
          label: 'Unavailable',
        }
      case 'idle':
        return {
          color: 'orange' as const,
          bgColor: 'bg-orange-50 dark:bg-orange-950/20',
          borderColor: 'border-orange-200 dark:border-orange-800',
          textColor: 'text-orange-700 dark:text-orange-300',
          statusDot: 'bg-orange-500',
          animate: false,
          label: 'Ready',
        }
      case 'analyzing':
        return {
          color: 'orange' as const,
          bgColor: 'bg-orange-50 dark:bg-orange-950/20',
          borderColor: 'border-orange-200 dark:border-orange-800',
          textColor: 'text-orange-700 dark:text-orange-300',
          statusDot: 'bg-orange-500 animate-pulse',
          animate: true,
          label: 'Analyzing',
        }
      default:
        return {
          color: 'gray' as const,
          bgColor: 'bg-gray-50 dark:bg-gray-950/20',
          borderColor: 'border-gray-200 dark:border-gray-800',
          textColor: 'text-gray-700 dark:text-gray-300',
          statusDot: 'bg-gray-500',
          animate: false,
          label: 'Unknown',
        }
    }
  }

  const config = getStatusConfig()

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`
            fixed bottom-4 left-4 z-50
            flex items-center gap-3 px-4 py-3
            rounded-full shadow-lg border-2
            ${config.bgColor} ${config.borderColor}
            transition-all duration-300 hover:shadow-xl hover:scale-105
            cursor-pointer
          `}
          role="status"
          aria-label={`Claude status: ${config.label}`}
        >
          {/* Claude Icon */}
          <div className="relative">
            <ClaudeIcon color={config.color} animate={config.animate} className="w-6 h-6" />
            {/* Status dot indicator */}
            <div
              className={`
                absolute -top-1 -right-1 w-3 h-3 rounded-full
                ${config.statusDot}
                ring-2 ring-white dark:ring-gray-900
              `}
              aria-hidden="true"
            />
          </div>

          {/* Status text */}
          <div className="flex flex-col">
            <span className={`text-sm font-bold ${config.textColor}`}>
              Claude
            </span>
            <span className={`text-xs ${config.textColor} opacity-80`}>
              {config.label}
            </span>
          </div>

          {/* Analyzing animation ripple effect */}
          {status === 'analyzing' && (
            <div className="absolute inset-0 rounded-full">
              <span className="absolute inset-0 rounded-full bg-orange-400 opacity-20 animate-ping" />
            </div>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${config.statusDot}`} />
            <span className="font-semibold">{config.label}</span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {message}
          </p>
          {currentTask && (
            <p className="text-xs text-gray-500 dark:text-gray-500 italic">
              Task: {currentTask}
            </p>
          )}
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500">
            <p><span className="font-semibold text-red-500">●</span> Unavailable: Not connected</p>
            <p><span className="font-semibold text-orange-500">●</span> Ready: Connected, idle</p>
            <p><span className="font-semibold text-orange-500 animate-pulse">●</span> Analyzing: Processing data</p>
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  )
}
