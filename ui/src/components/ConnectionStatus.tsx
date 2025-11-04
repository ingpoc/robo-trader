import React from 'react'
import { useSystemStatusStore } from '@/stores/systemStatusStore'

export function ConnectionStatus() {
  const isConnected = useSystemStatusStore((state) => state.isConnected)
  const connectionInfo = useSystemStatusStore((state) => state.connectionInfo)

  // Convert connection state to backendStatus equivalent
  const getBackendStatus = () => {
    if (!connectionInfo) return 'unknown'

    switch (connectionInfo.state) {
      case 'connected':
        return 'connected'
      case 'connecting':
        return 'connecting'
      case 'closing':
      case 'closed':
        return 'disconnected'
      default:
        return isConnected ? 'connected' : 'disconnected'
    }
  }

  const backendStatus = getBackendStatus()

  const getStatusInfo = () => {
    switch (backendStatus) {
      case 'unknown':
        return {
          color: 'text-warmgray-500',
          bgColor: 'bg-warmgray-100',
          text: 'Checking...',
          icon: '⏳'
        }
      case 'connecting':
        return {
          color: 'text-copper-600',
          bgColor: 'bg-copper-100',
          text: 'Connecting...',
          icon: '🔄'
        }
      case 'connected':
        return {
          color: 'text-emerald-600',
          bgColor: 'bg-emerald-100',
          text: 'Connected',
          icon: '🟢'
        }
      case 'disconnected':
        return {
          color: 'text-rose-600',
          bgColor: 'bg-rose-100',
          text: 'Disconnected',
          icon: '🔴'
        }
      case 'error':
        return {
          color: 'text-rose-600',
          bgColor: 'bg-rose-100',
          text: 'Connection Error',
          icon: '❌'
        }
      default:
        return {
          color: 'text-warmgray-500',
          bgColor: 'bg-warmgray-100',
          text: 'Unknown',
          icon: '❓'
        }
    }
  }

  const statusInfo = getStatusInfo()

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${statusInfo.color} ${statusInfo.bgColor}`}>
      <span className="text-base">{statusInfo.icon}</span>
      <span>Backend: {statusInfo.text}</span>
    </div>
  )
}