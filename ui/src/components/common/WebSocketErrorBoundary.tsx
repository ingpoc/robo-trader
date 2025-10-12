import React from 'react'
import { Button } from '@/components/ui/Button'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class WebSocketErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('WebSocket Error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message || 'Unknown error'
      const isWebSocketError = errorMessage.includes('WebSocket') || errorMessage.includes('connection')

      return (
        <div className="flex items-center justify-center h-screen p-4">
          <div className="max-w-md p-6 bg-red-50 border border-red-200 rounded-lg">
            <h2 className="text-lg font-semibold text-red-800 mb-2">
              {isWebSocketError ? 'Connection Error' : 'Application Error'}
            </h2>
            <p className="text-sm text-red-600 mb-4">
              {isWebSocketError
                ? 'Unable to establish WebSocket connection. Please check your internet connection.'
                : 'An unexpected error occurred in the application. Please reload to continue.'
              }
            </p>
            {process.env.NODE_ENV === 'development' && (
              <details className="mb-4">
                <summary className="text-xs text-red-700 cursor-pointer">Error Details (Development)</summary>
                <pre className="text-xs text-red-800 mt-2 p-2 bg-red-100 rounded overflow-auto">
                  {errorMessage}
                </pre>
              </details>
            )}
            <Button onClick={() => window.location.reload()}>
              Reload Application
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
