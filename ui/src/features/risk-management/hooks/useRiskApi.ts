import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RiskLimit,
  StopLossOrder,
  RiskAlert,
  PortfolioRiskMetrics,
  RiskMonitoringStatus,
  StopLossTemplate,
  RebalancingRule,
  EmergencyOverride,
  ApiResponse,
  PaginatedResponse,
  RiskLimitFormData,
  StopLossTemplateFormData,
  RebalancingRuleFormData,
  EmergencyOverrideFormData
} from '../types';

// API Base URL - fallback to main API if risk service not available
const API_BASE = 'http://localhost:8000';

// Query Keys
export const riskQueryKeys = {
  limits: (userId?: string) => ['risk-limits', userId] as const,
  stopLoss: (userId?: string, symbol?: string) => ['stop-loss', userId, symbol] as const,
  alerts: (userId?: string, filters?: any) => ['risk-alerts', userId, filters] as const,
  metrics: (portfolioId: string, period: string) => ['risk-metrics', portfolioId, period] as const,
  monitoring: (userId?: string, portfolioId?: string) => ['risk-monitoring', userId, portfolioId] as const,
  templates: () => ['stop-loss-templates'] as const,
  rebalancing: () => ['rebalancing-rules'] as const,
  overrides: () => ['emergency-overrides'] as const,
};

// Risk Limits Hooks
export const useRiskLimits = (userId?: string) => {
  return useQuery({
    queryKey: riskQueryKeys.limits(userId),
    queryFn: async (): Promise<RiskLimit[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/limits?${params}`);
      const result: ApiResponse<{ limits: RiskLimit[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch risk limits');
      }

      return result.data?.limits || [];
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useUpdateRiskLimit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ limitId, updates }: { limitId: string; updates: Partial<RiskLimit> }) => {
      const response = await fetch(`${API_BASE}/limits/${limitId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      const result: ApiResponse<RiskLimit> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to update risk limit');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.limits() });
    },
  });
};

export const useCreateRiskLimit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RiskLimitFormData) => {
      const response = await fetch(`${API_BASE}/limits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<RiskLimit> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create risk limit');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.limits() });
    },
  });
};

// Stop-Loss Hooks
export const useStopLossOrders = (userId?: string, symbol?: string) => {
  return useQuery({
    queryKey: riskQueryKeys.stopLoss(userId, symbol),
    queryFn: async (): Promise<StopLossOrder[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (symbol) params.append('symbol', symbol);

      const response = await fetch(`${API_BASE}/stop-loss?${params}`);
      const result: ApiResponse<{ stop_losses: StopLossOrder[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch stop-loss orders');
      }

      return result.data?.stop_losses || [];
    },
    staleTime: 15000, // 15 seconds
  });
};

export const useCreateStopLoss = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      symbol: string;
      position_id: string;
      trigger_type: StopLossOrder['trigger_type'];
      trigger_percent: number;
      activation_price: number;
      user_id: string;
    }) => {
      const response = await fetch(`${API_BASE}/stop-loss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<StopLossOrder> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create stop-loss order');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.stopLoss() });
    },
  });
};

export const useCancelStopLoss = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (stopLossId: string) => {
      const response = await fetch(`${API_BASE}/stop-loss/${stopLossId}`, {
        method: 'DELETE',
      });

      const result: ApiResponse<any> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to cancel stop-loss order');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.stopLoss() });
    },
  });
};

// Risk Alerts Hooks
export const useRiskAlerts = (userId?: string, filters?: {
  severity?: string;
  type?: string;
  start_date?: string;
  end_date?: string;
}) => {
  return useQuery({
    queryKey: riskQueryKeys.alerts(userId, filters),
    queryFn: async (): Promise<PaginatedResponse<RiskAlert>> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (filters?.severity) params.append('severity', filters.severity);
      if (filters?.type) params.append('type', filters.type);
      if (filters?.start_date) params.append('start_date', filters.start_date);
      if (filters?.end_date) params.append('end_date', filters.end_date);

      const response = await fetch(`${API_BASE}/alerts?${params}`);
      const result: ApiResponse<{ alerts: RiskAlert[]; pagination: any }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch risk alerts');
      }

      return {
        data: result.data?.alerts || [],
        pagination: result.data?.pagination || { total: 0, limit: 20, offset: 0, has_more: false },
      };
    },
    staleTime: 10000, // 10 seconds
  });
};

