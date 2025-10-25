import React from 'react'

interface ClaudeIconProps {
  className?: string
  color?: 'red' | 'orange' | 'gray'
  animate?: boolean
}

export function ClaudeIcon({ className = '', color = 'orange', animate = false }: ClaudeIconProps) {
  const colors = {
    red: '#DC2626', // Red-600
    orange: '#EA580C', // Claude's signature orange (Orange-600)
    gray: '#9CA3AF', // Gray-400
  }

  const fillColor = colors[color]

  return (
    <svg
      className={`${className} ${animate ? 'animate-pulse' : ''}`}
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Claude AI Status"
    >
      {/* Claude-inspired abstract brain/neural network design */}
      <path
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
        fill={fillColor}
        opacity="0.1"
      />
      <path
        d="M12 4c-4.41 0-8 3.59-8 8s3.59 8 8 8 8-3.59 8-8-3.59-8-8-8zm0 14c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6z"
        fill={fillColor}
        opacity="0.3"
      />
      {/* Central neural node */}
      <circle cx="12" cy="12" r="2.5" fill={fillColor} />
      {/* Neural connections */}
      <circle cx="8" cy="8" r="1.5" fill={fillColor} opacity="0.7" />
      <circle cx="16" cy="8" r="1.5" fill={fillColor} opacity="0.7" />
      <circle cx="8" cy="16" r="1.5" fill={fillColor} opacity="0.7" />
      <circle cx="16" cy="16" r="1.5" fill={fillColor} opacity="0.7" />
      {/* Connection lines */}
      <line x1="12" y1="12" x2="8" y2="8" stroke={fillColor} strokeWidth="1.5" opacity="0.5" />
      <line x1="12" y1="12" x2="16" y2="8" stroke={fillColor} strokeWidth="1.5" opacity="0.5" />
      <line x1="12" y1="12" x2="8" y2="16" stroke={fillColor} strokeWidth="1.5" opacity="0.5" />
      <line x1="12" y1="12" x2="16" y2="16" stroke={fillColor} strokeWidth="1.5" opacity="0.5" />
    </svg>
  )
}
