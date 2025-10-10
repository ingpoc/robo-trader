import { useEffect } from 'react'
import {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
} from '@/components/ui/Toast'
import { useDashboardStore } from '@/store/dashboardStore'

export function Toaster() {
  const toasts = useDashboardStore((state) => state.toasts)
  const removeToast = useDashboardStore((state) => state.removeToast)

  useEffect(() => {
    toasts.forEach((toast) => {
      const timer = setTimeout(() => {
        removeToast(toast.id)
      }, 5000)

      return () => clearTimeout(timer)
    })
  }, [toasts, removeToast])

  return (
    <ToastProvider>
      {toasts.map((toast) => (
        <Toast key={toast.id} variant={toast.variant} onOpenChange={() => removeToast(toast.id)}>
          <div className="flex-1">
            <ToastTitle>{toast.title}</ToastTitle>
            {toast.description && <ToastDescription>{toast.description}</ToastDescription>}
          </div>
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  )
}
