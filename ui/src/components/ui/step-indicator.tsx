import { cn } from '@/lib/utils'
import { Check, Circle, Clock } from 'lucide-react'

export interface Step {
  id: string
  title: string
  description?: string
  status: 'pending' | 'active' | 'completed' | 'error'
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep?: string
  className?: string
  orientation?: 'horizontal' | 'vertical'
}

export function StepIndicator({
  steps,
  currentStep,
  className,
  orientation = 'horizontal'
}: StepIndicatorProps) {
  const getStepIcon = (status: Step['status']) => {
    switch (status) {
      case 'completed':
        return <Check className="w-4 h-4" />
      case 'active':
        return <Clock className="w-4 h-4 animate-pulse" />
      case 'error':
        return <Circle className="w-4 h-4" />
      default:
        return <Circle className="w-4 h-4" />
    }
  }

  const getStepColor = (status: Step['status']) => {
    switch (status) {
      case 'completed':
        return 'text-success bg-success border-success'
      case 'active':
        return 'text-accent bg-accent border-accent'
      case 'error':
        return 'text-error bg-error border-error'
      default:
        return 'text-gray-400 bg-gray-100 border-gray-300'
    }
  }

  if (orientation === 'vertical') {
    return (
      <div className={cn('flex flex-col gap-4', className)}>
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-start gap-3">
            <div className={cn(
              'flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors',
              getStepColor(step.status)
            )}>
              {getStepIcon(step.status)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className={cn(
                  'text-sm font-medium',
                  step.status === 'active' ? 'text-accent' :
                  step.status === 'completed' ? 'text-success' :
                  step.status === 'error' ? 'text-error' : 'text-gray-600'
                )}>
                  {step.title}
                </h4>
                {step.status === 'active' && (
                  <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                )}
              </div>
              {step.description && (
                <p className="text-xs text-gray-500 mt-1">{step.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={cn('flex items-center justify-between', className)}>
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center flex-1">
          <div className="flex flex-col items-center">
            <div className={cn(
              'flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors',
              getStepColor(step.status)
            )}>
              {getStepIcon(step.status)}
            </div>
            <div className="mt-2 text-center">
              <div className={cn(
                'text-xs font-medium',
                step.status === 'active' ? 'text-accent' :
                step.status === 'completed' ? 'text-success' :
                step.status === 'error' ? 'text-error' : 'text-gray-600'
              )}>
                {step.title}
              </div>
              {step.description && (
                <div className="text-xs text-gray-500 mt-1 max-w-20 truncate">
                  {step.description}
                </div>
              )}
            </div>
          </div>
          {index < steps.length - 1 && (
            <div className={cn(
              'flex-1 h-0.5 mx-4 transition-colors',
              step.status === 'completed' ? 'bg-success' :
              step.status === 'active' ? 'bg-accent' : 'bg-gray-200'
            )} />
          )}
        </div>
      ))}
    </div>
  )
}