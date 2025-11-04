import React from 'react'
import { useClaudeStatus } from '@/hooks/useClaudeStatus'

export function ClaudeStatusIndicator() {
   const { status } = useClaudeStatus()

  const getStatusConfig = () => {
    switch (status) {
      case 'unavailable':
        return {
          label: 'Offline',
          description: 'Claude AI agent is not configured or disconnected',
        }
      case 'authenticated':
        return {
          label: 'Authenticated',
          description: 'CLI is authenticated but SDK not connected',
        }
      case 'idle':
        return {
          label: 'Available',
          description: 'Claude AI agent is connected and ready',
        }
      case 'connected/idle':
        return {
          label: 'SDK Connected',
          description: 'Claude SDK is actively connected to CLI process',
        }
      case 'analyzing':
        return {
          label: 'Analyzing',
          description: 'Claude is analyzing market data and executing strategies',
        }
      default:
        return {
          label: 'Unknown',
          description: 'Claude status is unknown',
        }
    }
  }

  const getClaudeIcon = () => {
    // Main Claude icon that changes based on status
    // Using actual Claude images for online/thinking states
    switch (status) {
      case 'unavailable':
        // Offline - Grayed out circle
        return (
          <svg
            className="w-6 h-6 text-gray-400"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Claude circle - grayed out when offline */}
            <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.4" />
          </svg>
        )
      case 'authenticated':
        // CLI authenticated but no SDK connection - Claude online image
        return (
          <img
            src="/Claude_online.svg"
            alt="Claude Authenticated"
            className="w-6 h-6 text-green-500"
          />
        )
      case 'idle':
        // Available/Connected - Claude online image
        return (
          <img
            src="/Claude_online.svg"
            alt="Claude Online"
            className="w-6 h-6 text-green-500"
          />
        )
      case 'connected/idle':
        // SDK actively connected - Claude online image with green tint
        return (
          <img
            src="/Claude_online.svg"
            alt="Claude SDK Connected"
            className="w-6 h-6 text-green-600"
          />
        )
      case 'analyzing':
        // Analyzing/Thinking - Claude online image with pulse animation
        return (
          <img
            src="/Claude_online.svg"
            alt="Claude Analyzing"
            className="w-6 h-6 text-orange-500 animate-pulse"
          />
        )
      default:
        return (
          <svg
            className="w-6 h-6 text-gray-400"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.4" />
          </svg>
        )
    }
  }

  const getWebSocketIcon = () => {
    // WiFi-style icon for WebSocket status
    switch (wsStatus) {
      case 'connected':
        return (
          <svg
            className="w-5 h-5 text-green-500"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* WiFi connected - all bars filled */}
            <path d="M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm0-5c2.8 0 5.3 1 7.3 2.8l1.4-1.4C17.7 12.3 15 11 12 11s-5.7 1.3-7.7 3.4l1.4 1.4c2-1.8 4.5-2.8 7.3-2.8zm0-5C8.3 8 5.1 9.1 2.7 10.9l1.4 1.4c2-1.5 4.5-2.3 7.9-2.3s5.9.8 7.9 2.3l1.4-1.4C18.9 9.1 15.7 8 12 8z" />
          </svg>
        )
      case 'connecting':
        return (
          <svg
            className="w-5 h-5 text-yellow-500 animate-pulse"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* WiFi connecting - partial bars */}
            <path d="M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm0-5c2.8 0 5.3 1 7.3 2.8l1.4-1.4C17.7 12.3 15 11 12 11s-5.7 1.3-7.7 3.4l1.4 1.4c2-1.8 4.5-2.8 7.3-2.8z" opacity="0.5" />
            <path d="M12 8c2.8 0 5.3 1 7.3 2.8l1.4-1.4C17.7 6.3 15 5 12 5s-5.7 1.3-7.7 3.4l1.4 1.4c2-1.8 4.5-2.8 7.3-2.8z" />
          </svg>
        )
      case 'disconnected':
        return (
          <svg
            className="w-5 h-5 text-red-500"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* WiFi disconnected - X mark */}
            <path d="M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm0-5c2.8 0 5.3 1 7.3 2.8l1.4-1.4C17.7 12.3 15 11 12 11s-5.7 1.3-7.7 3.4l1.4 1.4c2-1.8 4.5-2.8 7.3-2.8z" opacity="0.3" />
            <path d="M1 9l2 2c2.97-2.97 6.94-4.71 10.99-4.71 4.05 0 8.02 1.74 10.99 4.71l2-2C20.55 5.08 16.41 3 12 3 7.59 3 3.45 5.08 1 9zm8 8l3 3 3-3c1.65-1.66 2.57-3.92 2.57-6.29 0-2.37-.92-4.63-2.57-6.29L12 2 9.71 4.29C8.06 5.92 7.14 8.17 7.14 10.54c0 2.37.92 4.63 2.57 6.29L12 19l-3-3z" />
          </svg>
        )
      default:
        return (
          <svg
            className="w-5 h-5 text-gray-400"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2z" opacity="0.3" />
          </svg>
        )
    }
  }

  return (
    <div className="flex items-center justify-center">
      {getClaudeIcon()}
    </div>
  )
}
