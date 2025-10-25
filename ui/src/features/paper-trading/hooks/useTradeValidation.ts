/**
 * Trade Validation Hook
 * Validates trade inputs and calculates risk levels
 */

import { useMemo } from 'react'
import type { TradeFormData, AccountOverviewResponse, OpenPositionResponse, TradeValidationResult } from '../types'
import {
  validateBuyingPower,
  validatePositionSize,
  validatePortfolioRisk,
  validateStopLoss,
  validateTarget,
  validateTradeForm
} from '../utils/tradeValidator'

export function useTradeValidation(
  tradeForm: TradeFormData,
  accountOverview: AccountOverviewResponse | null,
  positions: OpenPositionResponse[]
): TradeValidationResult {
  return useMemo(() => {
    const errors: string[] = []
    const warnings: string[] = []
    let riskLevel: 'low' | 'medium' | 'high' = 'low'

    // Basic form validation
    if (!accountOverview || !tradeForm.symbol || !tradeForm.quantity || !tradeForm.price) {
      return { isValid: false, errors: [], warnings: [], riskLevel: 'low' }
    }

    const formValidation = validateTradeForm(tradeForm)
    if (!formValidation.isValid) {
      return { isValid: false, errors: formValidation.errors, warnings: [], riskLevel: 'low' }
    }

    const quantity = parseInt(tradeForm.quantity)
    const price = parseFloat(tradeForm.price)
    const tradeValue = quantity * price

    // Buying power check
    const buyingPowerError = validateBuyingPower(tradeValue, accountOverview.buying_power)
    if (buyingPowerError) {
      errors.push(buyingPowerError.message)
    }

    // Position size limits (5% of portfolio max)
    const positionSizeValidation = validatePositionSize(tradeValue, accountOverview.balance)
    if (positionSizeValidation.error) {
      errors.push(positionSizeValidation.error.message)
      riskLevel = 'high'
    } else if (positionSizeValidation.warning) {
      warnings.push(positionSizeValidation.warning.message)
      riskLevel = 'medium'
    }

    // Portfolio risk check (10% max total exposure)
    const portfolioRiskValidation = validatePortfolioRisk(
      tradeValue,
      accountOverview.deployed_capital,
      accountOverview.balance,
      tradeForm.type
    )
    if (portfolioRiskValidation.error) {
      errors.push(portfolioRiskValidation.error.message)
      riskLevel = 'high'
    } else if (portfolioRiskValidation.warning) {
      warnings.push(portfolioRiskValidation.warning.message)
      riskLevel = 'medium'
    }

    // Stop loss validation
    if (tradeForm.stopLoss) {
      const stopLoss = parseFloat(tradeForm.stopLoss)
      const stopLossValidation = validateStopLoss(stopLoss, price, tradeForm.type)

      if (stopLossValidation.error) {
        errors.push(stopLossValidation.error.message)
      }

      stopLossValidation.warnings.forEach(w => {
        warnings.push(w.message)
        if (riskLevel === 'low') riskLevel = 'medium'
      })
    } else {
      warnings.push('No stop loss set - consider adding risk protection')
      if (riskLevel === 'low') riskLevel = 'medium'
    }

    // Target price validation
    if (tradeForm.target) {
      const target = parseFloat(tradeForm.target)
      const targetValidation = validateTarget(target, price, tradeForm.type)

      if (targetValidation.error) {
        errors.push(targetValidation.error.message)
      }

      targetValidation.warnings.forEach(w => {
        warnings.push(w.message)
      })
    }

    // Check for existing position
    const existingPosition = positions.find(p => p.symbol === tradeForm.symbol.toUpperCase())
    if (existingPosition && tradeForm.type === 'BUY') {
      warnings.push(`You already have ${existingPosition.quantity} units of ${tradeForm.symbol}`)
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      riskLevel
    }
  }, [tradeForm, accountOverview, positions])
}
