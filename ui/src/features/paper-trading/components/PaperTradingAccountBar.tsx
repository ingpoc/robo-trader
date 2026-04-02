import { RefreshCw, Wallet2 } from 'lucide-react'

import { Button } from '@/components/ui/Button'

interface AccountOption {
  account_id: string
  account_name: string
  strategy_type: string
}

interface PaperTradingAccountBarProps {
  accounts: AccountOption[]
  selectedAccountId?: string | null
  onSelectAccount: (accountId: string) => void
  onRefresh: () => Promise<void>
  isRefreshing?: boolean
}

export function PaperTradingAccountBar({
  accounts,
  selectedAccountId,
  onSelectAccount,
  onRefresh,
  isRefreshing = false,
}: PaperTradingAccountBarProps) {
  const selectedAccount = accounts.find(account => account.account_id === selectedAccountId)

  return (
    <section className="desk-panel px-6 py-5">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Wallet2 className="h-4 w-4 text-primary" />
            <p className="desk-kicker">Account Context</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="desk-heading">
              {selectedAccount?.account_name || 'Select paper account'}
            </h2>
            {selectedAccount ? (
              <span className="rounded-full border border-border/80 px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {selectedAccount.strategy_type}
              </span>
            ) : null}
          </div>
          <p className="desk-copy max-w-2xl">
            The app is intentionally single-account and operator-scoped here. Discovery, research, decision review, and daily review all bind to the selected paper account only.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="paper-trading-account-select">
            Select paper trading account
          </label>
          <select
            id="paper-trading-account-select"
            name="paper_trading_account"
            value={selectedAccountId ?? ''}
            onChange={(event) => onSelectAccount(event.target.value)}
            className="desk-select min-w-[260px]"
            aria-label="Select paper trading account"
          >
            {accounts.length === 0 ? (
              <option value="">No paper accounts available</option>
            ) : null}
            {accounts.map(account => (
              <option key={account.account_id} value={account.account_id}>
                {account.account_name} · {account.strategy_type}
              </option>
            ))}
          </select>

          <Button variant="outline" onClick={() => void onRefresh()} isLoading={isRefreshing}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>
    </section>
  )
}
