/**
 * Account Management Context
 * Provides account selection, creation, and management functionality
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface Account {
  account_id: string
  account_name: string
  account_type: string
  strategy_type: string
  risk_level: string
  balance: number
  buying_power: number
  deployed_capital: number
  total_pnl: number
  total_pnl_pct: number
  monthly_pnl: number
  monthly_pnl_pct: number
  open_positions_count: number
  today_trades: number
  win_rate: number
  created_at: string
  reset_date: string
}

interface AccountContextType {
  accounts: Account[]
  selectedAccount: Account | null
  isLoading: boolean
  error: string | null
  selectAccount: (account: Account) => void
  createAccount: (accountData: CreateAccountData) => Promise<void>
  refreshAccounts: () => Promise<void>
  deleteAccount: (accountId: string) => Promise<void>
}

interface CreateAccountData {
  account_name: string
  initial_balance: number
  strategy_type: 'swing' | 'options' | 'hybrid'
  risk_level: 'low' | 'moderate' | 'high'
  max_position_size: number
  max_portfolio_risk: number
}

const AccountContext = createContext<AccountContextType | undefined>(undefined)

const STORAGE_KEY = 'robo-trader-selected-account'

export function AccountProvider({ children }: { children: ReactNode }) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load selected account from localStorage on mount
  useEffect(() => {
    const storedAccountId = localStorage.getItem(STORAGE_KEY)
    if (storedAccountId) {
      // We'll set this after loading accounts
    }
  }, [])

  // Load accounts on mount
  useEffect(() => {
    refreshAccounts()
  }, [])

  // Set selected account when accounts are loaded and we have a stored ID
  useEffect(() => {
    if (accounts.length > 0 && !selectedAccount) {
      const storedAccountId = localStorage.getItem(STORAGE_KEY)
      if (storedAccountId) {
        const storedAccount = accounts.find(acc => acc.account_id === storedAccountId)
        if (storedAccount) {
          setSelectedAccount(storedAccount)
          return
        }
      }
      // Default to first account if no stored account or stored account not found
      setSelectedAccount(accounts[0])
    }
  }, [accounts, selectedAccount])

  const selectAccount = (account: Account) => {
    setSelectedAccount(account)
    localStorage.setItem(STORAGE_KEY, account.account_id)
  }

  const refreshAccounts = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // For now, we'll fetch accounts from the backend
      // Since the backend doesn't have a list accounts endpoint yet, we'll start with the default account
      const defaultAccountId = 'paper_swing_main'

      const response = await fetch(`/api/paper-trading/accounts/${defaultAccountId}/overview`)
      if (!response.ok) {
        throw new Error('Failed to fetch account')
      }

      const accountData = await response.json()
      const account: Account = {
        account_id: accountData.account_id,
        account_name: 'Paper Trading - Swing Trading Account',
        account_type: accountData.account_type,
        strategy_type: accountData.strategy_type,
        risk_level: 'moderate', // Default for now
        balance: accountData.balance,
        buying_power: accountData.buying_power,
        deployed_capital: accountData.deployed_capital,
        total_pnl: accountData.total_pnl,
        total_pnl_pct: accountData.total_pnl_pct,
        monthly_pnl: accountData.monthly_pnl,
        monthly_pnl_pct: accountData.monthly_pnl_pct,
        open_positions_count: accountData.open_positions_count,
        today_trades: accountData.today_trades,
        win_rate: accountData.win_rate,
        created_at: accountData.created_at,
        reset_date: accountData.reset_date,
      }

      setAccounts([account])

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts')
      // Fallback to default account structure
      const fallbackAccount: Account = {
        account_id: 'paper_swing_main',
        account_name: 'Paper Trading - Swing Trading Account',
        account_type: 'swing_trading',
        strategy_type: 'swing',
        risk_level: 'moderate',
        balance: 100000,
        buying_power: 100000,
        deployed_capital: 0,
        total_pnl: 0,
        total_pnl_pct: 0,
        monthly_pnl: 0,
        monthly_pnl_pct: 0,
        open_positions_count: 0,
        today_trades: 0,
        win_rate: 0,
        created_at: new Date().toISOString(),
        reset_date: '',
      }
      setAccounts([fallbackAccount])
    } finally {
      setIsLoading(false)
    }
  }

  const createAccount = async (accountData: CreateAccountData) => {
    try {
      setError(null)

      // Generate account ID
      const accountId = `paper_${accountData.strategy_type}_${Date.now()}`

      // For now, we'll create a local account object
      // In a full implementation, this would call a backend endpoint
      const newAccount: Account = {
        account_id: accountId,
        account_name: accountData.account_name,
        account_type: accountData.strategy_type === 'swing' ? 'swing_trading' : 'options_trading',
        strategy_type: accountData.strategy_type,
        risk_level: accountData.risk_level,
        balance: accountData.initial_balance,
        buying_power: accountData.initial_balance,
        deployed_capital: 0,
        total_pnl: 0,
        total_pnl_pct: 0,
        monthly_pnl: 0,
        monthly_pnl_pct: 0,
        open_positions_count: 0,
        today_trades: 0,
        win_rate: 0,
        created_at: new Date().toISOString(),
        reset_date: '',
      }

      setAccounts(prev => [...prev, newAccount])
      selectAccount(newAccount)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account')
      throw err
    }
  }

  const deleteAccount = async (accountId: string) => {
    try {
      setError(null)

      // For now, just remove from local state
      // In a full implementation, this would call a backend endpoint
      setAccounts(prev => prev.filter(acc => acc.account_id !== accountId))

      // If deleted account was selected, select another one
      if (selectedAccount?.account_id === accountId) {
        const remainingAccounts = accounts.filter(acc => acc.account_id !== accountId)
        if (remainingAccounts.length > 0) {
          selectAccount(remainingAccounts[0])
        } else {
          setSelectedAccount(null)
          localStorage.removeItem(STORAGE_KEY)
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete account')
      throw err
    }
  }

  const value: AccountContextType = {
    accounts,
    selectedAccount,
    isLoading,
    error,
    selectAccount,
    createAccount,
    refreshAccounts,
    deleteAccount,
  }

  return (
    <AccountContext.Provider value={value}>
      {children}
    </AccountContext.Provider>
  )
}

export function useAccount() {
  const context = useContext(AccountContext)
  if (context === undefined) {
    throw new Error('useAccount must be used within an AccountProvider')
  }
  return context
}