/**
 * Account Selector Component
 * Allows users to select between different paper trading accounts
 */

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useAccount, Account } from '@/contexts/AccountContext'
import {
  ChevronDown,
  Plus,
  Wallet,
  TrendingUp,
  Shield,
  AlertTriangle,
  CheckCircle,
  X,
} from 'lucide-react'

interface AccountSelectorProps {
  className?: string
}

export function AccountSelector({ className }: AccountSelectorProps) {
  const { accounts, selectedAccount, selectAccount, createAccount, isLoading, error } = useAccount()
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [createForm, setCreateForm] = useState({
    account_name: '',
    initial_balance: '100000',
    strategy_type: 'swing' as 'swing' | 'options' | 'hybrid',
    risk_level: 'moderate' as 'low' | 'moderate' | 'high',
    max_position_size: '5',
    max_portfolio_risk: '10',
  })

  const handleCreateAccount = async () => {
    try {
      await createAccount({
        account_name: createForm.account_name,
        initial_balance: parseFloat(createForm.initial_balance),
        strategy_type: createForm.strategy_type,
        risk_level: createForm.risk_level,
        max_position_size: parseFloat(createForm.max_position_size),
        max_portfolio_risk: parseFloat(createForm.max_portfolio_risk),
      })
      setShowCreateDialog(false)
      setCreateForm({
        account_name: '',
        initial_balance: '100000',
        strategy_type: 'swing',
        risk_level: 'moderate',
        max_position_size: '5',
        max_portfolio_risk: '10',
      })
    } catch (err) {
      // Error is handled in context
    }
  }

  const getRiskBadgeColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'bg-green-100 text-green-800'
      case 'moderate': return 'bg-yellow-100 text-yellow-800'
      case 'high': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStrategyIcon = (strategyType: string) => {
    switch (strategyType) {
      case 'swing': return <TrendingUp className="w-4 h-4" />
      case 'options': return <Shield className="w-4 h-4" />
      case 'hybrid': return <Wallet className="w-4 h-4" />
      default: return <Wallet className="w-4 h-4" />
    }
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            <span className="ml-2">Loading accounts...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center text-red-600">
            <AlertTriangle className="w-4 h-4 mr-2" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Trading Account</CardTitle>
              <CardDescription>Select or create a paper trading account</CardDescription>
            </div>
            <Button
              size="sm"
              onClick={() => setShowCreateDialog(true)}
              className="flex items-center gap-1"
            >
              <Plus className="w-4 h-4" />
              New Account
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {selectedAccount && (
            <div className="p-4 border rounded-lg bg-muted/50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getStrategyIcon(selectedAccount.strategy_type)}
                  <div>
                    <h3 className="font-medium">{selectedAccount.account_name}</h3>
                    <p className="text-sm text-muted-foreground font-mono">
                      {selectedAccount.account_id}
                    </p>
                  </div>
                </div>
                <Badge className={getRiskBadgeColor(selectedAccount.risk_level)}>
                  {selectedAccount.risk_level.toUpperCase()} RISK
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Balance</p>
                  <p className="font-bold">₹{selectedAccount.balance.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">P&L</p>
                  <p className={`font-bold ${selectedAccount.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    ₹{selectedAccount.total_pnl.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {accounts.length > 1 && (
            <div>
              <Label className="text-sm font-medium">Switch Account</Label>
              <Select
                value={selectedAccount?.account_id || ''}
                onChange={(e) => {
                  const account = accounts.find(acc => acc.account_id === e.target.value)
                  if (account) selectAccount(account)
                }}
                options={accounts.map(account => ({
                  value: account.account_id,
                  label: `${account.account_name} (${account.account_id})`
                }))}
              />
            </div>
          )}

          {accounts.length === 0 && (
            <div className="text-center py-8">
              <Wallet className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No trading accounts found</p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Your First Account
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Account Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Trading Account</DialogTitle>
            <DialogDescription>
              Set up a new paper trading account with custom parameters
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label>Account Name</Label>
              <Input
                placeholder="e.g., My Swing Trading Account"
                value={createForm.account_name}
                onChange={(e) => setCreateForm({ ...createForm, account_name: e.target.value })}
              />
            </div>

            <div>
              <Label>Initial Balance (₹)</Label>
              <Input
                type="number"
                placeholder="100000"
                value={createForm.initial_balance}
                onChange={(e) => setCreateForm({ ...createForm, initial_balance: e.target.value })}
              />
            </div>

            <div>
              <Label>Strategy Type</Label>
              <Select
                value={createForm.strategy_type}
                onChange={(e) => setCreateForm({ ...createForm, strategy_type: e.target.value as any })}
                options={[
                  { value: 'swing', label: 'Swing Trading' },
                  { value: 'options', label: 'Options Trading' },
                  { value: 'hybrid', label: 'Hybrid' },
                ]}
              />
            </div>

            <div>
              <Label>Risk Level</Label>
              <Select
                value={createForm.risk_level}
                onChange={(e) => setCreateForm({ ...createForm, risk_level: e.target.value as any })}
                options={[
                  { value: 'low', label: 'Low Risk' },
                  { value: 'moderate', label: 'Moderate Risk' },
                  { value: 'high', label: 'High Risk' },
                ]}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Position Size (%)</Label>
                <Input
                  type="number"
                  placeholder="5"
                  value={createForm.max_position_size}
                  onChange={(e) => setCreateForm({ ...createForm, max_position_size: e.target.value })}
                />
              </div>
              <div>
                <Label>Max Portfolio Risk (%)</Label>
                <Input
                  type="number"
                  placeholder="10"
                  value={createForm.max_portfolio_risk}
                  onChange={(e) => setCreateForm({ ...createForm, max_portfolio_risk: e.target.value })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateAccount}
              disabled={!createForm.account_name.trim()}
            >
              Create Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}