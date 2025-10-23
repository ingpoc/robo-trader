import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Order,
  OrderTemplate,
  OrderGroup,
  BracketOrder,
  OrderMonitoringStatus,
  OrderStatistics,
  ConditionalOrder,
  OrderHistory,
  OrderExecution,
  PaginatedResponse,
  ApiResponse,
  OrderFormData,
  OrderTemplateFormData,
  BracketOrderFormData,
  OrderGroupFormData,
  OrderFilters,
  OrderSortOptions,
  OrderApiError,
} from '../types';

// API Base URL
const API_BASE = 'http://robo-trader-orders:8003';

// Query Keys
export const orderQueryKeys = {
  orders: (userId?: string, filters?: OrderFilters, sort?: OrderSortOptions) => [
    'orders',
    userId,
    filters,
    sort,
  ] as const,
  order: (orderId: string) => ['order', orderId] as const,
  orderHistory: (orderId: string) => ['order-history', orderId] as const,
  orderExecutions: (orderId: string) => ['order-executions', orderId] as const,
  templates: (userId?: string) => ['order-templates', userId] as const,
  template: (templateId: string) => ['order-template', templateId] as const,
  groups: (userId?: string) => ['order-groups', userId] as const,
  group: (groupId: string) => ['order-group', groupId] as const,
  brackets: (userId?: string) => ['bracket-orders', userId] as const,
  bracket: (bracketId: string) => ['bracket-order', bracketId] as const,
  conditionals: (userId?: string) => ['conditional-orders', userId] as const,
  conditional: (conditionalId: string) => ['conditional-order', conditionalId] as const,
  monitoring: (userId?: string) => ['order-monitoring', userId] as const,
  statistics: (userId?: string, period?: string) => ['order-statistics', userId, period] as const,
};

// Orders Hooks
export const useOrders = (
  userId?: string,
  filters?: OrderFilters,
  sort?: OrderSortOptions,
  page: number = 1,
  limit: number = 50
) => {
  return useQuery({
    queryKey: orderQueryKeys.orders(userId, filters, sort),
    queryFn: async (): Promise<PaginatedResponse<Order>> => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });

      if (userId) params.append('user_id', userId);
      if (filters?.symbol) params.append('symbol', filters.symbol);
      if (filters?.side) params.append('side', filters.side);
      if (filters?.order_type) params.append('order_type', filters.order_type);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.time_in_force) params.append('time_in_force', filters.time_in_force);
      if (filters?.date_from) params.append('date_from', filters.date_from);
      if (filters?.date_to) params.append('date_to', filters.date_to);
      if (filters?.min_value) params.append('min_value', filters.min_value.toString());
      if (filters?.max_value) params.append('max_value', filters.max_value.toString());
      if (filters?.tags) params.append('tags', filters.tags.join(','));

      if (sort) {
        params.append('sort_field', sort.field);
        params.append('sort_direction', sort.direction);
      }

      const response = await fetch(`${API_BASE}/orders?${params}`);
      const result: ApiResponse<PaginatedResponse<Order>> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch orders');
      }

      return result.data!;
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useOrder = (orderId: string) => {
  return useQuery({
    queryKey: orderQueryKeys.order(orderId),
    queryFn: async (): Promise<Order> => {
      const response = await fetch(`${API_BASE}/orders/${orderId}`);
      const result: ApiResponse<Order> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order');
      }

      return result.data!;
    },
    staleTime: 15000, // 15 seconds
  });
};

export const useOrderHistory = (orderId: string) => {
  return useQuery({
    queryKey: orderQueryKeys.orderHistory(orderId),
    queryFn: async (): Promise<OrderHistory> => {
      const response = await fetch(`${API_BASE}/orders/${orderId}/history`);
      const result: ApiResponse<OrderHistory> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order history');
      }

      return result.data!;
    },
    staleTime: 60000, // 1 minute
  });
};

export const useOrderExecutions = (orderId: string) => {
  return useQuery({
    queryKey: orderQueryKeys.orderExecutions(orderId),
    queryFn: async (): Promise<OrderExecution[]> => {
      const response = await fetch(`${API_BASE}/orders/${orderId}/executions`);
      const result: ApiResponse<{ executions: OrderExecution[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order executions');
      }

      return result.data?.executions || [];
    },
    staleTime: 10000, // 10 seconds
  });
};

export const useCreateOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: OrderFormData): Promise<Order> => {
      const response = await fetch(`${API_BASE}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<Order> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create order');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

export const useUpdateOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ orderId, updates }: { orderId: string; updates: Partial<Order> }): Promise<Order> => {
      const response = await fetch(`${API_BASE}/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      const result: ApiResponse<Order> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to update order');
      }

      return result.data!;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.order(data.id) });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

export const useCancelOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (orderId: string): Promise<Order> => {
      const response = await fetch(`${API_BASE}/orders/${orderId}/cancel`, {
        method: 'POST',
      });

      const result: ApiResponse<Order> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to cancel order');
      }

      return result.data!;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.order(data.id) });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

