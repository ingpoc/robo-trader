/**
 * Trade Validator Utilities
 * Pure validation functions for trade validation logic
 */

import type { TradeFormData, AccountOverviewResponse, OpenPositionResponse } from '../types'

export interface ValidationError {
  message: string
  field?: string
}

export interface ValidationWarning {
  message: string
  field?: string
}

/**
 * Validate if account has sufficient buying power for trade
 */
export function validateBuyingPower(
  tradeValue: number,
  buyingPower: number
): ValidationError | null {
  if (tradeValue > buyingPower) {
    return {
      message: `Insufficient buying power. Required: ₹${tradeValue.toLocaleString()}, Available: ₹${buyingPower.toLocaleString()}`,
      field: 'price'
    }
  }
  return null
}

/**
 * Validate position size against account balance (5% max)
 */
export function validatePositionSize(
  tradeValue: number,
  balance: number
): { error: ValidationError | null; warning: ValidationWarning | null } {
  const maxPositionSize = balance * 0.05

  if (tradeValue > maxPositionSize) {
    return {
      error: {
        message: `Position size exceeds 5% limit. Max allowed: ₹${maxPositionSize.toLocaleString()}`,
        field: 'quantity'
      },
      warning: null
    }
  }

  if (tradeValue > maxPositionSize * 0.8) {
    return {
      error: null,
      warning: {
        message: `Position size is 80% of maximum limit`,
        field: 'quantity'
      }
    }
  }

  return { error: null, warning: null }
}

/**
 * Validate portfolio risk (10% max total exposure)
 */
export function validatePortfolioRisk(
  tradeValue: number,
  currentExposure: number,
  balance: number,
  tradeType: 'BUY' | 'SELL'
): { error: ValidationError | null; warning: ValidationWarning | null } {
  if (tradeType === 'SELL') {
    return { error: null, warning: null }
  }

  const maxPortfolioRisk = balance * 0.1
  const projectedExposure = currentExposure + tradeValue

  if (projectedExposure > maxPortfolioRisk) {
    return {
      error: {
        message: `Trade would exceed 10% portfolio risk limit`,
        field: 'quantity'
      },
      warning: null
    }
  }

  if (projectedExposure > maxPortfolioRisk * 0.8) {
    return {
      error: null,
      warning: {
        message: `Trade would bring portfolio exposure to 80% of risk limit`,
        field: 'quantity'
      }
    }
  }

  return { error: null, warning: null }
}

/**
 * Validate stop loss direction and distance
 */
export function validateStopLoss(
  stopLoss: number,
  entryPrice: number,
  tradeType: 'BUY' | 'SELL'
): { error: ValidationError | null; warnings: ValidationWarning[] } {
  const warnings: ValidationWarning[] = []

  // Direction validation
  if (tradeType === 'BUY' && stopLoss >= entryPrice) {
    return {
      error: {
        message: 'Stop loss must be below entry price for BUY orders',
        field: 'stopLoss'
      },
      warnings: []
    }
  }

  if (tradeType === 'SELL' && stopLoss <= entryPrice) {
    return {
      error: {
        message: 'Stop loss must be above entry price for SELL orders',
        field: 'stopLoss'
      },
      warnings: []
    }
  }

  // Distance validation
  const stopLossPct = Math.abs(entryPrice - stopLoss) / entryPrice * 100

  if (stopLossPct < 0.5) {
    warnings.push({
      message: 'Stop loss is very tight (< 0.5% from entry)',
      field: 'stopLoss'
    })
  }

  if (stopLossPct > 15) {
    warnings.push({
      message: 'Stop loss is very wide (> 15% from entry)',
      field: 'stopLoss'
    })
  }

  return { error: null, warnings }
}

/**
 * Validate target price direction and distance
 */
export function validateTarget(
  target: number,
  entryPrice: number,
  tradeType: 'BUY' | 'SELL'
): { error: ValidationError | null; warnings: ValidationWarning[] } {
  const warnings: ValidationWarning[] = []

  // Direction validation
  if (tradeType === 'BUY' && target <= entryPrice) {
    return {
      error: {
        message: 'Target price must be above entry price for BUY orders',
        field: 'target'
      },
      warnings: []
    }
  }

  if (tradeType === 'SELL' && target >= entryPrice) {
    return {
      error: {
        message: 'Target price must be below entry price for SELL orders',
        field: 'target'
      },
      warnings: []
    }
  }

  // Distance validation
  const targetPct = Math.abs(entryPrice - target) / entryPrice * 100

  if (targetPct < 1) {
    warnings.push({
      message: 'Target is very close (< 1% from entry)',
      field: 'target'
    })
  }

  return { error: null, warnings }
}

/**
 * Calculate risk-reward ratio
 */
export function calculateRiskRewardRatio(
  entry: number,
  stopLoss: number,
  target: number
): number {
  const risk = Math.abs(entry - stopLoss)
  const reward = Math.abs(target - entry)

  if (risk === 0) return 0
  return reward / risk
}

/**
 * Check if position already exists for symbol
 */
export function checkExistingPosition(
  symbol: string,
  positions: OpenPositionResponse[]
): OpenPositionResponse | null {
  return positions.find(p => p.symbol === symbol.toUpperCase()) || null
}

/**
 * Validate trade form data
 */
export function validateTradeForm(data: TradeFormData): {
  isValid: boolean
  errors: string[]
} {
  const errors: string[] = []

  if (!data.symbol || data.symbol.trim().length === 0) {
    errors.push('Symbol is required')
  }

  if (!data.quantity || parseInt(data.quantity) <= 0) {
    errors.push('Quantity must be greater than 0')
  }

  if (!data.price || parseFloat(data.price) <= 0) {
    errors.push('Price must be greater than 0')
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}
