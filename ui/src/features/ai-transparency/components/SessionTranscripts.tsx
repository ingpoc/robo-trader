/**
 * Session Transcripts Component
 * Displays Claude session logs and full transcripts
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonCard } from '@/components/common/SkeletonLoader'
import { Clock, Zap, Target } from 'lucide-react'

export interface SessionTranscriptsProps {
  sessions: any[]
  isLoading: boolean
}

export const SessionTranscripts: React.FC<SessionTranscriptsProps> = ({ sessions, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4">
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} className="h-40" />
        ))}
      </div>
    )
  }

  if (!sessions || sessions.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-warmgray-500">No session transcripts available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {sessions.map((session, index) => (
        <Card key={index}>
          <CardHeader className="pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg">{session.type?.replace(/_/g, ' ').toUpperCase()}</CardTitle>
              <span className="text-sm text-warmgray-600">
                {new Date(session.timestamp).toLocaleDateString()}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-warmgray-500" />
                <div>
                  <p className="text-warmgray-600">Duration</p>
                  <p className="font-semibold">{(session.duration / 60).toFixed(1)}m</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-warmgray-500" />
                <div>
                  <p className="text-warmgray-600">Tokens</p>
                  <p className="font-semibold">{session.tokenInput + session.tokenOutput}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-warmgray-500" />
                <div>
                  <p className="text-warmgray-600">Decisions</p>
                  <p className="font-semibold">{session.decisionsCount}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div>
                  <p className="text-warmgray-600">Trades</p>
                  <p className="font-semibold">{session.tradesExecuted}</p>
                </div>
              </div>
            </div>
            {session.summary && (
              <div className="border-t pt-3">
                <p className="text-sm font-semibold text-warmgray-700">Summary:</p>
                <p className="text-sm text-warmgray-600 mt-2">{session.summary}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default SessionTranscripts
