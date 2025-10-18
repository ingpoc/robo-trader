import { AlertTriangle, AlertCircle, CheckCircle, Info } from 'lucide-react'
import { ReactNode } from 'react'

export type AlertType = 'error' | 'warning' | 'success' | 'info'

interface AlertCardProps {
  type: AlertType
  title: string
  message: ReactNode
  actionButton?: {
    label: string
    onClick: () => void
  }
  onDismiss?: () => void
}

const alertConfig = {
  error: {
    icon: AlertTriangle,
    bgColor: 'bg-rose-50 dark:bg-rose-950',
    borderColor: 'border-rose-200 dark:border-rose-800',
    textColor: 'text-rose-900 dark:text-rose-100',
    accentColor: 'text-rose-600 dark:text-rose-400',
    buttonBgColor: 'bg-rose-100 dark:bg-rose-900 hover:bg-rose-200 dark:hover:bg-rose-800',
  },
  warning: {
    icon: AlertCircle,
    bgColor: 'bg-amber-50 dark:bg-amber-950',
    borderColor: 'border-amber-200 dark:border-amber-800',
    textColor: 'text-amber-900 dark:text-amber-100',
    accentColor: 'text-amber-600 dark:text-amber-400',
    buttonBgColor: 'bg-amber-100 dark:bg-amber-900 hover:bg-amber-200 dark:hover:bg-amber-800',
  },
  success: {
    icon: CheckCircle,
    bgColor: 'bg-emerald-50 dark:bg-emerald-950',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
    textColor: 'text-emerald-900 dark:text-emerald-100',
    accentColor: 'text-emerald-600 dark:text-emerald-400',
    buttonBgColor: 'bg-emerald-100 dark:bg-emerald-900 hover:bg-emerald-200 dark:hover:bg-emerald-800',
  },
  info: {
    icon: Info,
    bgColor: 'bg-copper-50 dark:bg-copper-950',
    borderColor: 'border-copper-200 dark:border-copper-800',
    textColor: 'text-copper-900 dark:text-copper-100',
    accentColor: 'text-copper-600 dark:text-copper-400',
    buttonBgColor: 'bg-copper-100 dark:bg-copper-900 hover:bg-copper-200 dark:hover:bg-copper-800',
  },
}

export function ErrorCard({
  type = 'error',
  title,
  message,
  actionButton,
  onDismiss,
}: AlertCardProps & { type?: AlertType }) {
  const config = alertConfig[type]
  const Icon = config.icon

  return (
    <div className={`rounded-xl border-l-4 p-6 ${config.bgColor} ${config.borderColor}`}>
      <div className="flex items-start gap-4">
        <Icon className={`w-6 h-6 flex-shrink-0 ${config.accentColor} mt-0.5`} />
        <div className="flex-1">
          <h3 className={`text-lg font-bold ${config.textColor} mb-1`}>{title}</h3>
          <p className={`text-sm leading-relaxed ${config.textColor} opacity-90`}>{message}</p>
          {actionButton && (
            <button
              onClick={actionButton.onClick}
              className={`mt-3 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${config.buttonBgColor} ${config.textColor}`}
            >
              {actionButton.label}
            </button>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={`flex-shrink-0 ${config.accentColor} opacity-50 hover:opacity-100 transition-opacity`}
          >
            <span className="text-2xl leading-none">×</span>
          </button>
        )}
      </div>
    </div>
  )
}

export function WarningCard({
  title,
  message,
  actionButton,
  onDismiss,
}: Omit<AlertCardProps, 'type'>) {
  return (
    <ErrorCard type="warning" title={title} message={message} actionButton={actionButton} onDismiss={onDismiss} />
  )
}

export function SuccessCard({
  title,
  message,
  actionButton,
  onDismiss,
}: Omit<AlertCardProps, 'type'>) {
  return (
    <ErrorCard type="success" title={title} message={message} actionButton={actionButton} onDismiss={onDismiss} />
  )
}

export function InfoCard({
  title,
  message,
  actionButton,
  onDismiss,
}: Omit<AlertCardProps, 'type'>) {
  return (
    <ErrorCard type="info" title={title} message={message} actionButton={actionButton} onDismiss={onDismiss} />
  )
}
