// Application constants and configuration

export const APP_CONFIG = {
  name: 'Robo Trader',
  version: '1.0.0',
  environment: process.env.NODE_ENV || 'development',
} as const

export const API_ENDPOINTS = {
  dashboard: '/api/dashboard',
  newsEarnings: '/api/news-earnings',
  upcomingEarnings: '/api/upcoming-earnings',
  recommendations: '/api/ai/recommendations',
} as const

export const REFRESH_INTERVALS = {
  dashboard: 10000, // 10 seconds
  newsEarnings: 30000, // 30 seconds
  upcomingEarnings: 300000, // 5 minutes
  recommendations: 60000, // 1 minute
} as const

export const PAGINATION = {
  defaultPageSize: 20,
  maxPageSize: 100,
} as const

export const UI_CONSTANTS = {
  animationDuration: 200,
  debounceDelay: 300,
  maxRetries: 3,
} as const

export const SENTIMENT_COLORS = {
  positive: {
    bg: 'bg-emerald-50 dark:bg-emerald-950',
    border: 'border-emerald-200 dark:border-emerald-800',
    text: 'text-emerald-700 dark:text-emerald-400',
  },
  negative: {
    bg: 'bg-rose-50 dark:bg-rose-950',
    border: 'border-rose-200 dark:border-rose-800',
    text: 'text-rose-700 dark:text-rose-400',
  },
  neutral: {
    bg: 'bg-warmgray-50 dark:bg-warmgray-950',
    border: 'border-warmgray-300 dark:border-warmgray-800',
    text: 'text-warmgray-700 dark:text-warmgray-400',
  },
} as const

export const RECOMMENDATION_COLORS = {
  buy: {
    bg: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900 dark:text-emerald-200 dark:border-emerald-800',
  },
  sell: {
    bg: 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900 dark:text-rose-200 dark:border-rose-800',
  },
  hold: {
    bg: 'bg-copper-100 text-copper-800 border-copper-200 dark:bg-copper-900 dark:text-copper-200 dark:border-copper-800',
  },
} as const

export const STATUS_COLORS = {
  approved: 'text-emerald-600',
  rejected: 'text-rose-600',
  discussing: 'text-copper-600',
  pending: 'text-warmgray-400',
} as const

export const AGENT_STATUS_COLORS = {
  active: {
    bg: 'bg-emerald-50 dark:bg-emerald-950',
    border: 'border-emerald-200 dark:border-emerald-800',
    text: 'text-emerald-700 dark:text-emerald-400',
  },
  inactive: {
    bg: 'bg-warmgray-50 dark:bg-warmgray-950',
    border: 'border-warmgray-300 dark:border-warmgray-800',
    text: 'text-warmgray-700 dark:text-warmgray-400',
  },
  error: {
    bg: 'bg-rose-50 dark:bg-rose-950',
    border: 'border-rose-200 dark:border-rose-800',
    text: 'text-rose-700 dark:text-rose-400',
  },
} as const

export const RISK_LEVEL_COLORS = {
  low: {
    bg: 'bg-emerald-50 dark:bg-emerald-950',
    border: 'border-emerald-200 dark:border-emerald-800',
    text: 'text-emerald-700 dark:text-emerald-400',
  },
  medium: {
    bg: 'bg-copper-50 dark:bg-copper-950',
    border: 'border-copper-200 dark:border-copper-800',
    text: 'text-copper-700 dark:text-copper-400',
  },
  high: {
    bg: 'bg-rose-50 dark:bg-rose-950',
    border: 'border-rose-200 dark:border-rose-800',
    text: 'text-rose-700 dark:text-rose-400',
  },
} as const

export const CONFIDENCE_THRESHOLDS = {
  high: 0.8,
  medium: 0.6,
  low: 0,
} as const

export const ERROR_MESSAGES = {
  network: 'Network error. Please check your connection and try again.',
  timeout: 'Request timed out. Please try again.',
  notFound: 'Data not found. Please select a different stock.',
  server: 'Server error. Please try again later.',
  unknown: 'An unexpected error occurred. Please try again.',
} as const