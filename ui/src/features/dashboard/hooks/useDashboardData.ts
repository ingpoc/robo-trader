import { useQuery } from '@tanstack/react-query'

import { configurationAPI, operatorAPI, runtimeAPI } from '@/api/endpoints'
import type { AccountPolicy, ConfigurationStatus } from '@/types/api'
import type {
  OverviewSummary,
  PaperTradingOperatorSnapshot,
  RuntimeHealthResponse,
} from '@/features/paper-trading/types'

interface UseDashboardDataOptions {
  accountId: string | null
}

interface DashboardOperatorData {
  snapshot: PaperTradingOperatorSnapshot | null
  overviewSummary: OverviewSummary | null
  runtimeHealth: RuntimeHealthResponse | null
  configurationStatus: ConfigurationStatus | null
  accountPolicy: AccountPolicy | null
  incidents: Array<Record<string, unknown>>
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<unknown>
}

export const useDashboardData = ({ accountId }: UseDashboardDataOptions): DashboardOperatorData => {
  const query = useQuery(
    ['operator-dashboard', accountId],
    async () => {
      const [runtimeHealth, configurationStatus, snapshot] = await Promise.all([
        runtimeAPI.getHealth(),
        configurationAPI.getStatus(),
        accountId ? operatorAPI.getOperatorSnapshot(accountId) : Promise.resolve(null),
      ])

      return {
        runtimeHealth,
        configurationStatus: configurationStatus.configuration_status,
        snapshot,
      }
    },
    {
      enabled: Boolean(accountId),
      staleTime: 5000,
      cacheTime: 5 * 60 * 1000,
    }
  )

  const snapshot = query.data?.snapshot ?? null

  return {
    snapshot,
    overviewSummary: snapshot?.overview_summary ?? null,
    runtimeHealth: query.data?.runtimeHealth ?? null,
    configurationStatus: query.data?.configurationStatus ?? null,
    accountPolicy: snapshot?.account_policy ?? null,
    incidents: Array.isArray(snapshot?.incidents) ? snapshot.incidents : [],
    isLoading: query.isLoading,
    error: (query.error as Error | null) ?? null,
    refetch: query.refetch,
  }
}
