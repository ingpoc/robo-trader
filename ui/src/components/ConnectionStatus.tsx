import React from 'react'
import { useDashboardStore } from '@/store/dashboardStore'

export function ConnectionStatus() {
  const backendStatus = useDashboardStore((state) => state.backendStatus)

  const getStatusInfo = () => {
    switch (backendStatus) {
      case 'unknown':
        return {
          color: 'text-gray-500',
          bgColor: 'bg-gray-100',
          text: 'Checking...',
          icon: '⏳'
        }
      case 'connecting':
        return {
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-100',
          text: 'Connecting...',
          icon: '🔄'
        }
      case 'connected':
        return {
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          text: 'Connected',
          icon: '🟢'
        }
      case 'disconnected':
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          text: 'Disconnected',
          icon: '🔴'
        }
      case 'error':
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          text: 'Connection Error',
          icon: '❌'
        }
      default:
        return {
          color: 'text-gray-500',
          bgColor: 'bg-gray-100',
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