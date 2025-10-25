/**
 * Agent Card Component
 * Displays agent status and metrics in card format
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { CheckCircle, XCircle, Clock, AlertTriangle, Settings, Activity, Users, TrendingUp } from 'lucide-react'
import type { AgentStatus } from '../types'

export interface AgentCardProps {
  name: string
  status: AgentStatus
  onConfigure: () => void
  isClaudeAgent?: boolean
}

export const AgentCard: React.FC<AgentCardProps> = ({
  name,
  status,
  onConfigure,
  isClaudeAgent = false
}) => {
  const getStatusColor = () => {
    switch (status.status) {
      case 'running':
        return 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-100 border-emerald-300 dark:border-emerald-700'
      case 'error':
        return 'bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-100 border-rose-300 dark:border-rose-700'
      case 'idle':
        return 'bg-warmgray-200 dark:bg-warmgray-700 text-warmgray-700 dark:text-warmgray-300 border-warmgray-300 dark:border-warmgray-600'
      default:
        return 'bg-warmgray-100 dark:bg-warmgray-800 text-warmgray-700 dark:text-warmgray-300 border-warmgray-300 dark:border-warmgray-600'
    }
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'running':
        return <CheckCircle className="w-3 h-3" />
      case 'error':
        return <XCircle className="w-3 h-3" />
      case 'idle':
        return <Clock className="w-3 h-3" />
      default:
        return <AlertTriangle className="w-3 h-3" />
    }
  }

  return (
    <Card
      variant="interactive"
      className={isClaudeAgent ? 'border-copper-200 bg-gradient-to-r from-copper-50/50 to-emerald-50/50' : ''}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg capitalize flex items-center gap-2 text-warmgray-900 dark:text-warmgray-100">
            {isClaudeAgent ? (
              <Activity className="w-5 h-5 text-copper-500" />
            ) : (
              <Users className="w-5 h-5 text-copper-500" />
            )}
            {name.replace(/_/g, ' ')}
            {isClaudeAgent && (
              <span className="text-xs bg-copper-100 text-copper-800 px-2 py-1 rounded-full font-medium">
                AI Learning
              </span>
            )}
          </CardTitle>
          <div
            className={`px-2.5 py-1 text-xs rounded-full flex items-center gap-1 font-semibold border ${getStatusColor()}`}
          >
            {getStatusIcon()}
            {status.status}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="text-sm text-warmgray-600 dark:text-warmgray-400 space-y-1">
          <div>{status.message}</div>

          {/* Basic Metrics */}
          <div className="flex justify-between text-xs text-warmgray-500">
            <span>Tasks: {status.tasks_completed}</span>
            {status.uptime && <span>Uptime: {status.uptime}</span>}
          </div>

          {/* Claude Paper Trader Specific Metrics */}
          {isClaudeAgent && (
            <div className="space-y-1 pt-2 border-t border-warmgray-200 dark:border-warmgray-700">
              <div className="flex justify-between text-xs text-warmgray-500">
                <span className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  Win Rate: {status.win_rate?.toFixed(1)}%
                </span>
                <span>P&L: {status.pnl! >= 0 ? '+' : ''}₹{status.pnl?.toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between text-xs text-warmgray-500">
                <span>Token Usage: {status.tokens_used} / 10,000</span>
              </div>
            </div>
          )}
        </div>

        <Button
          size="sm"
          variant="secondary"
          onClick={onConfigure}
          className="w-full"
          aria-label={`Configure ${name.replace(/_/g, ' ')} agent`}
        >
          <Settings className="w-4 h-4 mr-2" />
          {isClaudeAgent ? 'View Learning' : 'Configure'}
        </Button>
      </CardContent>
    </Card>
  )
}

export default AgentCard
