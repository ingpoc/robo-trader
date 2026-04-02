import React from 'react'
import { cn } from '@/utils/cn'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  variant?: 'base' | 'featured' | 'compact' | 'interactive'
}

export function Card({ className, children, variant = 'base', ...props }: CardProps) {
  const variantStyles = {
    base: 'border-border bg-card text-card-foreground shadow-sm',
    featured: 'border-border bg-gradient-to-br from-card to-muted/35 text-card-foreground shadow-md ring-1 ring-copper-500/15',
    compact: 'border-border/70 bg-white/90 text-card-foreground shadow-sm dark:bg-warmgray-800/90',
    interactive: 'border-border bg-card text-card-foreground shadow-sm hover:-translate-y-0.5 hover:border-copper-300 hover:shadow-md',
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
        'flex flex-col space-y-1.5 border-b border-border/80 p-6',
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
        'font-serif text-2xl font-semibold leading-none tracking-tight text-card-foreground',
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
      className={cn('mt-2 text-sm text-muted-foreground', className)}
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
        'flex items-center justify-between border-t border-border/80 p-6 pt-4',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
