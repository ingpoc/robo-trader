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

  backendStatus: 'unknown' | 'connecting' | 'connected' | 'disconnected' | 'error'
  setBackendStatus: (status: DashboardStore['backendStatus']) => void

  selectedRecommendation: Recommendation | null
  setSelectedRecommendation: (recommendation: Recommendation | null) => void

  alerts: Alert[]
  addAlert: (alert: Alert) => void
  removeAlert: (id: string) => void

  // Real-time data tracking
  lastUpdateTimestamp: number | null
  setLastUpdateTimestamp: (timestamp: number) => void

  // Connection quality metrics
  connectionQuality: 'excellent' | 'good' | 'poor' | 'offline'
  setConnectionQuality: (quality: DashboardStore['connectionQuality']) => void

  // Data freshness indicators
  dataFreshness: {
    portfolio: number | null
    analytics: number | null
    alerts: number | null
  }
  updateDataFreshness: (type: keyof DashboardStore['dataFreshness'], timestamp: number) => void
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  dashboardData: null,
  setDashboardData: (data) => set((state) => ({
    dashboardData: data,
    lastUpdateTimestamp: Date.now(),
    dataFreshness: {
      ...state.dataFreshness,
      portfolio: Date.now(),
      analytics: Date.now(),
      alerts: Date.now(),
    }
  })),

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
  setConnected: (connected) => set({
    isConnected: connected,
    connectionQuality: connected ? 'excellent' : 'offline'
  }),

  backendStatus: 'unknown',
  setBackendStatus: (status) => set({ backendStatus: status }),

  selectedRecommendation: null,
  setSelectedRecommendation: (recommendation) =>
    set({ selectedRecommendation: recommendation }),

  alerts: [],
  addAlert: (alert) => set((state) => ({ alerts: [...state.alerts, alert] })),
  removeAlert: (id) =>
    set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),

  // Real-time data tracking
  lastUpdateTimestamp: null,
  setLastUpdateTimestamp: (timestamp) => set({ lastUpdateTimestamp: timestamp }),

  connectionQuality: 'offline',
  setConnectionQuality: (quality) => set({ connectionQuality: quality }),

  dataFreshness: {
    portfolio: null,
    analytics: null,
    alerts: null,
  },
  updateDataFreshness: (type, timestamp) =>
    set((state) => ({
      dataFreshness: {
        ...state.dataFreshness,
        [type]: timestamp,
      },
    })),
}))
