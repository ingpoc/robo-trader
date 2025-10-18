import React from 'react'
import { cn } from '@/utils/cn'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  variant?: 'base' | 'featured' | 'compact' | 'interactive'
}

export function Card({ className, children, variant = 'base', ...props }: CardProps) {
  const variantStyles = {
    base: 'border-warmgray-300 dark:border-warmgray-700 bg-white/80 dark:bg-warmgray-800/80 shadow-md hover:shadow-lg',
    featured: 'border-l-4 border-l-copper-500 border-warmgray-300 dark:border-warmgray-700 bg-gradient-to-br from-white to-warmgray-50 dark:from-warmgray-800 dark:to-warmgray-900 shadow-lg hover:shadow-xl hover:border-l-copper-600',
    compact: 'border-warmgray-300 dark:border-warmgray-700 bg-white/70 dark:bg-warmgray-800/70 shadow-sm hover:shadow-md',
    interactive: 'border-warmgray-200 dark:border-warmgray-700 bg-white/90 dark:bg-warmgray-800/90 shadow-md hover:shadow-xl hover:bg-warmgray-50 dark:hover:bg-warmgray-750 hover:border-copper-300 dark:hover:border-copper-700 cursor-pointer transition-all duration-300 hover:-translate-y-1',
  }

  return (
    <div
      className={cn(
        'rounded-xl border backdrop-blur-sm transition-all duration-200',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export function CardHeader({ className, children, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col space-y-1.5 p-6 border-b border-warmgray-200 dark:border-warmgray-700',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

export function CardTitle({ className, children, ...props }: CardTitleProps) {
  return (
    <h3
      className={cn(
        'text-2xl font-semibold leading-none tracking-tight text-warmgray-900 dark:text-warmgray-100 font-serif',
        className
      )}
      {...props}
    >
      {children}
    </h3>
  )
}

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export function CardContent({ className, children, ...props }: CardContentProps) {
  return (
    <div className={cn('p-6', className)} {...props}>
      {children}
    </div>
  )
}

// Additional card subcomponents for enhanced flexibility
interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

export function CardDescription({ className, children, ...props }: CardDescriptionProps) {
  return (
    <p
      className={cn('text-sm text-warmgray-600 dark:text-warmgray-400 mt-2', className)}
      {...props}
    >
      {children}
    </p>
  )
}

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between p-6 pt-4 border-t border-warmgray-200 dark:border-warmgray-700',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
