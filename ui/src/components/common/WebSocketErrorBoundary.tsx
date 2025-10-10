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
      return (
        <div className="flex items-center justify-center h-screen p-4">
          <div className="max-w-md p-6 bg-red-50 border border-red-200 rounded-lg">
            <h2 className="text-lg font-semibold text-red-800 mb-2">Connection Error</h2>
            <p className="text-sm text-red-600 mb-4">
              Unable to establish WebSocket connection. Please check your internet connection.
            </p>
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
