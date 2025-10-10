import { create } from 'zustand'
import type { DashboardData, Recommendation, Alert } from '@/types/api'

interface ToastState {
  id: string
  title: string
  description?: string
  variant: 'default' | 'success' | 'error'
}

interface DashboardStore {
  dashboardData: DashboardData | null
  setDashboardData: (data: DashboardData) => void

  toasts: ToastState[]
  addToast: (toast: Omit<ToastState, 'id'>) => void
  removeToast: (id: string) => void

  sidebarOpen: boolean
  toggleSidebar: () => void

  activeModal: 'chat' | 'recommendations' | 'agents' | 'analytics' | null
  openModal: (modal: NonNullable<DashboardStore['activeModal']>) => void
  closeModal: () => void

  isConnected: boolean
  setConnected: (connected: boolean) => void

  selectedRecommendation: Recommendation | null
  setSelectedRecommendation: (recommendation: Recommendation | null) => void

  alerts: Alert[]
  addAlert: (alert: Alert) => void
  removeAlert: (id: string) => void
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  dashboardData: null,
  setDashboardData: (data) => set({ dashboardData: data }),

  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: `${Date.now()}-${Math.random()}` }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  activeModal: null,
  openModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null }),

  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  selectedRecommendation: null,
  setSelectedRecommendation: (recommendation) =>
    set({ selectedRecommendation: recommendation }),

  alerts: [],
  addAlert: (alert) => set((state) => ({ alerts: [...state.alerts, alert] })),
  removeAlert: (id) =>
    set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),
}))
