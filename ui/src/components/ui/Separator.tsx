import React from 'react'

interface SeparatorProps {
  className?: string
  orientation?: 'horizontal' | 'vertical'
}

export function Separator({ className = '', orientation = 'horizontal' }: SeparatorProps) {
  if (orientation === 'vertical') {
    return (
      <div
        className={`w-px h-full bg-gray-200 dark:bg-gray-700 ${className}`}
        role="separator"
        aria-orientation="vertical"
      />
    )
  }

  return (
    <div
      className={`h-px w-full bg-gray-200 dark:bg-gray-700 ${className}`}
      role="separator"
      aria-orientation="horizontal"
    />
  )
}