import React, { Component, ErrorInfo, ReactNode } from 'react'
import { logsAPI } from '@/api/endpoints'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to backend
    logsAPI.logError({
      level: 'error',
      message: error.message,
      context: {
        componentStack: errorInfo.componentStack,
        errorBoundary: 'GlobalErrorBoundary',
      },
      stack_trace: error.stack,
    }).catch(logError => {
      console.error('Failed to log error to backend:', logError)
    })

    console.error('Global error caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-warmgray-50">
          <div className="max-w-md w-full bg-white border border-red-200 rounded-lg p-6 shadow-lg">
            <div className="flex items-center mb-4">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3">
                <span className="text-red-600 text-lg">⚠</span>
              </div>
              <h2 className="text-lg font-semibold text-warmgray-900">Something went wrong</h2>
            </div>

            <p className="text-warmgray-600 mb-4">
              An unexpected error occurred. The error has been logged and our team has been notified.
            </p>

            <div className="text-sm text-warmgray-500 mb-4">
              Error: {this.state.error?.message}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-copper-600 text-white rounded hover:bg-copper-700 transition-colors"
              >
                Reload Page
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: undefined })}
                className="px-4 py-2 bg-warmgray-200 text-warmgray-800 rounded hover:bg-warmgray-300 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}