// Order Templates Hooks
export const useOrderTemplates = (userId?: string) => {
  return useQuery({
    queryKey: orderQueryKeys.templates(userId),
    queryFn: async (): Promise<OrderTemplate[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/templates?${params}`);
      const result: ApiResponse<{ templates: OrderTemplate[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order templates');
      }

      return result.data?.templates || [];
    },
    staleTime: 300000, // 5 minutes
  });
};

export const useOrderTemplate = (templateId: string) => {
  return useQuery({
    queryKey: orderQueryKeys.template(templateId),
    queryFn: async (): Promise<OrderTemplate> => {
      const response = await fetch(`${API_BASE}/templates/${templateId}`);
      const result: ApiResponse<OrderTemplate> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order template');
      }

      return result.data!;
    },
    staleTime: 300000, // 5 minutes
  });
};

export const useCreateOrderTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: OrderTemplateFormData): Promise<OrderTemplate> => {
      const response = await fetch(`${API_BASE}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<OrderTemplate> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create order template');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.templates() });
    },
  });
};

export const useUpdateOrderTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ templateId, updates }: { templateId: string; updates: Partial<OrderTemplate> }): Promise<OrderTemplate> => {
      const response = await fetch(`${API_BASE}/templates/${templateId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      const result: ApiResponse<OrderTemplate> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to update order template');
      }

      return result.data!;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.templates() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.template(data.id) });
    },
  });
};

export const useDeleteOrderTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (templateId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/templates/${templateId}`, {
        method: 'DELETE',
      });

      const result: ApiResponse<any> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to delete order template');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.templates() });
    },
  });
};

export const useApplyOrderTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ templateId, overrides }: { templateId: string; overrides?: Partial<OrderFormData> }): Promise<Order> => {
      const response = await fetch(`${API_BASE}/templates/${templateId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(overrides || {}),
      });

      const result: ApiResponse<Order> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to apply order template');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

// Bracket Orders Hooks
export const useBracketOrders = (userId?: string) => {
  return useQuery({
    queryKey: orderQueryKeys.brackets(userId),
    queryFn: async (): Promise<BracketOrder[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/brackets?${params}`);
      const result: ApiResponse<{ brackets: BracketOrder[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch bracket orders');
      }

      return result.data?.brackets || [];
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useCreateBracketOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BracketOrderFormData): Promise<BracketOrder> => {
      const response = await fetch(`${API_BASE}/brackets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<BracketOrder> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create bracket order');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.brackets() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

// Order Groups Hooks
export const useOrderGroups = (userId?: string) => {
  return useQuery({
    queryKey: orderQueryKeys.groups(userId),
    queryFn: async (): Promise<OrderGroup[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/groups?${params}`);
      const result: ApiResponse<{ groups: OrderGroup[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order groups');
      }

      return result.data?.groups || [];
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useCreateOrderGroup = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: OrderGroupFormData): Promise<OrderGroup> => {
      const response = await fetch(`${API_BASE}/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<OrderGroup> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create order group');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.groups() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.monitoring() });
    },
  });
};

// Conditional Orders Hooks
export const useConditionalOrders = (userId?: string) => {
  return useQuery({
    queryKey: orderQueryKeys.conditionals(userId),
    queryFn: async (): Promise<ConditionalOrder[]> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/conditionals?${params}`);
      const result: ApiResponse<{ conditionals: ConditionalOrder[] }> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch conditional orders');
      }

      return result.data?.conditionals || [];
    },
    staleTime: 30000, // 30 seconds
  });
};

export const useCreateConditionalOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      condition: ConditionalOrder['condition'];
      trigger_order: OrderFormData;
      expires_at?: string;
    }): Promise<ConditionalOrder> => {
      const response = await fetch(`${API_BASE}/conditionals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result: ApiResponse<ConditionalOrder> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create conditional order');
      }

      return result.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.conditionals() });
    },
  });
};

// Monitoring and Statistics Hooks
export const useOrderMonitoringStatus = (userId?: string) => {
  return useQuery({
    queryKey: orderQueryKeys.monitoring(userId),
    queryFn: async (): Promise<OrderMonitoringStatus> => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/monitoring/status?${params}`);
      const result: ApiResponse<OrderMonitoringStatus> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch monitoring status');
      }

      return result.data!;
    },
    staleTime: 5000, // 5 seconds
  });
};

export const useOrderStatistics = (userId?: string, period: string = '1M') => {
  return useQuery({
    queryKey: orderQueryKeys.statistics(userId, period),
    queryFn: async (): Promise<OrderStatistics> => {
      const params = new URLSearchParams({
        period,
      });
      if (userId) params.append('user_id', userId);

      const response = await fetch(`${API_BASE}/statistics?${params}`);
      const result: ApiResponse<OrderStatistics> = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to fetch order statistics');
      }

      return result.data!;
    },
    staleTime: 60000, // 1 minute
  });
};