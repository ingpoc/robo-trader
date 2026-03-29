/**
 * Account Management Context
 * Provides account selection, creation, and management functionality.
 */

import React, { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

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

let inFlightAccountsRequest: Promise<Account[]> | null = null

function normalizeAccounts(payload: any): Account[] {
  return (payload.accounts || []).map((accountData: any) => ({
    account_id: accountData.accountId,
    account_name: accountData.accountName || accountData.accountId,
    account_type: accountData.accountType,
    strategy_type: accountData.accountType,
    risk_level: accountData.riskLevel || 'moderate',
    balance: accountData.currentBalance || 0,
    buying_power: accountData.marginAvailable || 0,
    deployed_capital: accountData.totalInvested || 0,
    total_pnl: 0,
    total_pnl_pct: 0,
    monthly_pnl: 0,
    monthly_pnl_pct: 0,
    open_positions_count: 0,
    today_trades: 0,
    win_rate: 0,
    created_at: accountData.createdDate || new Date().toISOString(),
    reset_date: '',
  }))
}

async function fetchAccountsOnce(): Promise<Account[]> {
  if (!inFlightAccountsRequest) {
    inFlightAccountsRequest = (async () => {
      const response = await fetch('/api/paper-trading/accounts')
      if (!response.ok) {
        throw new Error('Failed to fetch accounts')
      }

      const data = await response.json()
      return normalizeAccounts(data)
    })().finally(() => {
      inFlightAccountsRequest = null
    })
  }

  return inFlightAccountsRequest
}

export function AccountProvider({ children }: { children: ReactNode }) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const selectAccount = useCallback((account: Account) => {
    setSelectedAccount(account)
    localStorage.setItem(STORAGE_KEY, account.account_id)
  }, [])

  const refreshAccounts = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const loadedAccounts = await fetchAccountsOnce()
      setAccounts(loadedAccounts)

      const storedAccountId = localStorage.getItem(STORAGE_KEY)
      const nextSelectedAccount = storedAccountId
        ? loadedAccounts.find(account => account.account_id === storedAccountId) || loadedAccounts[0] || null
        : loadedAccounts[0] || null

      setSelectedAccount(nextSelectedAccount)

      if (!nextSelectedAccount) {
        localStorage.removeItem(STORAGE_KEY)
      } else if (storedAccountId !== nextSelectedAccount.account_id) {
        localStorage.setItem(STORAGE_KEY, nextSelectedAccount.account_id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts')
      setAccounts([])
      setSelectedAccount(null)
      localStorage.removeItem(STORAGE_KEY)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshAccounts()
  }, [refreshAccounts])

  const createAccount = async (accountData: CreateAccountData) => {
    try {
      setError(null)

      const response = await fetch('/api/paper-trading/accounts/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          account_name: accountData.account_name,
          initial_balance: accountData.initial_balance,
          strategy_type: accountData.strategy_type,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create account')
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Failed to create account')
      }

      const newAccount: Account = {
        account_id: data.account.accountId,
        account_name: data.account.accountName,
        account_type: accountData.strategy_type === 'swing' ? 'swing_trading' : 'options_trading',
        strategy_type: accountData.strategy_type,
        risk_level: accountData.risk_level,
        balance: data.account.currentBalance,
        buying_power: data.account.currentBalance,
        deployed_capital: 0,
        total_pnl: 0,
        total_pnl_pct: 0,
        monthly_pnl: 0,
        monthly_pnl_pct: 0,
        open_positions_count: 0,
        today_trades: 0,
        win_rate: 0,
        created_at: data.account.createdAt,
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

      const response = await fetch(`/api/paper-trading/accounts/${accountId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete account')
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Failed to delete account')
      }

      setAccounts(prev => {
        const remainingAccounts = prev.filter(account => account.account_id !== accountId)

        if (selectedAccount?.account_id === accountId) {
          const nextAccount = remainingAccounts[0] || null
          setSelectedAccount(nextAccount)

          if (nextAccount) {
            localStorage.setItem(STORAGE_KEY, nextAccount.account_id)
          } else {
            localStorage.removeItem(STORAGE_KEY)
          }
        }

        return remainingAccounts
      })
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
