import { Card, CardContent } from '@/components/ui/Card'
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
  return (
    <Card variant="compact">
      <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="text-sm font-semibold text-foreground">Paper Trading Account</div>
          <p className="text-sm text-muted-foreground">
            Account selection is explicit. Discovery, decisions, execution, and review all run against the selected paper account only.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <select
            id="paper-trading-account-select"
            name="paper_trading_account"
            value={selectedAccountId ?? ''}
            onChange={(event) => onSelectAccount(event.target.value)}
            className="h-10 min-w-[240px] rounded-md border border-border bg-card px-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
            Refresh Accounts
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