export const useAcknowledgeAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alertId, acknowledgedBy, notes }: {
      alertId: string;
      acknowledgedBy: string;
      notes?: string;
    }) => {
      const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: acknowledgedBy, notes }),
      });

      const result: ApiResponse<RiskAlert> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to acknowledge alert');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.alerts() });
    },
  });
};

// Portfolio Risk Metrics Hooks
export const usePortfolioRiskMetrics = (portfolioId: string, period: string = '1M') => {
  return useQuery({
    queryKey: riskQueryKeys.metrics(portfolioId, period),
    queryFn: async (): Promise<PortfolioRiskMetrics> => {
      const params = new URLSearchParams({
        portfolio_id: portfolioId,
        period,
      });

      const response = await fetch(`${API_BASE}/portfolio/risk-metrics?${params}`);
      const result: ApiResponse<PortfolioRiskMetrics> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch risk metrics');
      }

      return result.data!;
    },
    staleTime: 60000, // 1 minute
  });
};

// Risk Monitoring Status Hooks
export const useRiskMonitoringStatus = (userId?: string, portfolioId?: string) => {
  return useQuery({
    queryKey: riskQueryKeys.monitoring(userId, portfolioId),
    queryFn: async (): Promise<RiskMonitoringStatus> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (portfolioId) params.append('portfolio_id', portfolioId);

      const response = await fetch(`${API_BASE}/monitor/status?${params}`);
      const result: ApiResponse<RiskMonitoringStatus> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch monitoring status');
      }

      return result.data!;
    },
    staleTime: 5000, // 5 seconds
  });
};

// Stop-Loss Templates Hooks (assuming these endpoints exist)
export const useStopLossTemplates = () => {
  return useQuery({
    queryKey: riskQueryKeys.templates(),
    queryFn: async (): Promise<StopLossTemplate[]> => {
      // This would be a custom endpoint for templates
      const response = await fetch(`${API_BASE}/templates/stop-loss`);
      const result: ApiResponse<{ templates: StopLossTemplate[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch stop-loss templates');
      }

      return result.data?.templates || [];
    },
    staleTime: 300000, // 5 minutes
  });
};

export const useCreateStopLossTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: StopLossTemplateFormData) => {
      const response = await fetch(`${API_BASE}/templates/stop-loss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<StopLossTemplate> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create stop-loss template');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.templates() });
    },
  });
};

// Rebalancing Rules Hooks (assuming these endpoints exist)
export const useRebalancingRules = () => {
  return useQuery({
    queryKey: riskQueryKeys.rebalancing(),
    queryFn: async (): Promise<RebalancingRule[]> => {
      const response = await fetch(`${API_BASE}/rebalancing/rules`);
      const result: ApiResponse<{ rules: RebalancingRule[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch rebalancing rules');
      }

      return result.data?.rules || [];
    },
    staleTime: 300000, // 5 minutes
  });
};

export const useCreateRebalancingRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RebalancingRuleFormData) => {
      const response = await fetch(`${API_BASE}/rebalancing/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<RebalancingRule> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create rebalancing rule');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.rebalancing() });
    },
  });
};

// Emergency Overrides Hooks (assuming these endpoints exist)
export const useEmergencyOverrides = () => {
  return useQuery({
    queryKey: riskQueryKeys.overrides(),
    queryFn: async (): Promise<EmergencyOverride[]> => {
      const response = await fetch(`${API_BASE}/emergency/overrides`);
      const result: ApiResponse<{ overrides: EmergencyOverride[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch emergency overrides');
      }

      return result.data?.overrides || [];
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useCreateEmergencyOverride = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EmergencyOverrideFormData) => {
      const response = await fetch(`${API_BASE}/emergency/overrides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<EmergencyOverride> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create emergency override');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskQueryKeys.overrides() });
    },
  });
};